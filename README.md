# YouTube zu Mixxx (Firefox, Linux)

Die Erweiterung fügt auf normalen YouTube-Videoseiten und in YouTube-Suchergebnissen eine Schaltfläche hinzu. Ein Klick lädt nur die Audiospur über `yt-dlp`, konvertiert sie mit `ffmpeg` in MP3 und speichert sie im konfigurierten Ordner. Shorts und Live-Streams werden abgewiesen. Downloads sind auf einzelne Videos beschränkt; ein Download-Archiv verhindert erneute Downloads.

## Voraussetzungen

- Linux und Firefox 109 oder neuer (Manifest V3; auf dem Zielsystem ist Firefox 156 vorhanden)
- Mixxx 2.5.6
- `yt-dlp` und `ffmpeg`
- Python 3

Unter Arch Linux kommen Firefox, Mixxx und ffmpeg aus den offiziellen Paketquellen; `yt-dlp` wird aus dem AUR installiert. Zum Beispiel:

```sh
sudo pacman -S firefox mixxx ffmpeg
yay -S yt-dlp
```

Das Installationsskript installiert keine Pakete und benötigt keine Root-Rechte.

## Installation

1. Im Repository ausführen:

   ```sh
   ./install.sh
   ```

   Das Skript kopiert den Native-Messaging-Host nach `~/.local/lib/youtube-to-mixxx/` und registriert ihn für Firefox unter `~/.mozilla/native-messaging-hosts/`. Es benötigt `python3`, `yt-dlp`, `ffmpeg` und `firefox` im `PATH`.

2. In Firefox `about:debugging#/runtime/this-firefox` öffnen, **Temporäres Add-on laden…** auswählen und `extension/manifest.json` aus diesem Repository laden.

   Firefox entfernt temporär geladene Add-ons beim Beenden. Für eine dauerhafte Installation muss die Erweiterung als XPI über AMO signiert werden; lokal Entwickelnde können Firefox Developer Edition/Nightly nutzen.

3. Die Erweiterungs-Einstellungen öffnen und den Download-Ordner prüfen. Standard ist `~/Musik/YouTube`. Änderungen werden lokal unter `~/.config/youtube-to-mixxx/config.json` mit Dateirechten `0600` gespeichert.

4. Die Erweiterung testen, indem eine normale YouTube-Videoseite oder eine YouTube-Suchergebnisseite geöffnet wird.

## Mixxx-Musikordner und Aktualisierung

Der Download-Ordner muss innerhalb eines Mixxx-Musikordners liegen. Diesen kannst du in Mixxx unter **Preferences → Library → Music Directories** eintragen. Mit dem Standardziel `~/Musik/YouTube` muss also mindestens `~/Musik` als Musikordner hinzugefügt werden.

Auf dem untersuchten System war in der lokalen Mixxx-Datenbank zum Zeitpunkt der Umsetzung nur `~/Downloads` als Musikordner eingetragen. Die Datenbank wurde dafür ausschließlich lesend geprüft und nicht verändert. Bis `~/Musik` in Mixxx eingetragen ist, empfiehlt sich als Alternative ein Pfad unter `~/Downloads`.

Die Mixxx-2.5-Dokumentation nennt **Library → Rescan Library** als unterstützten Weg, neu hinzugefügte Dateien bei laufendem Mixxx zu importieren. Eine unterstützte Kommandozeilen-, DBus- oder sonstige Remote-Schnittstelle zum Starten dieses Scans ist für Mixxx 2.5.6 nicht dokumentiert. Die Erweiterung manipuliert deshalb weder Mixxx-Datenbankdateien noch Mixxx-Prozesse. Nach Erfolg zeigt der Button den Hinweis, in Mixxx **Library → Rescan Library** auszuführen. `Rescan on startup` ist zusätzlich als automatische, aber verzögerte Alternative verfügbar.

## Qualität, Metadaten und Duplikate

- MP3 mit 192 kbit/s, konvertiert durch ffmpeg
- yt-dlp bettet verfügbare Video-Metadaten und Thumbnail-Cover in die MP3 ein; der Uploader wird als Interpret verwendet
- Dateiname: `Titel [YouTube-ID].mp3`
- yt-dlp-Archiv unter `~/.config/youtube-to-mixxx/downloaded-ids.txt`; bereits erfasste Videos werden nicht erneut geladen
- Video-URL und Host werden sowohl in der Erweiterung als auch im Native-Messaging-Host geprüft; der Host akzeptiert ausschließlich HTTPS-Watch-URLs von YouTube
- yt-dlp wird als Argumentliste ohne Shell aufgerufen

## Fehlerbehebung

- **„Native host not found“**: `./install.sh` erneut ausführen und Firefox neu starten. `~/.mozilla/native-messaging-hosts/org.mixxx.youtube_downloader.json` muss auf die installierte Hostdatei zeigen.
- **Native-Host-Berechtigung verweigert**: Add-on-ID im Manifest (`youtube-to-mixxx@local`) und `allowed_extensions` im Native-Host-Manifest müssen übereinstimmen.
- **Download oder Konvertierung scheitert**: Prüfen, ob `yt-dlp` und `ffmpeg` in einer Shell im `PATH` liegen. YouTube kann Änderungen vornehmen, die ein Update von yt-dlp erfordern.
- **Mixxx zeigt den Titel nicht**: Sicherstellen, dass der Download-Ordner innerhalb eines Mixxx-Musikordners liegt, dann **Library → Rescan Library** auswählen.
- **Protokolle**: Native-Host-Fehler gehen an `stderr` und sind in der Firefox-Browserkonsole (`Strg+Umschalt+J`) sichtbar. Der Host speichert keine zusätzlichen Download-Protokolle.

## Entwicklung und Tests

```sh
python -m unittest discover -s tests -v
python -m py_compile native_host/youtube_to_mixxx.py
node --check extension/background.js
node --check extension/content.js
node --check extension/options.js
```

Die automatisierten Tests prüfen Host-Validierung, Einstellungen, Native-Messaging-Framing und Syntax. Ein End-to-End-Download samt Mixxx-GUI-Sichtbarkeit hängt von einem geeigneten YouTube-Video ab und wurde nicht gegen ein fest eingebautes Testvideo ausgeführt.

## Deinstallation

`./uninstall.sh` entfernt Native-Host, Host-Manifest und lokale Konfiguration. Die Firefox-Erweiterung zusätzlich unter `about:addons` entfernen.
