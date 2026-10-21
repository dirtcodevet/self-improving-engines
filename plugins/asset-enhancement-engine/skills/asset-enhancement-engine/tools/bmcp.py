"""Tiny client for the Blender MCP add-on socket (localhost:9876).

Usage:
  python bmcp.py ping
  python bmcp.py info
  python bmcp.py exec <script.py> [more.py ...]   # run Blender Python, print stdout
  python bmcp.py code "<python source>"
  python bmcp.py shot <out.png> [max_size]        # viewport screenshot

Port: 9876 unless BMCP_PORT is set. A second Blender on its own port lets two cases run side by side without
sharing one scene (woman2, 2026-10-19). Never start a second add-on server on 9876: the add-on binds with
SO_REUSEADDR, which on Windows lets two Blenders share the port and commands land in either one.
"""
import json
import os
import socket
import sys

HOST, PORT = "localhost", int(os.environ.get("BMCP_PORT", "9876"))


def send(cmd_type, params=None, timeout=600):
    s = socket.create_connection((HOST, PORT), timeout=timeout)
    s.sendall(json.dumps({"type": cmd_type, "params": params or {}}).encode("utf-8"))
    buf = b""
    while True:
        chunk = s.recv(65536)
        if not chunk:
            break
        buf += chunk
        try:
            resp = json.loads(buf.decode("utf-8"))
            break
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
    s.close()
    return resp


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    op = sys.argv[1]
    if op == "ping":
        r = send("ping")
    elif op == "info":
        r = send("get_scene_info")
    elif op == "exec":
        src = ""
        for p in sys.argv[2:]:
            with open(p, "r", encoding="utf-8") as f:
                src += f.read() + "\n"
        r = send("execute_code", {"code": src})
    elif op == "code":
        r = send("execute_code", {"code": sys.argv[2]})
    elif op == "shot":
        mx = int(sys.argv[3]) if len(sys.argv) > 3 else 1000
        r = send("get_viewport_screenshot", {"filepath": sys.argv[2], "max_size": mx})
    else:
        print("unknown op", op)
        sys.exit(1)
    if r.get("status") == "success" and isinstance(r.get("result"), dict) and "result" in r["result"] and op in ("exec", "code"):
        print(r["result"]["result"], end="")
    else:
        print(json.dumps(r, indent=1)[:20000])
    if r.get("status") != "success":
        sys.exit(2)


if __name__ == "__main__":
    main()
