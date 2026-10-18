#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
VERSION="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["version"])' "${ROOT}/extension/manifest.json")"
OUTPUT_DIR="${ROOT}/dist"
OUTPUT="${OUTPUT_DIR}/youtube-to-mixxx-${VERSION}.xpi"

command -v zip >/dev/null 2>&1 || { printf 'zip wird zum Paketieren benötigt.\n' >&2; exit 1; }
mkdir -p "${OUTPUT_DIR}"
rm -f "${OUTPUT}"
(cd "${ROOT}/extension" && zip -X -q -r "${OUTPUT}" . -x '*/.DS_Store' '*/Thumbs.db')
printf 'Unsigned XPI erstellt: %s\n' "${OUTPUT}"
printf 'Für die dauerhafte Installation in Firefox Release muss es bei AMO als „unlisted“ signiert werden.\n'
