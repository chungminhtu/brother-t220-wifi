# CLAUDE.md — brother-t220-wifi

Project instructions and current deployment state for this repo.
Public repo: https://github.com/chungminhtu/brother-t220-wifi

## Standing workflow rule (every change, no asking)

Any change to code/config here runs the FULL cycle:
1. Update **README** if behavior/architecture changes (architecture change = MUST update README, incl. mermaid diagrams).
2. **Commit + push** — NO `Co-Authored-By` / Claude / Anthropic anywhere in message or files.
3. `./build.sh <version>` → new DMG.
4. New **GitHub release** (tag + attach DMG), include DMG SHA-256.
5. **Install prod** on this Mac from the clean pkg (`installer -pkg`, sudo), then verify.

The LaunchAgent runs `/Library/PrintServer/brhbp/brhbpd.py`. Editing the
`~/.local` copy has NO effect — always ship via the pkg or copy into `/Library`.
No print tests needed; the user prints themselves.

## Current deployed state (as of v2.1.0, 2026-08-15)

- **Prod on this Mac** = clean pkg **v2.1.0**:
  - CUPS backend `/usr/libexec/cups/backend/brhbp` — `root:wheel 0755`.
  - Shared queue `DCP-T220-WiFi` → device URI `brhbp://127.0.0.1:9101`.
  - Daemon `brhbpd` listening on `127.0.0.1:9101` (under `caffeinate -si`, KeepAlive).
  - mono/color routing verified (`print-color-mode` → GRAYSCALE / COLOR).
- **README** updated: sequence diagram has the color/mono branch, speed table
  28/11 ppm, backend added to the install diagram.
- **Release v2.1.0**: DMG SHA-256 `fc06bea6063984d0a494df73049e54e47983ca0622d7dc0543a720f629a6171f`.
- **Commit + tag pushed**, history clean (0 co-author).

## Architecture (one line)

Phone/Mac (AirPrint) → CUPS queue `DCP-T220-WiFi` (PDF passthrough) → `brhbp`
backend (reads color mode) → `brhbpd` daemon :9101 → macOS `cupsfilter`
(PDF→PWG, color or gray) → PJL wrap → raw USB queue `DCP-T220` → printer.
No Docker, no Brother software runs. macOS-only.

## Speed facts (Brother spec, verified)

Draft: 28 ppm B&W / 11 ppm color. Normal: 16 / 9. B&W is the printer's hardware
ceiling; software cannot exceed it. Default quality = DRAFT; color chosen per job.
