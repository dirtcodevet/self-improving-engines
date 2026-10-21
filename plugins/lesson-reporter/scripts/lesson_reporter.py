#!/usr/bin/env python3
"""Lesson reporter - OUTBOX PROTOTYPE (no network). Spec: docs/lesson-reporter/SPEC.md in the repo.

Packages ONLY engine-improvement material - structured lessons, diffs of the engine's own tools, method notes - into a
redacted package in a local outbox, shows exactly what would be sent, and records the user's approval. It never sends
anything: `send` is disabled. It imports no network or process modules (a test checks this).

Three switches, all OFF by default (SPEC "Consent"):
  1. the plugin itself ships disabled (defaultEnabled: false);
  2. reporting for an engine must be turned on by the user in an interactive terminal (`enable`);
  3. every package needs its own approval, typed in an interactive terminal, bound to the package's sha256.

usage (the skill passes --data "${CLAUDE_PLUGIN_DATA}"):
  python lesson_reporter.py --data DIR status  [--engine ENGINE_PLUGIN_DIR]
  python lesson_reporter.py --data DIR enable  --engine ENGINE_PLUGIN_DIR      # terminal only
  python lesson_reporter.py --data DIR disable --engine ENGINE_PLUGIN_DIR
  python lesson_reporter.py --data DIR prepare --engine ENGINE_PLUGIN_DIR --lessons lessons.json
                                               [--tool-change tools/x.py=PATH ...] [--note note.md ...] [--outbox DIR]
  python lesson_reporter.py show    PACKAGE_DIR
  python lesson_reporter.py approve PACKAGE_DIR                                # terminal only
  python lesson_reporter.py verify  PACKAGE_DIR
  python lesson_reporter.py screen  PACKAGE_JSON --engine ENGINE_PLUGIN_DIR    # maintainer / CI side
  python lesson_reporter.py send    PACKAGE_DIR                                # disabled in the prototype
"""
import argparse
import difflib
import hashlib
import json
import os
import re
import secrets
import sys
import time
import unicodedata
from datetime import date
from pathlib import Path, PurePosixPath, PureWindowsPath

VERSION = "0.0.1"
PACKAGE_SCHEMA = "lesson-report/0.1"
OUTBOX_SCHEMA = "lesson-outbox/0.1"

KINDS = ["check", "judgment", "tool", "method_note"]
LESSON_FIELDS = ["id", "kind", "target", "title", "statement", "evidence", "toggle", "ratchet",
                 "proof", "replaces", "tool_change", "toolmaking"]
LESSON_REQUIRED = ["id", "kind", "target", "title", "statement", "evidence", "toggle", "ratchet"]
PACKAGE_FIELDS = ["schema", "reporter_version", "engine", "engine_version", "created", "lessons", "tool_diffs",
                  "notes", "links", "attention", "redactions"]
NOTE_EXTENSIONS = {".md", ".txt"}
# never lesson material, whatever the folder: pictures, meshes, scenes, arrays, archives, media, documents
FORBIDDEN_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".exr", ".hdr", ".heic", ".psd", ".svg",
    ".blend", ".blend1", ".obj", ".fbx", ".glb", ".gltf", ".ply", ".stl", ".abc", ".usd", ".usda", ".usdc", ".usdz",
    ".vdb", ".npz", ".npy", ".pkl", ".pickle", ".h5", ".hdf5", ".pt", ".pth", ".safetensors", ".onnx", ".ckpt",
    ".zip", ".7z", ".rar", ".tar", ".gz", ".mp4", ".mov", ".avi", ".webm", ".wav", ".mp3", ".pdf", ".docx", ".xlsx",
    ".exe", ".dll", ".so", ".dylib", ".pyc",
}

ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._#-]{0,63}$")
FLAG_RE = re.compile(r"^[A-Z][A-Za-z0-9_]{1,63}$")
LOGREF_RE = re.compile(r"^[A-Za-z0-9_.#/ -]{1,80}$")
REL_RE = re.compile(r"^[A-Za-z0-9_./-]{1,200}$")
PROOF_CMD_RE = re.compile(r"^(?:python3?|bash|sh)\s+([A-Za-z0-9_./-]+)(?:\s+[A-Za-z0-9_./<>=:-]+)*$")


class Refused(Exception):
    """Nothing was written. `reasons` = [{code, where, detail}]; details never contain a detected secret."""

    def __init__(self, reasons):
        self.reasons = reasons
        super().__init__("; ".join(f"{r['code']} at {r['where']}: {r['detail']}" for r in reasons))


def _reason(code, where, detail):
    return {"code": code, "where": where, "detail": detail}


# ---------------------------------------------------------------- patterns
BS, FS = r"\\{1,2}", "/"            # one or two backslashes (two when escaped inside source code), or a slash


def _tail(sep):
    """The rest of a path written with ONE separator style. Folders may contain spaces ("My Models") but not start
    with one or hold , ; and a change of separator ends the path - so a path never runs on into the prose after it."""
    mid = rf"(?:{sep}[^\s\\/:*?\"<>|,;][^\\/:*?\"<>|\r\n,;]{{0,63}}?(?={sep}))*"
    last = rf"(?:{sep}[^\\/:*?\"<>|\s,;)\]'`]*)?"            # the last part may not hold spaces (prose follows it)
    return mid + last


_EITHER = rf"(?:(?={BS}){_tail(BS)}|(?={FS}){_tail(FS)})"
PATH_RES = [
    re.compile(rf"(?<![A-Za-z0-9])[A-Za-z]:{_EITHER}"),                                     # C:\... C:/...
    re.compile(rf"\\\\[^\\/\s:*?\"<>|]+{_tail(BS)}"),                                       # \\host\share\...
    re.compile(rf"(?<![\w])~[A-Za-z0-9_.-]*{_EITHER}"),                                     # ~/... ~user/...
    re.compile(rf"(?:%(?:USERPROFILE|HOMEPATH|APPDATA|LOCALAPPDATA|TEMP|TMP|ONEDRIVE)%|\$\{{?(?:HOME|USERPROFILE|TMPDIR)\}}?)"
               rf"{_EITHER}", re.I),
    re.compile(rf"(?<![\w.<>/~-])/(?:[A-Za-z]|mnt|home|Users|Volumes|private|tmp|var|opt|srv|root|media|run|data|"
               rf"workspace|etc|usr)(?=/){_tail(FS)}"),                                      # /c/Users/... /home/...
]
FILE_URL_RE = re.compile(r"file:/{2,3}[^\s\"'<>)]+", re.I)
URL_RE = re.compile(r"https?://[^\s\"'<>)\]]+", re.I)
CASE_RE = re.compile(r"(?<![A-Za-z0-9_])cases(?:\\{1,2}|/)[^\\/\s\"'<>|,;:)\]]+")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
IP_RE = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")

