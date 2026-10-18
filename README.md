# YouTube zu Mixxx – Tampermonkey für Firefox/Linux

Das Tampermonkey-Userscript ergänzt auf normalen YouTube-Videoseiten und in YouTube-Suchergebnissen eine Schaltfläche. Sie lädt die Audiospur über `yt-dlp`, konvertiert sie mit `ffmpeg` in MP3 und speichert sie im konfigurierten Ordner. Shorts und Live-Streams werden abgewiesen. Das Userscript bleibt nach der einmaligen Installation in Tampermonkey gespeichert und wird bei passenden YouTube-Seiten automatisch ausgeführt.

## Voraussetzungen

- Linux mit Firefox und installierter Tampermonkey-Erweiterung
- Python 3
- `yt-dlp` und `ffmpeg`
- systemd mit aktivem User-Manager (`systemctl --user`)
- Mixxx 2.5.6, wenn die gespeicherten Titel anschließend in Mixxx verwendet werden sollen

Unter Arch Linux lassen sich Firefox, Mixxx und ffmpeg aus den offiziellen Paketquellen und `yt-dlp` aus dem AUR installieren:

```sh
sudo pacman -S firefox mixxx ffmpeg
yay -S yt-dlp
```

Tampermonkey kann über [addons.mozilla.org](https://addons.mozilla.org/firefox/addon/tampermonkey/) installiert werden. Das Installationsskript dieses Projekts benötigt keine Root-Rechte und installiert keine Systempakete.

## Installation

1. Das Repository herunterladen oder klonen und im Projektverzeichnis den lokalen Dienst installieren:

   ```sh
   ./install-tampermonkey.sh
   ```

   Das Skript kopiert den Downloader und die HTTP-Brücke nach `~/.local/lib/youtube-to-mixxx/` und richtet `youtube-to-mixxx-http.service` als systemd-User-Dienst ein. Der Dienst wird gestartet und bei künftigen Anmeldungen automatisch aktiviert.

2. In Firefox Tampermonkey öffnen, **Neues Script erstellen** auswählen und den gesamten Inhalt aus `userscripts/youtube-to-mixxx.user.js` in den Editor kopieren. Das Script speichern.

3. Falls Firefox oder Tampermonkey nach Zugriff auf `127.0.0.1` fragt, den Zugriff für das Userscript erlauben.

4. Eine normale YouTube-Videoseite oder Suchergebnisseite neu laden. Dort sollte **Als MP3 für Mixxx speichern** erscheinen.

## Lokaler Dienst

Das Userscript kann aus dem Browser heraus keine lokalen Programme starten. Es sendet deshalb den ausgewählten Videolink an die lokale HTTP-Brücke. Diese läuft als User-Dienst und lauscht nur auf `127.0.0.1:8765`; sie lädt nichts auf einen externen Server hoch. Die Brücke prüft den YouTube-Link und startet den Downloader. Normale Anfragen von anderen Website-Ursprüngen werden abgewiesen.

Dienststatus und Protokoll lassen sich so prüfen:

```sh
systemctl --user status youtube-to-mixxx-http.service
journalctl --user -u youtube-to-mixxx-http.service
```

## Downloadordner und Mixxx-Bibliothek

Der Standard-Downloadordner ist `~/Musik/YouTube`. Ein anderer Pfad kann in `~/.config/youtube-to-mixxx/config.json` eingetragen werden, zum Beispiel:

```json
{
  "downloadPath": "~/Musik/YouTube"
}
```

Der Zielordner muss innerhalb eines in Mixxx eingetragenen Musikordners liegen. Den Musikordner kannst du in Mixxx unter **Preferences → Library → Music Directories** ergänzen. Für das Standardziel `~/Musik/YouTube` muss mindestens `~/Musik` eingetragen sein.

Mixxx 2.5.6 dokumentiert keinen unterstützten Remote-Aufruf zum Aktualisieren der Bibliothek. Nach einem erfolgreichen Download zeigt der Button daher den Hinweis, in Mixxx **Library → Rescan Library** auszuführen. Alternativ kann **Rescan on startup** neue Titel beim nächsten Programmstart erfassen. Die Anwendung verändert keine Mixxx-Datenbankdateien.

## Downloadverhalten

- Audio wird als MP3 mit 192 kbit/s gespeichert.
- Verfügbare Metadaten und das Thumbnail-Cover werden eingebettet; der Uploader wird als Interpret verwendet.
- Dateiname: `Titel [YouTube-ID].mp3`.
- `yt-dlp` speichert bereits geladene Video-IDs im Archiv `~/.config/youtube-to-mixxx/downloaded-ids.txt` und lädt sie nicht erneut.
- Nach erfolgreichem Download wird der Button auf der aktuellen Seite deaktiviert. Bei einem archivierten Video meldet der Downloader „Bereits heruntergeladen“ und deaktiviert den Button ebenfalls.
- Nach einem Seitenneuladen kann der Button wieder erscheinen. Das Download-Archiv verhindert dabei einen erneuten Download und meldet das Video als bereits geladen.

## Aktualisieren

Nach Änderungen oder einem Update des Repositorys:

1. `./install-tampermonkey.sh` erneut ausführen, um die lokale Brücke und den Downloader zu aktualisieren.
2. Den Inhalt von `userscripts/youtube-to-mixxx.user.js` erneut im Tampermonkey-Editor speichern, falls sich das Userscript geändert hat.
3. Den Dienst bei Bedarf neu starten:

   ```sh
   systemctl --user restart youtube-to-mixxx-http.service
   ```

## Fehlerbehebung

- **Der Button erscheint nicht:** Prüfen, ob das Userscript in Tampermonkey aktiviert ist und die YouTube-Seite neu laden. Unterstützt werden normale Videos und Suchergebnisse, keine Shorts oder Live-Streams.
- **„Lokaler Downloader nicht erreichbar“:** Status des Dienstes prüfen. Bei einem Fehler `journalctl --user -u youtube-to-mixxx-http.service` ansehen und den Dienst mit `systemctl --user restart youtube-to-mixxx-http.service` neu starten.
- **Tampermonkey kann die lokale Adresse nicht aufrufen:** Prüfen, ob der Zugriff auf `127.0.0.1` in Tampermonkey/Firefox erlaubt ist und der Dienst auf Port `8765` läuft.
- **Download oder Konvertierung schlägt fehl:** Prüfen, ob `yt-dlp` und `ffmpeg` installiert sind. YouTube-Änderungen können ein Update von `yt-dlp` erfordern.
- **Mixxx zeigt den Titel nicht:** Prüfen, ob der Downloadordner in einem Mixxx-Musikordner liegt, danach **Library → Rescan Library** ausführen.
- **Protokolle:** Fehler und Zugriffe der HTTP-Brücke stehen im systemd-Journal des User-Dienstes (siehe oben).

## Entwicklung und Tests

```sh
python -m unittest discover -s tests -v
python -m py_compile local_service/downloader.py local_service/http_bridge.py
node --check userscripts/youtube-to-mixxx.user.js
```

Die automatisierten Tests prüfen unter anderem YouTube-URL-Validierung, Einstellungen und Downloader-Verhalten. Ein echter YouTube-Download und der anschließende Sichtbarkeitstest in der Mixxx-GUI müssen mit einem ausgewählten Video manuell durchgeführt werden.

## Deinstallation

1. Das Userscript in Tampermonkey entfernen oder deaktivieren.
2. Den User-Dienst stoppen und aus dem Autostart nehmen:

   ```sh
   systemctl --user disable --now youtube-to-mixxx-http.service
   rm -f ~/.config/systemd/user/youtube-to-mixxx-http.service
   systemctl --user daemon-reload
   ```

3. Die installierten Programmdateien entfernen:

   ```sh
   rm -rf ~/.local/lib/youtube-to-mixxx
   ```

   Die Einstellungen und das Download-Archiv bleiben unter `~/.config/youtube-to-mixxx/` erhalten. Wenn du sie ebenfalls löschen möchtest:

   ```sh
   rm -rf ~/.config/youtube-to-mixxx
   ```
