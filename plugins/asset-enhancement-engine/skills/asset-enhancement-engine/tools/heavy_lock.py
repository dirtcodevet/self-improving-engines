"""HEAVY-RUN LOCK (RI A24): lets several builders work side by side while their heavy CPU / RAM runs (field builds,
full-mesh passes) share the machine by a MEMORY BUDGET. Exists because the cat v3 round 2 runs four owners in parallel on a
16 GB machine, and two simultaneous 0.10 mm field builds would push free memory under the 2 GB floor (NOTES_v3 resource
rule). 2026-10-19: was exclusive (one heavy job at a time, whatever its size); a torso test then waited ~55 min behind
the cat's jobs at ~1 % total CPU with 15 cores idle. A job that declares its memory now runs beside the others.

usage: python heavy_lock.py [--reserve-gb R [--floor-gb 2.0]] [--min-free-gb F] [--label NAME] -- <command ...>
  - SHARED (--reserve-gb R: the GB the job will use at its peak): it starts when no exclusive job runs or waits ahead of
    it and  R + floor + (the reservations of the running shared jobs not yet in use)  <= measured free memory.
    "Not yet in use" = max(0, reserve - the memory its process tree holds now): memory a job already holds is already out
    of the measured free memory and is not counted twice. --min-free-gb, if given, is also required free.
    A job that does not fit with nothing else running gives up after 30 min (exit 75);
  - EXCLUSIVE (no --reserve-gb: every existing call, unchanged): waits until no other heavy job runs, then until free
    physical memory >= --min-free-gb (default 2.0; give up after 30 min, exit 75), and runs alone. A waiting exclusive
    job holds back shared jobs that arrive after it, so it is not starved;
  - runs the command, releases, exits with the command's exit code;
  - a holder whose process is dead is cleared (its PID, and the PID's start time against the holder's, are checked);
  - every acquire / release is appended to <lock dir>/heavy_lock.log with times and free memory.
State: <lock> (tripo_rebuild/layers/.heavy.lock) lists the running holders, one line each, PID first; it exists while any
heavy job runs and a line without tabs is the original one-holder format ("pid label" = exclusive). <lock>.wait lists the
waiting jobs. Both are changed only under a named Windows mutex, which the OS releases if its holder dies.
Builders that size their own worker pools call others_unused_gb() (the other jobs' reservations not yet in use)
or free_budget_gb() (free memory less those).
"""
import ctypes
import hashlib
import os
import subprocess
import sys
import time
from ctypes import wintypes

LOCK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tripo_rebuild", "layers", ".heavy.lock")
LOCK = os.path.normpath(os.environ.get("HEAVY_LOCK_FILE", LOCK))
LOG = os.path.join(os.path.dirname(LOCK), "heavy_lock.log")
WAIT = LOCK + ".wait"
FLOOR_GB = 2.0          # kept free under every shared admission (the A24 reserve)
GIVE_UP_S = 1800        # 30 min, as the original memory gate
_K = ctypes.WinDLL("kernel32", use_last_error=True)
_K.OpenProcess.restype = wintypes.HANDLE; _K.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
_K.CloseHandle.argtypes = [wintypes.HANDLE]
_K.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
_K.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(ctypes.c_ulonglong)] * 4
_K.CreateMutexW.restype = wintypes.HANDLE; _K.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
_K.WaitForSingleObject.restype = wintypes.DWORD; _K.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
_K.ReleaseMutex.argtypes = [wintypes.HANDLE]
_K.CreateToolhelp32Snapshot.restype = wintypes.HANDLE; _K.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]


class _MS(ctypes.Structure):
    _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong), ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong), ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong), ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]


class _PMC(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [(k, ctypes.c_size_t) for k in (
        "PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage", "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage",
        "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage", "PrivateUsage")]


class _PE(ctypes.Structure):
    _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD), ("th32ProcessID", wintypes.DWORD),
                ("th32DefaultHeapID", ctypes.c_size_t), ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", ctypes.c_long), ("dwFlags", wintypes.DWORD),
                ("szExeFile", ctypes.c_wchar * 260)]


def free_gb():
    m = _MS(); m.dwLength = ctypes.sizeof(_MS)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    return m.ullAvailPhys / 1e9


def pid_alive(pid):
    h = _K.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not h: return False
    code = wintypes.DWORD(); _K.GetExitCodeProcess(h, ctypes.byref(code)); _K.CloseHandle(h)
    return code.value == 259  # STILL_ACTIVE


def _started(pid):
    """the process's creation time (epoch s), None if it cannot be opened"""
    h = _K.OpenProcess(0x1000, False, pid)
    if not h: return None
    t = [ctypes.c_ulonglong() for _ in range(4)]; ok = _K.GetProcessTimes(h, *[ctypes.byref(x) for x in t]); _K.CloseHandle(h)
    return t[0].value / 1e7 - 11644473600.0 if ok else None


