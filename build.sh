#!/bin/bash
# Build DCP-T220-WiFi-Installer.dmg containing a double-click .pkg.
set -euo pipefail
cd "$(dirname "$0")"
VERSION="${1:-2.0.0}"
ID="com.local.brhbpd"
BUILD=build
DMG="DCP-T220-WiFi-Installer.dmg"

rm -rf "$BUILD" "$DMG"
mkdir -p "$BUILD/dmgroot"

chmod +x scripts/postinstall payload/Library/PrintServer/brhbp/brhbpd.py

# Component pkg from the payload rooted at / (installs into /Library/...).
pkgbuild --root payload \
         --identifier "$ID" \
         --version "$VERSION" \
         --scripts scripts \
         --install-location / \
         "$BUILD/component.pkg"

# Product pkg (double-clickable installer UI).
productbuild --package "$BUILD/component.pkg" \
             --identifier "$ID.installer" \
             --version "$VERSION" \
             "$BUILD/dmgroot/DCP-T220-WiFi-Installer.pkg"

cp README.md "$BUILD/dmgroot/README.md" 2>/dev/null || true

hdiutil create -volname "DCP-T220 WiFi Installer" \
               -srcfolder "$BUILD/dmgroot" -ov -format UDZO "$DMG"

echo "Built $DMG"
