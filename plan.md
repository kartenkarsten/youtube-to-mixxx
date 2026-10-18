# Implementierungsplan: YouTube zu Mixxx mit Tampermonkey

## Ziel

Ein Tampermonkey-Userscript fügt auf YouTube-Videoseiten und Suchergebnissen einen Button hinzu. Darüber wird die Audiospur eines normalen Videos als MP3 heruntergeladen und in einem Mixxx-Musikordner abgelegt.

## Anforderungen

- Zielsystem: Linux/Arch Linux, Firefox mit Tampermonkey und Mixxx 2.5.6.
- Unterstützt werden normale YouTube-Videos, keine Shorts oder Live-Streams.
- Ein Klick startet den Download ohne weitere Dialoge.
- Standardziel: `~/Musik/YouTube`; konfigurierbar in `~/.config/youtube-to-mixxx/config.json`.
- Dateien sollen von Mixxx während eines laufenden Programms auffindbar gemacht werden können.
- Nach einem erfolgreichen Download oder einem erkannten Duplikat wird der Button deaktiviert.

## Architektur

1. **Tampermonkey-Userscript** (`userscripts/youtube-to-mixxx.user.js`)
   - Fügt die Aktion auf normalen Videoseiten und in Suchergebnissen ein.
   - Sendet die ausgewählte Video-URL an die lokale HTTP-Brücke.
   - Zeigt Download-Erfolg, Duplikate und Fehler an.
2. **Lokale HTTP-Brücke und Downloader** (`local_service/`)
   - Läuft als systemd-User-Dienst und bindet ausschließlich an `127.0.0.1:8765`.
   - Weist normale Requests von anderen Website-Ursprüngen ab und validiert YouTube-URLs.
   - Ruft `yt-dlp` und `ffmpeg` ohne Shell-Interpolation auf und legt MP3, Metadaten und Cover im konfigurierten Zielordner ab.
   - Nutzt ein Archiv unter `~/.config/youtube-to-mixxx/downloaded-ids.txt`, um erneute Downloads zu verhindern.
3. **Installation und Dokumentation**
   - `install-tampermonkey.sh` installiert den lokalen Dienst und aktiviert den systemd-User-Dienst.
   - Die README beschreibt Installation, Konfiguration, Betrieb und Fehlerbehebung.

## Mixxx-Aktualisierung

Für Mixxx 2.5.6 ist kein unterstützter Remote-Aufruf zum Starten eines Bibliotheksscans dokumentiert. Nach einem Download ist deshalb **Library → Rescan Library** manuell auszuführen oder **Rescan on startup** zu verwenden. Mixxx-Datenbankdateien werden nicht direkt verändert.

## Verifikation

- Automatisierte Tests für URL-Validierung, Konfiguration, Downloader-Fehler und Zugriffskontrolle der HTTP-Brücke.
- Syntaxprüfungen für Python und das Userscript.
- Ein echter YouTube-Download samt Sichtbarkeit in der Mixxx-GUI ist manuell mit einem ausgewählten Video zu prüfen.

## Umsetzungsstand

- Tampermonkey-Userscript mit Buttons auf Videoseiten und Suchergebnissen ist implementiert.
- HTTP-Brücke und Downloader laufen als installierbarer systemd-User-Dienst.
- Button wird nach erfolgreichem Download oder Duplikat deaktiviert; Fehler erlauben einen erneuten Versuch.
- Das Repository enthält für die Browserintegration nur noch das Tampermonkey-Userscript und die dafür benötigten lokalen Dienste.
