#!/bin/sh
# Install (or reinstall) the macOS LaunchAgent that runs run.sh every 60 seconds.
#   ./install-launchd.sh            install and start
#   ./install-launchd.sh uninstall  stop and remove
set -eu
DIR=$(cd "$(dirname "$0")" && pwd)
LABEL=io.github.times-gate-dashboard
PLIST=$HOME/Library/LaunchAgents/$LABEL.plist
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
if [ "${1:-}" = uninstall ]; then rm -f "$PLIST"; echo "removed $LABEL"; exit 0; fi
mkdir -p "$HOME/Library/LaunchAgents" "$HOME/Library/Logs"
cat > "$PLIST" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key><array><string>/bin/sh</string><string>$DIR/run.sh</string></array>
  <key>StartInterval</key><integer>60</integer>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>$HOME/Library/Logs/times-gate-dashboard.log</string>
  <key>StandardErrorPath</key><string>$HOME/Library/Logs/times-gate-dashboard.log</string>
</dict></plist>
PL
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "installed $LABEL; log: ~/Library/Logs/times-gate-dashboard.log"