SECRET_RES = [
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}")),
    ("GitHub token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{22,}")),
    ("API key", re.compile(r"\bsk-(?:ant-|proj-)?[A-Za-z0-9_-]{20,}")),
    ("AWS key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}")),
    ("private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("JSON web token", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
    ("bearer token", re.compile(r"\bbearer\s+[A-Za-z0-9._~+/-]{20,}", re.I)),
    ("credential assignment", re.compile(r"(?i)\b(?:api[_-]?key|secret|token|password|passwd|pwd)\b\s*[:=]\s*['\"]?"
                                         r"[A-Za-z0-9_\-/+=.]{16,}")),
]
# phrases addressed to an AI that reads the text (the maintainer's reviewer, or later every user's agent)
INJECTION_ANY = [re.compile(p, re.I) for p in (
    r"\b(?:ignore|disregard|forget|override)\b[^.\n]{0,40}?\b(?:previous|prior|above|earlier|preceding|all|any|other)\b"
    r"[^.\n]{0,20}?\b(?:instructions?|rules?|prompts?|messages?|guidelines?)\b",
    r"\byou are now\b",
    r"\b(?:system|developer)\s+(?:prompt|message|instructions?)\b",
    r"</?\s*(?:system|assistant|user|developer|instructions?)\s*>",
    r"\[/?INST\]|<\|im_(?:start|end)\|>",
    r"\b(?:do not|don't|never)\s+(?:tell|inform|show|ask|alert|notify)\s+the\s+(?:user|person|human|maintainer|reviewer)\b",
    r"\bwithout\s+(?:asking|telling|informing|notifying|showing)\s+the\s+(?:user|person|human|maintainer|reviewer)\b",
    r"\b(?:ai|llm|agent|model|claude|assistant|bot)(?:\s+(?:reviewer|maintainer))?\s*[:,]\s*(?:please\s+)?"
    r"(?:approve|merge|ignore|accept|enable|run|execute)\b",
)]
INJECTION_PROSE = [re.compile(p, re.I | re.M) for p in (
    r"^\s*(?:system|assistant|human|user)\s*:",
    r"\b(?:curl|wget|iwr|invoke-webrequest|invoke-restmethod|certutil|bitsadmin)\s+\S",
    r"\bpowershell(?:\.exe)?\s+-(?:e|enc|encodedcommand)\b",
    r"\|\s*(?:sh|bash|iex|powershell)\b",
)]
MARKUP_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)|<\s*(?:img|script|iframe|object|embed|link|meta|style|svg|form|input)\b|"
                       r"<!--|javascript:|data:[a-z]+/[a-z0-9.+-]+;base64", re.I)
QUOTE_RES = [re.compile(r'"([^"\n]{3,600})"'), re.compile(r"\u201c([^\u201d\n]{3,600})\u201d"),
             re.compile(r"\u201e([^\u201c\u201d\n]{3,600})[\u201c\u201d]")]
BLOCKQUOTE_RE = re.compile(r"^\s*>\s*\S+(?:\s+\S+){5,}", re.M)
B64_RE = re.compile(r"[A-Za-z0-9+/]{120,}={0,2}")
HEX_RE = re.compile(r"\b[0-9a-fA-F]{128,}\b")
NUM_RE = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?(?![\w.])")
NUMBERS_PER_LINE = 24
ATTENTION_RES = {
    "network": re.compile(r"\b(?:import|from)\s+(?:socket|ssl|http|urllib|requests|httpx|aiohttp|ftplib|smtplib|paramiko|"
                          r"websocket)\b|\burlopen\(|\brequests\.\w+\("),
    "subprocess": re.compile(r"\b(?:import|from)\s+subprocess\b|\bsubprocess\.|\bos\.(?:system|popen|exec\w*|spawn\w*)\("),
    "dynamic_code": re.compile(r"\b(?:eval|exec|__import__)\s*\(|\bimportlib\b"),
    "deserialization": re.compile(r"\bpickle\.|\ballow_pickle\s*=\s*True|\bmarshal\.|\byaml\.load\(|\bjoblib\.load\("),
    "native_code": re.compile(r"\bctypes\b|\bcffi\b"),
    "file_deletion": re.compile(r"\bshutil\.rmtree\(|\bos\.(?:remove|unlink|rmdir)\(|\.unlink\(|\.rmdir\("),
    "environment": re.compile(r"\bos\.environ\b|\bgetenv\(|\bkeyring\b"),
    "url": re.compile(r"https?://", re.I),
    "download_command": re.compile(r"\b(?:curl|wget|Invoke-WebRequest|iwr)\b", re.I),
}