def _mem_gb(pid):
    """memory the process holds: min(working set, private bytes) (GB)"""
    h = _K.OpenProcess(0x1000 | 0x0010, False, pid)  # + PROCESS_VM_READ
    if not h: return 0.0
    m = _PMC(); m.cb = ctypes.sizeof(_PMC); ok = ctypes.windll.psapi.GetProcessMemoryInfo(wintypes.HANDLE(h), ctypes.byref(m), m.cb)
    _K.CloseHandle(h)
    return min(m.WorkingSetSize, m.PrivateUsage) / 1e9 if ok else 0.0


def _ppids():
    """{pid: parent pid} of every process (Toolhelp snapshot)"""
    snap = _K.CreateToolhelp32Snapshot(0x2, 0); out = {}
    if not snap or snap == ctypes.c_void_p(-1).value:
        return out
    e = _PE(); e.dwSize = ctypes.sizeof(_PE)
    ok = ctypes.windll.kernel32.Process32FirstW(wintypes.HANDLE(snap), ctypes.byref(e))
    while ok:
        out[e.th32ProcessID] = e.th32ParentProcessID; ok = ctypes.windll.kernel32.Process32NextW(wintypes.HANDLE(snap), ctypes.byref(e))
    _K.CloseHandle(snap)
    return out


def tree(root, pp=None):
    """root and its descendants (a child must have started after its parent: a recycled parent PID adopts nothing)"""
    pp = _ppids() if pp is None else pp; kids = {}
    for c, p in pp.items():
        if c != p:
            kids.setdefault(p, []).append(c)
    out, todo = [root], [root]
    while todo:
        p = todo.pop(); tp = _started(p)
        for c in kids.get(p, []):
            tc = _started(c)
            if tp is not None and tc is not None and tc + 1 >= tp:
                out.append(c); todo.append(c)
    return out


def tree_gb(root, pp=None):
    return sum(_mem_gb(p) for p in tree(root, pp))


def log(msg):
    with open(LOG, "a", encoding="utf-8") as fh: fh.write(f"{time.strftime('%H:%M:%S')} {msg}\n")


class _Mutex:
    """a named Windows mutex per lock file: the registry's read-modify-write is atomic across processes; the OS releases
    it if its holder dies (WAIT_ABANDONED is still a grant)"""
    def __init__(self):
        self.h = _K.CreateMutexW(None, False, "Local\\heavy_lock_" + hashlib.sha1(os.path.normcase(LOCK).encode()).hexdigest()[:16])
        if not self.h: raise OSError(f"CreateMutexW failed ({ctypes.get_last_error()})")

    def __enter__(self):
        if _K.WaitForSingleObject(self.h, 60000) not in (0, 0x80): raise TimeoutError("heavy_lock mutex held > 60 s")
        return self

    def __exit__(self, *a):
        _K.ReleaseMutex(self.h)


def _read(path):
    rows = []
    try:
        txt = open(path, encoding="utf-8").read()
    except FileNotFoundError:
        return rows
    for ln in txt.splitlines():
        if not ln.strip(): continue
        try:
            if "\t" in ln:
                p = ln.split("\t"); rows.append(dict(pid=int(p[0]), label=p[1], mode=p[2], reserve=None if p[3] == "-" else float(p[3]),
                                                     t0=None if p[4] == "-" else float(p[4])))
            else:                                   # the original format "pid label": an exclusive holder
                p = ln.split(None, 1); rows.append(dict(pid=int(p[0]), label=p[1] if len(p) > 1 else "?", mode="excl", reserve=None, t0=None))
        except (ValueError, IndexError):
            log(f"CLEARED unreadable lock line {ln[:80]!r}")
    return rows


def _write(path, rows):
    if not rows:
        try: os.remove(path)
        except FileNotFoundError: pass
        return
    txt = "".join(f"{r['pid']}\t{r['label']}\t{r['mode']}\t{'-' if r['reserve'] is None else r['reserve']}\t"
                  f"{'-' if r['t0'] is None else format(r['t0'], '.3f')}\n" for r in rows)
    tmp = f"{path}.{os.getpid()}.tmp"
    with open(tmp, "w", encoding="utf-8") as fh: fh.write(txt)
    for k in range(50):                             # a reader outside the mutex can hold the file open for a moment
        try: os.replace(tmp, path); return
        except PermissionError: time.sleep(0.05)
    os.replace(tmp, path)


def _alive(r):
    if not pid_alive(r["pid"]): return False
    ts = _started(r["pid"])                         # a recycled PID started after the holder registered is not the holder
    return r["t0"] is None or ts is None or ts <= r["t0"] + 2.0


def _live(path, quiet=False):
    rows = _read(path); keep = [r for r in rows if _alive(r)]
    if len(keep) != len(rows):
        for r in rows:
            if r not in keep and not quiet: log(f"CLEARED stale lock of dead pid {r['pid']}")
        _write(path, keep)
    return keep


def _unused_gb(rows, pp=None, skip=()):
    """the running shared jobs' reservations not yet in use (GB)"""
    pp = _ppids() if pp is None else pp
    return sum(max(0.0, r["reserve"] - tree_gb(r["pid"], pp)) for r in rows if r["mode"] == "shared" and r["pid"] not in skip)


