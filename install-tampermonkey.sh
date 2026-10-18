#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${HOME}/.local/lib/youtube-to-mixxx"
UNIT_DIR="${HOME}/.config/systemd/user"

for dependency in python3 yt-dlp ffmpeg systemctl; do
  if ! command -v "${dependency}" >/dev/null 2>&1; then
    printf 'Fehlende Abhängigkeit: %s\n' "${dependency}" >&2
    exit 1
  fi
done

install -d -m 700 "${INSTALL_DIR}" "${UNIT_DIR}"
install -m 755 "${ROOT}/native_host/youtube_to_mixxx.py" "${INSTALL_DIR}/youtube_to_mixxx.py"
install -m 755 "${ROOT}/native_host/http_bridge.py" "${INSTALL_DIR}/http_bridge.py"

cat > "${UNIT_DIR}/youtube-to-mixxx-http.service" <<EOF
[Unit]
Description=Lokale HTTP-Brücke für YouTube-zu-Mixxx (Tampermonkey)
After=network.target

[Service]
Type=simple
ExecStart=$(command -v python3) ${INSTALL_DIR}/http_bridge.py
Restart=on-failure
RestartSec=3
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now youtube-to-mixxx-http.service

printf 'Tampermonkey-Brücke installiert und gestartet.\n'
printf 'Userscript zum Importieren: %s/userscripts/youtube-to-mixxx.user.js\n' "${ROOT}"
printf 'Status prüfen: systemctl --user status youtube-to-mixxx-http.service\n'
