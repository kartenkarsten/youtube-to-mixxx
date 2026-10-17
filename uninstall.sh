#!/usr/bin/env bash
set -euo pipefail

rm -f "${HOME}/.mozilla/native-messaging-hosts/org.mixxx.youtube_downloader.json"
rm -rf "${HOME}/.local/lib/youtube-to-mixxx"
rm -rf "${HOME}/.config/youtube-to-mixxx"
printf 'Native-Messaging-Host und Einstellungen entfernt.\n'
printf 'Die Erweiterung kann zusätzlich in Firefox unter about:addons entfernt werden.\n'
