#!/usr/bin/env python3
"""Docker-free print daemon for Brother DCP-T220 (USB-only).

Listens on 127.0.0.1:9101 (JetDirect-style: one connection = one job,
close = end). Receives PDF from the shared CUPS queue, converts it to
PWG raster with macOS's native cupsfilter, wraps it in the PJL envelope
the printer requires (@PJL ENTER LANGUAGE=PWGRASTER — discovered by
reverse-engineering Brother's Linux filter output), and hands the result
raw to the local CUPS USB queue.

Chain: [shared queue "DCP-T220-WiFi", PDF passthrough PPD]
       -> this daemon -> cupsfilter (PDF -> PWG) -> PJL wrap
       -> lp -o raw -d DCP-T220 -> usb:// -> paper
"""
import os, socket, subprocess, sys, tempfile, time

HOST, PORT = "127.0.0.1", 9101
USB_QUEUE = "DCP-T220"
BASE = os.path.dirname(os.path.abspath(__file__))
RENDER_PPD = os.path.join(BASE, "render.ppd")
LOG = os.path.expanduser("~/Library/Logs/brhbpd.log")

# PJL envelope taken verbatim from Brother's own filter output. {rendermode}
# is filled per job: COLOR (photos) or GRAYSCALE (fast B&W, ~28 ppm vs 11).
PJL_TEMPLATE = ("\x1b%-12345X@PJL \n"
                "@PJL SET PAPER=A4\n"
                "@PJL SET BORDERLESS=OFF\n"
                "@PJL SET JTTOPMARGIN=300\n"
                "@PJL SET JTBOTMARGIN=300\n"
                "@PJL SET JTLEFTMARGIN=300\n"
                "@PJL SET JTRIGHTMARGIN=300\n"
                "@PJL SET RENDERMODE={rendermode}\n"
                "@PJL SET PRINTQUALITY=DRAFT\n"
                "@PJL SET DUPLEX=OFF\n"
                "@PJL SET MEDIATYPE=REGULAR\n"
                "@PJL SET SOURCETRAY=AUTO\n"
                "@PJL SET FIDELITY=TRUE\n"
                "@PJL ENTER LANGUAGE=PWGRASTER\n")
PJL_TRAILER = b"\x1b%-12345X\x1b%-12345X"


def log(msg):
    with open(LOG, "a") as f:
        f.write(f"{time.strftime('%F %T')} {msg}\n")


def ensure_usb_queue():
    """Create the raw USB queue if missing (self-healing on new machines)."""
    if subprocess.run(["/usr/bin/lpstat", "-p", USB_QUEUE],
                      capture_output=True).returncode == 0:
        return True
    r = subprocess.run(["/usr/sbin/lpinfo", "-v"], capture_output=True, timeout=30)
    for line in r.stdout.decode().splitlines():
        if "usb://Brother/DCP-T220" in line:
            uri = line.split()[-1]
            subprocess.run(["/usr/sbin/lpadmin", "-p", USB_QUEUE, "-v", uri,
                            "-E", "-o", "printer-is-shared=false"], capture_output=True)
            log(f"created USB queue {USB_QUEUE} -> {uri}")
            return True
    log("printer not found on USB")
    return False


def read_job(conn):
    """Read one job. Optional first line 'BRHBP1 <color|mono>\\n' from our
    CUPS backend sets the color mode; anything else (a bare PDF) = color."""
    buf = b""
    while b"\n" not in buf and len(buf) < 64:
        chunk = conn.recv(64 - len(buf))
        if not chunk:
            break
        buf += chunk
    mode = "color"
    if buf.startswith(b"BRHBP1 "):
        line, _, rest = buf.partition(b"\n")
        mode = "mono" if b"mono" in line else "color"
        buf = rest
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as fin:
        fin.write(buf)
        total = len(buf)
        while True:
            chunk = conn.recv(65536)
            if not chunk:
                break
            fin.write(chunk)
            total += len(chunk)
        return fin.name, total, mode


def handle(conn):
    pdfname, total, mode = read_job(conn)
    log(f"job received: {total} bytes, mode={mode}")
    if total == 0:
        os.unlink(pdfname)
        return
    prnname = pdfname + ".prn"
    try:
        colormodel = "Gray" if mode == "mono" else "RGB"
        rendermode = "GRAYSCALE" if mode == "mono" else "COLOR"
        r = subprocess.run(
            ["/usr/sbin/cupsfilter", "-p", RENDER_PPD, "-m", "image/pwg-raster",
             "-o", f"ColorModel={colormodel}", "-o", "cupsPrintQuality=Draft", pdfname],
            capture_output=True, timeout=300)
        pwg = r.stdout
        i = pwg.find(b"RaS2")
        if r.returncode != 0 or i < 0:
            log(f"convert FAILED rc={r.returncode} err={r.stderr[-300:]!r}")
            return
        pjl_header = PJL_TEMPLATE.format(rendermode=rendermode).encode()
        with open(prnname, "wb") as f:
            f.write(pjl_header + pwg[i:] + PJL_TRAILER)
        log(f"converted: {os.path.getsize(prnname)} bytes PJL+PWG")
        ensure_usb_queue()
        r2 = subprocess.run(["/usr/bin/lp", "-d", USB_QUEUE, "-o", "raw", prnname],
                            capture_output=True, timeout=60)
        log(f"lp rc={r2.returncode} out={r2.stdout.decode().strip()} err={r2.stderr.decode().strip()}")
    finally:
        for p in (pdfname, prnname):
            try:
                os.unlink(p)
            except OSError:
                pass


def main():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen(2)
    log(f"listening on {HOST}:{PORT} (docker-free)")
    while True:
        conn, _ = srv.accept()
        try:
            handle(conn)
        except Exception as e:
            log(f"error: {e}")
        finally:
            conn.close()


if __name__ == "__main__":
    sys.exit(main())
