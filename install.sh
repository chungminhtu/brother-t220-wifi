#!/bin/bash
# Brother DCP-T220 WiFi/AirPrint print server installer for macOS.
#
# Turns this Mac into a print server for the USB-only DCP-T220 so any
# phone/Mac on the same WiFi can print (AirPrint/IPP).
#
# Chain: shared CUPS queue "DCP-T220-WiFi" -> local daemon :9101
#        -> Docker (official Brother Linux filter) -> hbp -> USB queue.
#
# Requirements: Docker (OrbStack/Docker Desktop) running, printer plugged
# in via USB and powered on, python3 (ships with macOS).
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/.local/brhbp"
AGENTS="$HOME/Library/LaunchAgents"

echo "==> Checking prerequisites"
command -v docker >/dev/null || { echo "ERROR: docker not found. Install OrbStack or Docker Desktop."; exit 1; }
docker info >/dev/null 2>&1 || { echo "ERROR: docker daemon not running."; exit 1; }

USB_URI=$(lpinfo -v 2>/dev/null | awk '/direct usb:\/\/Brother\/DCP-T220/ {print $2; exit}')
[ -n "$USB_URI" ] || { echo "ERROR: DCP-T220 not found on USB. Plug it in and power it on."; exit 1; }
echo "    printer: $USB_URI"

echo "==> Building Brother filter image (downloads official driver)"
docker build --platform linux/amd64 -t brfilter "$DIR/docker"

echo "==> Installing daemon"
mkdir -p "$DEST"
cp "$DIR/brhbpd.py" "$DEST/brhbpd.py"
cp "$DIR/DCP-T220-WiFi.ppd" "$DEST/DCP-T220-WiFi.ppd"

DOCKER_BIN="$(command -v docker)"
/usr/bin/sed -i '' "s#^DOCKER = .*#DOCKER = \"$DOCKER_BIN\"#" "$DEST/brhbpd.py"

echo "==> Creating CUPS queues"
lpadmin -p DCP-T220 -v "$USB_URI" -E -o printer-is-shared=false 2>/dev/null || true
lpadmin -p DCP-T220-WiFi -v 'socket://127.0.0.1:9101' \
        -P "$DEST/DCP-T220-WiFi.ppd" -o PageSize=A4 \
        -o printer-error-policy=retry-job -o printer-is-shared=true -E
cupsctl --share-printers

echo "==> Installing LaunchAgents (daemon + AirPrint advertisement)"
UID_NUM=$(id -u)
for tmpl in com.local.brhbpd.plist com.local.brhbpd-airprint.plist; do
    sed "s#__HOME__#$HOME#g" "$DIR/launchagents/$tmpl" > "$AGENTS/$tmpl"
    launchctl bootout "gui/$UID_NUM/${tmpl%.plist}" 2>/dev/null || true
    launchctl bootstrap "gui/$UID_NUM" "$AGENTS/$tmpl"
done

sleep 2
if nc -z 127.0.0.1 9101 2>/dev/null; then
    echo "==> OK. Daemon listening on :9101."
else
    echo "WARNING: daemon not listening yet; check $DEST/brhbpd.log"
fi

echo
echo "Done. Print to 'DCP-T220-WiFi' from this Mac, or from any phone/Mac"
echo "on the same WiFi (AirPrint: 'DCP-T220-WiFi @ $(scutil --get ComputerName)')."
echo "Keep this Mac awake and Docker running."
echo "Optional test:  lp -d DCP-T220-WiFi /etc/hosts"
