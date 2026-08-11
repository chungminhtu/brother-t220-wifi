#!/bin/bash
# Remove the DCP-T220 WiFi print server from this Mac.
set -uo pipefail
UID_NUM=$(id -u)
launchctl bootout "gui/$UID_NUM/com.local.brhbpd" 2>/dev/null
launchctl bootout "gui/$UID_NUM/com.local.brhbpd-airprint" 2>/dev/null
rm -f "$HOME/Library/LaunchAgents/com.local.brhbpd.plist" \
      "$HOME/Library/LaunchAgents/com.local.brhbpd-airprint.plist"
lpadmin -x DCP-T220-WiFi 2>/dev/null
rm -rf "$HOME/.local/brhbp"
docker rmi brfilter 2>/dev/null
echo "Removed. (USB queue 'DCP-T220' left in place; delete with: lpadmin -x DCP-T220)"
