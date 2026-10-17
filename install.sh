#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${HOME}/.local/lib/youtube-to-mixxx"
MANIFEST_DIR="${HOME}/.mozilla/native-messaging-hosts"
HOST_MANIFEST="${MANIFEST_DIR}/org.mixxx.youtube_downloader.json"

for dependency in python3 yt-dlp ffmpeg firefox; do
  if ! command -v "${dependency}" >/dev/null 2>&1; then
    printf 'Fehlende Abhängigkeit: %s\n' "${dependency}" >&2
    exit 1
  fi
done

install -d -m 700 "${INSTALL_DIR}" "${MANIFEST_DIR}"
install -m 755 "${ROOT}/native_host/youtube_to_mixxx.py" "${INSTALL_DIR}/youtube_to_mixxx.py"
python3 - "${INSTALL_DIR}/youtube_to_mixxx.py" "${HOST_MANIFEST}" <<'PY'
import json
import os
import sys
import tempfile

host_path, manifest_path = sys.argv[1:]
manifest = {
    "name": "org.mixxx.youtube_downloader",
    "description": "Lokaler YouTube-zu-Mixxx-Downloader",
    "path": os.path.abspath(host_path),
    "type": "stdio",
    "allowed_extensions": ["youtube-to-mixxx@local"],
}
directory = os.path.dirname(manifest_path)
fd, temporary = tempfile.mkstemp(prefix="host-", dir=directory, text=True)
try:
    with os.fdopen(fd, "w", encoding="utf-8") as output:
        json.dump(manifest, output, ensure_ascii=False, indent=2)
        output.write("\n")
    os.chmod(temporary, 0o600)
    os.replace(temporary, manifest_path)
finally:
    if os.path.exists(temporary):
        os.unlink(temporary)
PY

printf 'Native-Messaging-Host installiert: %s\n' "${HOST_MANIFEST}"
printf 'Erweiterung in Firefox über about:debugging#/runtime/this-firefox laden: %s/extension/manifest.json\n' "${ROOT}"
printf 'Danach Firefox neu starten, falls der Host nicht gefunden wird.\n'
