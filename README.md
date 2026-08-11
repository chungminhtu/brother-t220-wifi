# brother-t220-wifi

Turn a Mac into a WiFi/AirPrint print server for the **Brother DCP-T220**
(USB-only printer, no macOS CUPS driver). Any iPhone/Android/Mac on the same
WiFi can then print to it.

## Why this exists

- The DCP-T220 only understands Brother's proprietary `vnd.brother-hbp` format.
- Brother ships no macOS CUPS driver; the bundled iPrint&Scan bridge
  (`HttpToUsb`) answers IPP `Print-Job` with a **fake success** (no job-id,
  nothing prints) — verified by packet capture. Dead end.
- The official **Linux** driver does produce `hbp`. It runs fine inside Docker
  (x86_64 emulation), consuming PostScript and emitting `hbp`.

## Architecture

```
phone / other Mac (AirPrint, same WiFi)
        │ IPP :631
        ▼
CUPS shared queue "DCP-T220-WiFi"  (PostScript PPD, renders any input to PS)
        │ socket://127.0.0.1:9101  (JetDirect-style: stream + close = job)
        ▼
brhbpd.py daemon  (LaunchAgent com.local.brhbpd)
        │ docker run brfilter      (official Brother Linux filter, PS → hbp)
        ▼
CUPS queue "DCP-T220"  →  usb://Brother/DCP-T220  →  paper
```

A second LaunchAgent (`com.local.brhbpd-airprint`) advertises an
AirPrint-complete Bonjour record (URF key, PDF pdl) so iOS/Android always
discover the printer.

## Install

```bash
./install.sh
```

Prerequisites on the host Mac:

- Docker (OrbStack or Docker Desktop) installed and running
- DCP-T220 plugged in via USB, powered on
- macOS python3 (preinstalled)

The Brother driver deb is downloaded from Brother's official server during
`docker build`; it is not redistributed in this repo.

## Use

- From the Mac: print to **DCP-T220-WiFi**
- From iPhone/iPad: Share → Print → `DCP-T220-WiFi @ <Mac name>`
- From Android: system print dialog (install *Mopria Print Service* if the
  printer does not appear)
- Keep the Mac awake and Docker running; the daemon logs to
  `~/.local/brhbp/brhbpd.log`

## Uninstall

```bash
./uninstall.sh
```

## Notes

- Queue `DCP-T220` (raw USB) is internal — do not print to it directly.
- Paper size defaults to A4 (change in `docker/Dockerfile` sed line and PPD).
- CUPS may log `client-error-charset-not-supported` for a duplicate
  Print-Job retry from Android's spooler; the first job goes through.