def others_unused_gb():
    """for builders sizing their own pools: the reservations (GB) of the OTHER running jobs not yet in use (the caller's
    own holder - an ancestor of this process - is skipped)"""
    pp = _ppids(); anc, p = set(), os.getpid()
    while p in pp and p not in anc:
        anc.add(p); p = pp[p]
    with _Mutex():
        rows = [r for r in _read(LOCK) if _alive(r)]
    return _unused_gb(rows, pp, skip=anc)


def free_budget_gb():
    """measured free memory less the other running jobs' unused reservations (GB)"""
    return free_gb() - others_unused_gb()


def _admit(me, run, wait, floor, min_free):
    """(ok, why) for job `me` against the running holders and the waiting list"""
    ahead = [w for w in wait if w["mode"] == "excl" and w["pid"] != me["pid"] and w["t0"] < me["t0"]]
    if me["mode"] == "excl":
        if run: return False, "running: " + ", ".join(r["label"] for r in run)
        if ahead: return False, "exclusive ahead: " + ", ".join(w["label"] for w in ahead)
        return True, ""
    ex = [r for r in run if r["mode"] != "shared"]
    if ex: return False, "exclusive running: " + ", ".join(r["label"] for r in ex)
    if ahead: return False, "exclusive ahead: " + ", ".join(w["label"] for w in ahead)
    unused = _unused_gb(run); fr = free_gb(); need = me["reserve"] + floor + unused
    if fr < need or (min_free is not None and fr < min_free):
        return False, f"free {fr:.2f} GB < reserve {me['reserve']} + floor {floor} + unused {unused:.2f} = {need:.2f} GB" + \
            (f" (or min-free {min_free})" if min_free is not None else "")
    return True, f"free {fr:.2f} >= {need:.2f} GB"


def acquire(label, reserve=None, floor=FLOOR_GB, min_free=None, poll=1.0):
    """wait for admission, register as a holder; returns the holder row"""
    t0 = time.time(); me = dict(pid=os.getpid(), label=label, mode="excl" if reserve is None else "shared", reserve=reserve, t0=t0)
    said, alone_since = False, None
    try:
        while True:
            with _Mutex():
                run = _live(LOCK); wait = _live(WAIT, quiet=True)
                if not any(w["pid"] == me["pid"] for w in wait):
                    wait.append(me); _write(WAIT, wait)
                ok, why = _admit(me, run, wait, floor, min_free)
                if ok:
                    row = dict(me, t0=time.time()); _write(LOCK, run + [row]); _write(WAIT, [w for w in wait if w["pid"] != me["pid"]])
                    extra = "" if reserve is None else f" reserve {reserve} GB shared ({why}; beside: {', '.join(r['label'] for r in run) or 'none'})"
                    log(f"ACQUIRE {label} pid {me['pid']} waited {time.time()-t0:.0f}s free {free_gb():.2f} GB{extra}"); return row
            if not said:
                log(f"WAIT {label} pid {me['pid']} {'exclusive' if reserve is None else f'reserve {reserve} GB'}: {why}"); said = True
            if reserve is not None:                  # a shared job that cannot fit even with nothing else running gives up
                alone_since = (alone_since or time.time()) if not run else None
                if alone_since and time.time() - alone_since > GIVE_UP_S:
                    log(f"GIVE UP {label}: {why} for 30 min with nothing else running"); sys.exit(75)
            time.sleep(poll)
    finally:
        with _Mutex():
            wait = _read(WAIT)
            if any(w["pid"] == me["pid"] for w in wait): _write(WAIT, [w for w in wait if w["pid"] != me["pid"]])


def release(row):
    with _Mutex():
        _write(LOCK, [r for r in _read(LOCK) if r["pid"] != row["pid"]])
    log(f"RELEASE {row['label']} free {free_gb():.2f} GB")


def main():
    a = sys.argv[1:]
    if "--" not in a: print(__doc__); sys.exit(2)
    opts, cmd = a[:a.index("--")], a[a.index("--") + 1:]
    val = lambda k, d: float(opts[opts.index(k) + 1]) if k in opts else d  # noqa: E731
    reserve, floor, min_free = val("--reserve-gb", None), val("--floor-gb", FLOOR_GB), val("--min-free-gb", None)
    label = opts[opts.index("--label") + 1] if "--label" in opts else os.path.basename(cmd[0])
    row = acquire(" ".join(label.split()), reserve, floor, min_free)
    try:
        if reserve is None:                          # exclusive: the original free-memory gate, unchanged
            mf = 2.0 if min_free is None else min_free; t0 = time.time()
            while free_gb() < mf:
                if time.time() - t0 > GIVE_UP_S: log(f"GIVE UP {label}: free {free_gb():.2f} < {mf} GB for 30 min"); sys.exit(75)
                time.sleep(2)
        rc = subprocess.call(cmd)
    finally:
        release(row)
    sys.exit(rc)


if __name__ == "__main__":
    main()