# ---------------------------------------------------------------- engine and consent
def load_engine(engine_dir):
    d = Path(engine_dir)
    manifest = json.loads((d / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    cfg = json.loads((d / "reporter.json").read_text(encoding="utf-8"))
    return {"name": manifest["name"], "version": manifest.get("version", "unversioned"), "dir": d, "config": cfg,
            "skill": d / cfg["skill_dir"]}


def _settings_file(data_dir):
    return Path(data_dir) / "settings.json"


def _read_settings(data_dir):
    p = _settings_file(data_dir)
    try:
        s = json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}
    except ValueError:
        s = {}                                     # an unreadable settings file counts as OFF
    return s if isinstance(s, dict) else {}


class _Console:
    """The person's console device - CONOUT$/CONIN$ on Windows, /dev/tty elsewhere - and NEVER stdin, which an
    agent can pipe into. (The first prototype trusted sys.stdin.isatty(); on Windows that is True for the NUL device
    an agent's shell uses as stdin, and the agent's shell passed the gate. SPEC: Findings.)"""

    def __init__(self):
        if os.name == "nt":
            import msvcrt
            self._msvcrt = msvcrt
            self._out = open("CONOUT$", "w", encoding="utf-8", errors="replace")   # OSError: no console at all
        else:
            self._tty = open("/dev/tty", "r+", encoding="utf-8", errors="replace")  # OSError: no terminal
            self._out = self._tty

    def write(self, s):
        self._out.write(s)
        self._out.flush()

    def read_line(self, timeout):
        """Keystrokes from the console itself; None on timeout. A hidden console (an agent's) never gets any."""
        deadline = time.monotonic() + timeout
        if os.name == "nt":
            buf = ""
            while time.monotonic() < deadline:
                if self._msvcrt.kbhit():
                    ch = self._msvcrt.getwch()
                    if ch in "\r\n":
                        self.write("\n")
                        return buf
                    if ch == "\x03":
                        return None
                    if ch == "\b":
                        buf = buf[:-1]
                        self.write("\b \b")
                        continue
                    buf += ch
                    self.write(ch)
                else:
                    time.sleep(0.05)
            return None
        import select
        ready, _, _ = select.select([self._tty], [], [], timeout)
        return self._tty.readline().rstrip("\n") if ready else None


def _confirm_timeout():
    try:
        return min(600.0, max(1.0, float(os.environ.get("LESSON_REPORTER_CONFIRM_TIMEOUT", "300"))))
    except ValueError:
        return 300.0


def human_confirm(what, console=None, timeout=None):
    """A person at the console types a one-time code shown only on that console. Raises Refused otherwise."""
    try:
        con = console or _Console()
    except OSError:
        raise Refused([_reason("NEEDS_TERMINAL", what, "only you can do this, in your own interactive terminal "
                               "(PowerShell or Windows Terminal; in Git Bash use `winpty python ...`)")]) from None
    code = secrets.token_hex(3)
    con.write(f"\nTo {what}, type this one-time code and press Enter: {code}\n> ")
    answer = con.read_line(timeout or _confirm_timeout())
    if answer is None or answer.strip().lower() != code:
        con.write("Not confirmed - nothing changed.\n")
        raise Refused([_reason("NOT_CONFIRMED", what, "the one-time code was not typed at the console; nothing changed")])


def is_opted_in(data_dir, engine_name):
    return _read_settings(data_dir).get("engines", {}).get(engine_name, {}).get("enabled") is True


def set_opt_in(data_dir, engine_name, on, confirm=None):
    """Turning ON needs the person at the console (human_confirm); turning OFF always works, from anywhere."""
    if on:
        (confirm or human_confirm)(f"switch ON lesson reporting for {engine_name}")
    s = _read_settings(data_dir)
    s.setdefault("engines", {})[engine_name] = {"enabled": bool(on), "changed": date.today().isoformat()}
    Path(data_dir).mkdir(parents=True, exist_ok=True)
    _settings_file(data_dir).write_text(json.dumps(s, indent=1) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- identity and redaction
def _home_name(home):
    p = PureWindowsPath(home) if ("\\" in home or re.match(r"^[A-Za-z]:", home)) else PurePosixPath(home)
    return p.name


def _git_identity(text):
    names, emails, in_user = [], [], False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("["):
            in_user = s.lower().startswith("[user")
        elif in_user and "=" in s:
            k, v = (x.strip() for x in s.split("=", 1))
            v = v.strip('"')
            if k.lower() == "name" and v:
                names.append(v)
            elif k.lower() == "email" and v:
                emails.append(v)
    return names, emails


def build_identifiers(home=None, env=None, gitconfig_text=None, extra_terms=(), data_dir=None):
    """What identifies this user on this machine. Reads env, the home path, ~/.gitconfig [user] and the user's own
    redact_terms.txt. Never reads credential stores or the gh CLI's config (it holds a token)."""
    env = dict(os.environ) if env is None else env
    home = str(home or Path.home())
    if gitconfig_text is None:
        g = Path(home) / ".gitconfig"
        gitconfig_text = g.read_text(encoding="utf-8", errors="replace") if g.is_file() else ""
    git_names, git_emails = _git_identity(gitconfig_text)
    names = set(git_names)
    for n in git_names:
        names |= {t for t in re.split(r"\s+", n) if len(t) >= 3}
    users = {_home_name(home)} | {env.get(k, "") for k in ("USERNAME", "USER", "LOGNAME")}
    hosts = {env.get(k, "") for k in ("COMPUTERNAME", "HOSTNAME")}
    terms = set(extra_terms)
    if data_dir and (Path(data_dir) / "redact_terms.txt").is_file():
        for line in (Path(data_dir) / "redact_terms.txt").read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.strip().startswith("#"):
                terms.add(line.strip())
    clean = lambda xs: sorted({x for x in xs if x and len(x) >= 2}, key=len, reverse=True)  # noqa: E731
    return {"home": home, "users": clean(users), "hosts": clean(hosts), "names": clean(names),
            "emails": clean(git_emails), "terms": clean(terms)}


def _norm(p):
    s = p.replace("\\\\", "/").replace("\\", "/")
    m = re.match(r"^/([A-Za-z])/(.*)$", s)
    if m:
        s = m.group(1) + ":/" + m.group(2)
    return s.rstrip("/").lower()


def _word_re(term):
    return re.compile(rf"(?<![A-Za-z0-9]){re.escape(term)}(?![A-Za-z0-9])", re.I)


class Redactor:
    """Replaces paths, identities and case names. Counts what it replaced; never keeps the original values."""

    def __init__(self, ids, eng):
        self.counts = {}
        roots = []
        for p, ph in ((eng["skill"], "<engine>"), (eng["dir"], "<engine-plugin>")):
            for form in {str(Path(p).absolute()), str(Path(p).resolve())}:
                roots.append((_norm(form), ph))
        self.roots = sorted(set(roots), key=lambda r: len(r[0]), reverse=True)
        self.id_res = []
        for cat, ph in (("emails", "<email>"), ("names", "<name>"), ("hosts", "<host>"), ("users", "<user>"),
                        ("terms", "<term>")):
            for t in ids[cat]:
                self.id_res.append((_word_re(t), ph, cat))

    def _bump(self, cat, n=1):
        if n:
            self.counts[cat] = self.counts.get(cat, 0) + n

    def _path(self, m):
        p = m.group(0)
        n = _norm(p)
        for root, ph in self.roots:
            if n == root or n.startswith(root + "/"):
                self._bump("engine_path")
                return ph + "/" + n[len(root):].lstrip("/") if n != root else ph
        self._bump("path")
        return "<path>"

    def text(self, s):
        s, n = FILE_URL_RE.subn("<path>", s)
        self._bump("path", n)
        urls = []

        def keep(m):
            urls.append(m.group(0))
            return f"\ue000{len(urls) - 1}\ue001"
        s = URL_RE.sub(keep, s)
        for rx in PATH_RES:
            s = rx.sub(self._path, s)
        s = re.sub("\ue000(\\d+)\ue001", lambda m: urls[int(m.group(1))], s)
        s, n = CASE_RE.subn("cases/<case>", s)
        self._bump("case", n)
        s, n = EMAIL_RE.subn("<email>", s)
        self._bump("email", n)
        s, n = IP_RE.subn("<ip>", s)
        self._bump("ip", n)
        for rx, ph, cat in self.id_res:
            s, n = rx.subn(ph, s)
            self._bump(cat, n)
        return s


# ---------------------------------------------------------------- screening
def _excerpt(s, start, end):
    frag = s[max(0, start - 10):min(len(s), end + 10)].replace("\n", " ")
    for _, rx in SECRET_RES:
        frag = rx.sub("<secret>", frag)
    return (frag[:57] + "...") if len(frag) > 60 else frag


def screen_raw(text, where):
    """Before redaction: secrets (refused, never shown) and invisible characters."""
    out = []
    for name, rx in SECRET_RES:
        if rx.search(text):
            out.append(_reason("SECRET", where, f"contains what looks like a {name}; remove it (the value is not shown)"))
    hidden = sorted({f"U+{ord(c):04X}" for c in text
                     if unicodedata.category(c) == "Cf" or (unicodedata.category(c) == "Cc" and c not in "\t\n\r")})
    if hidden:
        out.append(_reason("HIDDEN_UNICODE", where, "invisible or control characters: " + ", ".join(hidden[:8])))
    return out


def _embedded_data(text, where, lines=None):
    out = []
    if B64_RE.search(text) or HEX_RE.search(text):
        out.append(_reason("EMBEDDED_DATA", where, "a long encoded blob (base64/hex) - lessons carry no data"))
    for line in (text.splitlines() if lines is None else lines):
        if len(NUM_RE.findall(line)) >= NUMBERS_PER_LINE:
            out.append(_reason("EMBEDDED_DATA", where, f"a line with {NUMBERS_PER_LINE}+ numbers looks like "
                               "measurement data - describe the result instead"))
            break
    return out


def _urls(text):
    return [u.rstrip(".,;:!?") for u in URL_RE.findall(text)]


PLACEHOLDER_RE = re.compile(r"<(?:path|engine|engine-plugin|user|host|name|email|ip|term|case|secret)>")


def _neutral(text):
    """The redactor's own placeholders (<user>, <path>...) are not markup or role tags; screen without them."""
    return PLACEHOLDER_RE.sub("_", text)


def screen_prose(text, where):
    """Lesson fields and notes, after redaction."""
    text = _neutral(text)
    out = []
    for rx in QUOTE_RES:
        for m in rx.finditer(text):
            if len(m.group(1).split()) >= 6:
                out.append(_reason("VERBATIM_QUOTE", where, "a quoted passage of 6+ words may be conversation text - "
                                   f"paraphrase it in your own words: {_excerpt(text, m.start(), m.end())!r}"))
                break
    if BLOCKQUOTE_RE.search(text):
        out.append(_reason("VERBATIM_QUOTE", where, "a block quote may be conversation text - paraphrase it"))
    for rx in INJECTION_ANY + INJECTION_PROSE:
        m = rx.search(text)
        if m:
            out.append(_reason("INJECTION", where, "text addressed to an AI or a shell command in prose: "
                               f"{_excerpt(text, m.start(), m.end())!r}"))
            break
    m = MARKUP_RE.search(text)
    if m:
        out.append(_reason("MARKUP", where, f"images, HTML or hidden comments are not allowed: "
                           f"{_excerpt(text, m.start(), m.end())!r}"))
    out += _embedded_data(text, where)
    for u in _urls(text):
        host = u.split("//", 1)[1].split("/", 1)[0]
        if "?" in u or "@" in host or ("#" in u and "=" in u.split("#", 1)[1]):
            out.append(_reason("URL_DATA", where, "a link with a query, fragment data or user part can carry data; "
                               "link the plain page"))
            break
    return out


def _added_lines(diff):
    return [ln[1:] for ln in diff.splitlines() if ln.startswith("+") and not ln.startswith("+++")]


def screen_diff(diff, where, rel):
    """Tool diffs, after redaction: AI-addressed text, data blobs; risky code is not refused but marked."""
    out, attention = [], []
    added = _neutral("\n".join(_added_lines(diff)))
    for rx in INJECTION_ANY:
        m = rx.search(added)
        if m:
            out.append(_reason("INJECTION", where, f"text addressed to an AI: {_excerpt(added, m.start(), m.end())!r}"))
            break
    if rel.endswith(".md"):
        m = MARKUP_RE.search(added)
        if m:
            out.append(_reason("MARKUP", where, "images, HTML or hidden comments are not allowed"))
    out += _embedded_data(added, where, added.splitlines())
    for construct, rx in ATTENTION_RES.items():
        if rx.search(added):
            attention.append({"where": where, "construct": construct})
    return out, attention


def _strings(obj, where):
    if isinstance(obj, str):
        yield where, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from _strings(v, f"{where}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _strings(v, f"{where}[{i}]")


def _map_strings(obj, fn):
    if isinstance(obj, str):
        return fn(obj)
    if isinstance(obj, dict):
        return {k: _map_strings(v, fn) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_map_strings(v, fn) for v in obj]
    return obj


def unredacted(obj, where, ids=None):
    """Defence in depth on the finished package: any absolute path or identity left is a refusal."""
    out = []
    for w, s in _strings(obj, where):
        if any(rx.search(s) for rx in PATH_RES) or FILE_URL_RE.search(s):
            out.append(_reason("UNREDACTED_PATH", w, "an absolute path is still present"))
        if EMAIL_RE.search(s) or IP_RE.search(s):
            out.append(_reason("UNREDACTED_IDENTITY", w, "an e-mail address or IP address is still present"))
        if ids:
            if _norm(ids["home"]) and _norm(ids["home"]) in _norm(s):
                out.append(_reason("LEAK", w, "the home folder is still present"))
            for cat in ("users", "hosts", "names", "emails", "terms"):
                if any(_word_re(t).search(s) for t in ids[cat]):
                    out.append(_reason("LEAK", w, f"one of your {cat} is still present"))
    return out


# ---------------------------------------------------------------- lesson schema (mirrors schema/lesson.schema.json)
def _check_rel(rel, cfg, where):
    r = rel.replace("\\", "/")
    parts = r.split("/")
    if (not REL_RE.match(r) or r.startswith("/") or re.match(r"^[A-Za-z]:", rel) or ".." in parts
            or len(parts) < 2 or parts[0] not in cfg["diffable_dirs"]):
        return [_reason("OUTSIDE_ALLOWLIST", where, "only files under " + ", ".join(f"{d}/" for d in cfg["diffable_dirs"])
                        + " of the engine can be reported (never cases/, eval/ or anything outside the engine)")]
    ext = PurePosixPath(r).suffix.lower()
    if ext in FORBIDDEN_EXTENSIONS or ext not in cfg["diffable_extensions"]:
        return [_reason("FORBIDDEN_TYPE", where, f"'{ext}' files are not lesson material")]
    return []


def _str_field(L, key, where, maxlen, errs, required=True, minlen=1):
    v = L.get(key)
    if v is None:
        if required:
            errs.append(_reason("SCHEMA", f"{where}.{key}", "required"))
        return
    if not isinstance(v, str) or not (minlen <= len(v) <= maxlen):
        errs.append(_reason("SCHEMA", f"{where}.{key}", f"must be text of {minlen}-{maxlen} characters"))


def _keys(d, allowed, required, where, errs):
    if not isinstance(d, dict):
        errs.append(_reason("SCHEMA", where, "must be an object"))
        return False
    extra, missing = set(d) - set(allowed), set(required) - set(d)
    if extra:
        errs.append(_reason("SCHEMA", where, "unknown field(s): " + ", ".join(sorted(extra))))
    if missing:
        errs.append(_reason("SCHEMA", where, "missing field(s): " + ", ".join(sorted(missing))))
    return not extra and not missing


def validate_lessons(doc, cfg, where="lessons"):
    errs = []
    if not isinstance(doc, dict) or set(doc) != {"lessons"} or not isinstance(doc.get("lessons"), list):
        return [_reason("SCHEMA", where, "the file must be {\"lessons\": [ ... ]} and nothing else")]
    lessons = doc["lessons"]
    if not 1 <= len(lessons) <= cfg["limits"]["max_lessons"]:
        errs.append(_reason("SCHEMA", where, f"1-{cfg['limits']['max_lessons']} lessons per package"))
    for i, L in enumerate(lessons):
        w = f"{where}[{i}]"
        if not _keys(L, LESSON_FIELDS, LESSON_REQUIRED, w, errs):
            continue
        if not (isinstance(L["id"], str) and ID_RE.match(L["id"])):
            errs.append(_reason("SCHEMA", f"{w}.id", "letters, digits and . _ # - only, up to 64"))
        if L["kind"] not in KINDS:
            errs.append(_reason("SCHEMA", f"{w}.kind", "one of " + ", ".join(KINDS)))
        if L["target"] not in cfg["lesson_targets"]:
            errs.append(_reason("SCHEMA", f"{w}.target", "one of " + ", ".join(cfg["lesson_targets"])))
        _str_field(L, "title", w, 120, errs)
        _str_field(L, "statement", w, 1500, errs)
        ev = L["evidence"]
        if not isinstance(ev, list) or not 1 <= len(ev) <= 10:
            errs.append(_reason("SCHEMA", f"{w}.evidence", "1-10 evidence items (a lesson cites its log entry)"))
        else:
            for j, e in enumerate(ev):
                we = f"{w}.evidence[{j}]"
                if not _keys(e, ["log_ref", "summary", "measured"], ["log_ref", "summary"], we, errs):
                    continue
                if not (isinstance(e["log_ref"], str) and LOGREF_RE.match(e["log_ref"])):
                    errs.append(_reason("SCHEMA", f"{we}.log_ref", "a log reference like METHOD.md#92"))
                _str_field(e, "summary", we, 500, errs)
                if "measured" in e:
                    m = e["measured"]
                    if _keys(m, ["metric", "before", "after", "unit"], ["metric"], f"{we}.measured", errs):
                        _str_field(m, "metric", f"{we}.measured", 60, errs)
                        _str_field(m, "unit", f"{we}.measured", 20, errs, required=False, minlen=0)
                        for k in ("before", "after"):
                            if k in m and not (m[k] is None or (isinstance(m[k], (int, float))
                                                               and not isinstance(m[k], bool))):
                                errs.append(_reason("SCHEMA", f"{we}.measured.{k}", "a number or null"))
        t = L["toggle"]
        if _keys(t, ["flag", "default"], ["flag", "default"], f"{w}.toggle", errs):
            if not (isinstance(t["flag"], str) and FLAG_RE.match(t["flag"])):
                errs.append(_reason("SCHEMA", f"{w}.toggle.flag", "a flag name like J14_short_name"))
            if t["default"] is not False:
                errs.append(_reason("SCHEMA", f"{w}.toggle.default", "must be false: a reported lesson arrives switched "
                                    "off and only the maintainer decides its default"))
        r = L["ratchet"]
        if _keys(r, ["loosens", "what"], ["loosens"], f"{w}.ratchet", errs):
            if not isinstance(r["loosens"], bool):
                errs.append(_reason("SCHEMA", f"{w}.ratchet.loosens", "true or false"))
            elif r["loosens"]:
                _str_field(r, "what", f"{w}.ratchet", 300, errs)
        if L["kind"] in ("check", "tool") and "proof" not in L:
            errs.append(_reason("SCHEMA", f"{w}.proof", f"a {L['kind']} lesson needs a planted-defect proof"))
        if "proof" in L:
            p = L["proof"]
            if _keys(p, ["planted_defect", "command", "expect"], ["planted_defect", "command", "expect"],
                     f"{w}.proof", errs):
                _str_field(p, "planted_defect", f"{w}.proof", 300, errs)
                if p["expect"] != "fails_on_planted":
                    errs.append(_reason("SCHEMA", f"{w}.proof.expect", "must be fails_on_planted"))
                m = PROOF_CMD_RE.match(p["command"]) if isinstance(p["command"], str) and len(p["command"]) <= 200 else None
                if not m or _check_rel(m.group(1), cfg, ""):
                    errs.append(_reason("SCHEMA", f"{w}.proof.command", "one 'python|bash <engine tool> args' command; "
                                        "no pipes, chaining, quotes or paths outside the engine's tool folders"))
        if "replaces" in L and not (isinstance(L["replaces"], list) and len(L["replaces"]) <= 10
                                    and all(isinstance(x, str) and ID_RE.match(x) for x in L["replaces"])):
            errs.append(_reason("SCHEMA", f"{w}.replaces", "a list of up to 10 lesson ids"))
        if "tool_change" in L and not (isinstance(L["tool_change"], str) and REL_RE.match(L["tool_change"])):
            errs.append(_reason("SCHEMA", f"{w}.tool_change", "the engine-relative path of one reported tool change"))
        if "toolmaking" in L:
            tm = L["toolmaking"]
            if _keys(tm, ["trigger", "caught", "verdict", "why"], [], f"{w}.toolmaking", errs):
                for k in ("trigger", "caught", "why"):
                    _str_field(tm, k, f"{w}.toolmaking", 300, errs, required=False)
                if "verdict" in tm and tm["verdict"] not in ("good", "superseded", "flawed"):
                    errs.append(_reason("SCHEMA", f"{w}.toolmaking.verdict", "good, superseded or flawed"))
    return errs


# ---------------------------------------------------------------- inputs
def _read_input(path, where, allowed_ext, max_bytes, reasons):
    p = Path(path)
    ext = p.suffix.lower()
    if ext in FORBIDDEN_EXTENSIONS or ext not in allowed_ext:
        reasons.append(_reason("FORBIDDEN_TYPE", where, f"'{ext or 'no extension'}' files are not lesson material"))
        return None
    if not p.is_file():
        reasons.append(_reason("MISSING", where, "file not found"))
        return None
    if p.stat().st_size > max_bytes:
        reasons.append(_reason("TOO_LARGE", where, f"over {max_bytes} bytes"))
        return None
    data = p.read_bytes()
    if b"\x00" in data:
        reasons.append(_reason("BINARY", where, "binary content is never lesson material"))
        return None
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        reasons.append(_reason("BINARY", where, "not UTF-8 text"))
        return None


def _inside(child, parent):
    try:
        Path(child).resolve().relative_to(Path(parent).resolve())
        return True
    except ValueError:
        return False


def _fence(text):
    run = max((len(m.group(0)) for m in re.finditer(r"`+", text)), default=0)
    return "`" * max(3, run + 1)


def _sha(b):
    return hashlib.sha256(b).hexdigest()


# ---------------------------------------------------------------- prepare / preview
def prepare(engine_dir, lessons_path, outbox, data_dir, tool_changes=(), notes=(), ids=None, today=None):
    """Build one redacted package in <outbox>/<engine>/<date>-<sha10>/. Raises Refused and writes nothing on any problem."""
    eng = load_engine(engine_dir)
    cfg, lim = eng["config"], eng["config"]["limits"]
    if not cfg.get("accepts_reports"):
        raise Refused([_reason("ENGINE_CLOSED", eng["name"], "this engine does not accept lesson reports")])
    if not is_opted_in(data_dir, eng["name"]):
        raise Refused([_reason("NOT_OPTED_IN", eng["name"], "reporting is off for this engine; switch it on yourself "
                               "with `enable` in your own terminal")])
    outbox = Path(os.path.abspath(outbox))
    if _inside(outbox, eng["dir"]):
        raise Refused([_reason("OUTBOX_LOCATION", "outbox", "the outbox may not be inside the engine")])
    ids = ids or build_identifiers(data_dir=data_dir)
    red = Redactor(ids, eng)
    reasons, attention = [], []

    lessons = []
    raw = _read_input(lessons_path, "lessons", {".json"}, lim["max_package_bytes"], reasons)
    if raw is not None:
        raw_reasons = screen_raw(raw, "lessons")
        reasons += raw_reasons
        if not raw_reasons:
            try:
                doc = json.loads(raw)
            except ValueError as e:
                doc = None
                reasons.append(_reason("SCHEMA", "lessons", f"not valid JSON ({e.msg}, line {e.lineno})"))
            if doc is not None:
                # JSON escapes (​, g...) hide characters from the raw-text screen: screen the decoded strings too
                decoded = [r for w, s in _strings(doc, "lessons") for r in screen_raw(s, w)]
                reasons += decoded
                errs = decoded or validate_lessons(doc, cfg)
                reasons += errs
                if not errs:
                    lessons = _map_strings(doc["lessons"], red.text)
                    for w, s in _strings(lessons, "lessons"):
                        reasons += screen_prose(s, w)

    diffs = []
    if len(tool_changes) > lim["max_tool_changes"]:
        reasons.append(_reason("TOO_LARGE", "tool_changes", f"at most {lim['max_tool_changes']} per package"))
    for rel, path in tool_changes:
        w = f"tool_change {rel}"
        bad = _check_rel(rel, cfg, w)
        if bad:
            reasons += bad
            continue
        rel = rel.replace("\\", "/")
        new = _read_input(path, w, set(cfg["diffable_extensions"]), lim["max_diff_bytes"] * 4, reasons)
        if new is None:
            continue
        shipped = eng["skill"] / rel
        old = shipped.read_text(encoding="utf-8", errors="replace") if shipped.is_file() else ""
        diff = "".join(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                                            fromfile=("a/" + rel) if shipped.is_file() else "/dev/null",
                                            tofile="b/" + rel))
        if not diff:
            reasons.append(_reason("NO_CHANGE", w, "identical to the shipped file"))
            continue
        raw_reasons = screen_raw(diff, w)
        reasons += raw_reasons
        if raw_reasons:
            continue
        diff = red.text(diff)
        if len(diff.encode("utf-8")) > lim["max_diff_bytes"]:
            reasons.append(_reason("TOO_LARGE", w, f"diff over {lim['max_diff_bytes']} bytes"))
            continue
        errs, att = screen_diff(diff, w, rel)
        reasons += errs
        attention += att
        diffs.append({"path": rel, "change": "modified" if shipped.is_file() else "added", "diff": diff})

    note_items = []
    if len(notes) > lim["max_notes"]:
        reasons.append(_reason("TOO_LARGE", "notes", f"at most {lim['max_notes']} per package"))
    for i, path in enumerate(notes, 1):
        w = f"note-{i}"
        text = _read_input(path, w, NOTE_EXTENSIONS, lim["max_note_bytes"], reasons)
        if text is None:
            continue
        raw_reasons = screen_raw(text, w)
        reasons += raw_reasons
        if raw_reasons:
            continue
        text = red.text(text)
        reasons += screen_prose(text, w)
        note_items.append({"name": f"note-{i}.md", "text": text})   # the user's file name is not carried

    diff_paths = {d["path"] for d in diffs}
    for i, L in enumerate(lessons):
        if "tool_change" in L and L["tool_change"] not in diff_paths:
            reasons.append(_reason("SCHEMA", f"lessons[{i}].tool_change", "names no tool change in this package"))
    if reasons:
        raise Refused(reasons)

    links = sorted({u for _, s in _strings([lessons, note_items], "") for u in _urls(s)})
    pkg = {"schema": PACKAGE_SCHEMA, "reporter_version": VERSION, "engine": eng["name"],
           "engine_version": eng["version"], "created": today or date.today().isoformat(), "lessons": lessons,
           "tool_diffs": diffs, "notes": note_items, "links": links, "attention": attention,
           "redactions": dict(sorted(red.counts.items()))}
    leaks = unredacted([lessons, diffs, note_items], "package", ids)
    if leaks:
        raise Refused(leaks)
    text = json.dumps(pkg, indent=1, ensure_ascii=False) + "\n"
    if len(text.encode("utf-8")) > lim["max_package_bytes"]:
        raise Refused([_reason("TOO_LARGE", "package", f"over {lim['max_package_bytes']} bytes")])
    sha = _sha(text.encode("utf-8"))
    pkg_dir = outbox / eng["name"] / f"{pkg['created']}-{sha[:10]}"
    if pkg_dir.exists():
        raise Refused([_reason("ALREADY_EXISTS", "outbox", "this exact package is already in the outbox")])
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "package.json").write_bytes(text.encode("utf-8"))
    preview = _preview(pkg, text, sha)
    (pkg_dir / "PREVIEW.md").write_bytes(preview.encode("utf-8"))
    manifest = {"schema": OUTBOX_SCHEMA, "reporter_version": VERSION, "engine": eng["name"],
                "engine_version": eng["version"], "package_sha256": sha, "package_bytes": len(text.encode("utf-8")),
                "preview_sha256": _sha(preview.encode("utf-8")), "status": "awaiting-approval", "network": "none",
                "_note": "Only package.json would ever be sent. Original (unredacted) values are stored nowhere here."}
    (pkg_dir / "MANIFEST.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    return pkg_dir


def _diff_stats(diff):
    lines = diff.splitlines()
    plus = sum(1 for ln in lines if ln.startswith("+") and not ln.startswith("+++"))
    minus = sum(1 for ln in lines if ln.startswith("-") and not ln.startswith("---"))
    return plus, minus


def _preview(pkg, text, sha):
    out = ["# Lesson package - PREVIEW (nothing has been sent)", "",
           f"Engine **{pkg['engine']}** {pkg['engine_version']} - created {pkg['created']} - package sha256 `{sha}`", "",
           "Status: **awaiting your approval.** This prototype has no network transport: approving only records your",
           "consent in this folder. Only `package.json` (reproduced in full below) would ever be sent.", "",
           "## Summary", ""]
    out.append(f"- {len(pkg['lessons'])} lesson(s):")
    for L in pkg["lessons"]:
        out.append(f"  - `{L['id']}` [{L['kind']} -> {L['target']}] {L['title']} - flag `{L['toggle']['flag']}` "
                   "(arrives OFF)")
        if L["ratchet"]["loosens"]:
            out.append(f"    - **LOOSENS A CHECK:** {L['ratchet']['what']} - needs the maintainer's explicit approval")
    out.append(f"- {len(pkg['tool_diffs'])} tool change(s):"
               + "".join(f"\n  - `{d['path']}` ({d['change']}, +{_diff_stats(d['diff'])[0]} -{_diff_stats(d['diff'])[1]})"
                         for d in pkg["tool_diffs"]))
    out.append(f"- {len(pkg['notes'])} method note(s)")
    if pkg["links"]:
        out.append("- links: " + ", ".join(pkg["links"]))
    if pkg["attention"]:
        out.append("- code the maintainer must review by hand: "
                   + ", ".join(f"{a['construct']} ({a['where']})" for a in pkg["attention"]))
    red = ", ".join(f"{n} {k}" for k, n in pkg["redactions"].items()) or "nothing"
    out += [f"- redacted: {red} (the original values are not stored anywhere in this folder)", "",
            "## Exactly what would be sent (package.json, byte for byte)", ""]
    fence = _fence(text)
    out.append(f"{fence}json\n{text}{fence}")
    out += ["", "## To approve", "",
            "Read everything above. Then, in your own terminal (not through an agent):",
            "`python lesson_reporter.py approve <this folder>` and type the one-time code it shows on your console.",
            "Changing package.json afterwards voids the approval. Delete this folder to withdraw.", ""]
    return "\n".join(out)


# ---------------------------------------------------------------- approval / verify / send / screen
def verify(pkg_dir):
    pkg_dir = Path(pkg_dir)
    manifest = json.loads((pkg_dir / "MANIFEST.json").read_text(encoding="utf-8"))
    sha = _sha((pkg_dir / "package.json").read_bytes())
    intact = sha == manifest["package_sha256"]
    appr = pkg_dir / "APPROVAL.json"
    approved = intact and appr.is_file() and json.loads(appr.read_text(encoding="utf-8")).get("package_sha256") == sha
    return {"intact": intact, "approved": approved}


def approve(pkg_dir, confirm=None):
    """The person approves exactly this package (by its sha256) with a one-time code typed at their console."""
    pkg_dir = Path(pkg_dir)
    if not verify(pkg_dir)["intact"]:
        raise Refused([_reason("TAMPERED", "package.json", "changed since it was prepared; prepare it again")])
    manifest = json.loads((pkg_dir / "MANIFEST.json").read_text(encoding="utf-8"))
    sha = manifest["package_sha256"]
    (confirm or human_confirm)(f"approve package {sha[:12]} ({manifest['engine']}) exactly as shown in its PREVIEW.md")
    if _sha((pkg_dir / "package.json").read_bytes()) != sha:          # changed while the person was looking
        raise Refused([_reason("TAMPERED", "package.json", "changed during approval; nothing approved")])
    (pkg_dir / "APPROVAL.json").write_text(json.dumps(
        {"package_sha256": sha, "approved_on": date.today().isoformat(),
         "how": "one-time code typed at the person's console", "transport": "none (prototype)"}, indent=1) + "\n",
        encoding="utf-8")
    manifest["status"] = "approved-not-sent"
    (pkg_dir / "MANIFEST.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")


def send(pkg_dir):
    raise Refused([_reason("TRANSPORT_DISABLED", "send", "the prototype has no network transport; the package stays "
                           "in the outbox (SPEC: Transport, pending the maintainer's decision)")])


def screen_package(package_json, engine_dir):
    """Maintainer / CI side: re-check a received package.json without knowing the sender. [] = clean.
    The file is untrusted: any malformed shape is a SCHEMA finding, never a crash."""
    try:
        return _screen_package(package_json, engine_dir)
    except (TypeError, AttributeError, KeyError, ValueError) as e:
        return [_reason("SCHEMA", "package", f"malformed package ({type(e).__name__})")]


def _screen_package(package_json, engine_dir):
    eng = load_engine(engine_dir)
    cfg, lim = eng["config"], eng["config"]["limits"]
    raw = Path(package_json).read_bytes()
    if len(raw) > lim["max_package_bytes"]:
        return [_reason("TOO_LARGE", "package", f"over {lim['max_package_bytes']} bytes")]
    try:
        text = raw.decode("utf-8")
        pkg = json.loads(text)
    except (UnicodeDecodeError, ValueError):
        return [_reason("SCHEMA", "package", "not UTF-8 JSON")]
    out = screen_raw(text, "package") + [r for w, s in _strings(pkg, "package") for r in screen_raw(s, w)]
    if not isinstance(pkg, dict) or set(pkg) != set(PACKAGE_FIELDS):
        return out + [_reason("SCHEMA", "package", "fields must be exactly: " + ", ".join(PACKAGE_FIELDS))]
    if pkg["schema"] != PACKAGE_SCHEMA or pkg["engine"] != eng["name"]:
        out.append(_reason("SCHEMA", "package", f"schema must be {PACKAGE_SCHEMA} and engine {eng['name']}"))
    out += validate_lessons({"lessons": pkg["lessons"]}, cfg)
    for w, s in _strings(pkg["lessons"], "lessons"):
        out += screen_prose(s, w)
    if not isinstance(pkg["tool_diffs"], list) or not isinstance(pkg["notes"], list):
        return out + [_reason("SCHEMA", "package", "tool_diffs and notes must be lists")]
    for i, d in enumerate(pkg["tool_diffs"]):
        w = f"tool_diffs[{i}]"
        if not _keys(d, ["path", "change", "diff"], ["path", "change", "diff"], w, out):
            continue
        out += _check_rel(d["path"], cfg, w)
        errs, _ = screen_diff(d["diff"], w, d["path"])
        out += errs
        if len(d["diff"].encode("utf-8")) > lim["max_diff_bytes"]:
            out.append(_reason("TOO_LARGE", w, f"diff over {lim['max_diff_bytes']} bytes"))
    for i, n in enumerate(pkg["notes"]):
        w = f"notes[{i}]"
        if _keys(n, ["name", "text"], ["name", "text"], w, out):
            out += screen_prose(n["text"], w)
    out += unredacted([pkg["lessons"], pkg["tool_diffs"], pkg["notes"]], "package")
    return out


# ---------------------------------------------------------------- CLI
def main(argv=None):
    try:
        sys.stdout.reconfigure(errors="replace")
    except AttributeError:
        pass
    ap = argparse.ArgumentParser(description="Lesson reporter - outbox prototype (no network).")
    ap.add_argument("--data", default=os.environ.get("LESSON_REPORTER_DATA"),
                    help="the reporter's data folder (the skill passes ${CLAUDE_PLUGIN_DATA})")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("status", "enable", "disable"):
        s = sub.add_parser(name)
        s.add_argument("--engine", required=name != "status")
    s = sub.add_parser("prepare")
    s.add_argument("--engine", required=True)
    s.add_argument("--lessons", required=True)
    s.add_argument("--tool-change", action="append", default=[], metavar="REL=PATH")
    s.add_argument("--note", action="append", default=[])
    s.add_argument("--outbox")
    for name in ("show", "approve", "verify", "send"):
        sub.add_parser(name).add_argument("package_dir")
    s = sub.add_parser("screen")
    s.add_argument("package_json")
    s.add_argument("--engine", required=True)
    a = ap.parse_args(argv)
    try:
        if a.cmd in ("status", "enable", "disable", "prepare") and not a.data:
            ap.error("--data DIR is required (or set LESSON_REPORTER_DATA)")
        if a.cmd == "status":
            engines = _read_settings(a.data).get("engines", {})
            names = [load_engine(a.engine)["name"]] if a.engine else sorted(engines)
            for n in names or ["(no engine has been switched on)"]:
                print(f"{n}: {'ON' if is_opted_in(a.data, n) else 'OFF'}")
        elif a.cmd in ("enable", "disable"):
            name = load_engine(a.engine)["name"]
            set_opt_in(a.data, name, a.cmd == "enable")
            print(f"{name}: reporting {'ON' if a.cmd == 'enable' else 'OFF'}")
        elif a.cmd == "prepare":
            changes = []
            for tc in a.tool_change:
                if "=" not in tc:
                    ap.error("--tool-change takes REL=PATH, e.g. tools/frame_fit.py=C:/work/frame_fit.py")
                changes.append(tuple(tc.split("=", 1)))
            pkg = prepare(a.engine, a.lessons, a.outbox or Path(a.data) / "outbox", a.data,
                          tool_changes=changes, notes=a.note)
            print(f"Package written (NOT sent): {pkg}\nRead {Path(pkg) / 'PREVIEW.md'} in full, then approve it yourself "
                  "in your own terminal if you agree.")
        elif a.cmd == "show":
            print((Path(a.package_dir) / "PREVIEW.md").read_text(encoding="utf-8"))
        elif a.cmd == "approve":
            print(f"Approving {Path(a.package_dir).name}. Read its PREVIEW.md in full first; only package.json "
                  "would ever be sent.")
            approve(a.package_dir)
            print("Approved (recorded locally). Nothing was sent: the prototype has no transport.")
        elif a.cmd == "verify":
            print(json.dumps(verify(a.package_dir)))
        elif a.cmd == "send":
            send(a.package_dir)
        elif a.cmd == "screen":
            reasons = screen_package(a.package_json, a.engine)
            for r in reasons:
                print(f"  {r['code']:18s} {r['where']}: {r['detail']}")
            print("SCREEN:", "clean" if not reasons else f"{len(reasons)} problem(s)")
            return 1 if reasons else 0
    except Refused as e:
        print("REFUSED - nothing was written or sent:")
        for r in e.reasons:
            print(f"  {r['code']:18s} {r['where']}: {r['detail']}")
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
