#!/usr/bin/env python3
"""JetDirect-style print daemon for Brother DCP-T220 (USB-only).

Listens on 127.0.0.1:9101. Each connection is one job: PostScript in,
connection close ends the job. Converts PS -> vnd.brother-hbp with the
official Brother Linux filter inside Docker (image "brfilter"), then
hands the result raw to the local CUPS USB queue.

Chain: [shared CUPS queue socket://127.0.0.1:9101] -> this daemon
       -> docker brfilter -> lp -o raw -d DCP-T220 -> usb:// -> printer
"""
import socket, subprocess, sys, tempfile, os, time

HOST, PORT = "127.0.0.1", 9101
USB_QUEUE = "DCP-T220"
DOCKER = "/usr/local/bin/docker"
LOG = os.path.expanduser("~/.local/brhbp/brhbpd.log")


def log(msg):
    with open(LOG, "a") as f:
        f.write(f"{time.strftime('%F %T')} {msg}\n")


def handle(conn):
    with tempfile.NamedTemporaryFile(suffix=".ps", delete=False) as ps:
        total = 0
        while True:
            chunk = conn.recv(65536)
            if not chunk:
                break
            ps.write(chunk)
            total += len(chunk)
        psname = ps.name
    log(f"job received: {total} bytes")
    if total == 0:
        os.unlink(psname)
        return
    hbpname = psname + ".hbp"
    try:
        with open(psname, "rb") as fin, open(hbpname, "wb") as fout:
            r = subprocess.run(
                [DOCKER, "run", "--rm", "-i", "--platform", "linux/amd64", "brfilter"],
                stdin=fin, stdout=fout, stderr=subprocess.PIPE, timeout=300)
        size = os.path.getsize(hbpname)
        if r.returncode != 0 or size == 0:
            log(f"convert FAILED rc={r.returncode} size={size} err={r.stderr[-300:]!r}")
            return
        log(f"converted: {size} bytes hbp")
        r2 = subprocess.run(["/usr/bin/lp", "-d", USB_QUEUE, "-o", "raw", hbpname],
                            capture_output=True, timeout=60)
        log(f"lp rc={r2.returncode} out={r2.stdout.decode().strip()} err={r2.stderr.decode().strip()}")
    finally:
        for p in (psname, hbpname):
            try:
                os.unlink(p)
            except OSError:
                pass


def main():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen(2)
    log(f"listening on {HOST}:{PORT}")
    while True:
        conn, addr = srv.accept()
        try:
            handle(conn)
        except Exception as e:
            log(f"error: {e}")
        finally:
            conn.close()


if __name__ == "__main__":
    sys.exit(main())
