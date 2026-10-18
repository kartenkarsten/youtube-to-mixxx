# YouTube zu Mixxx – Tampermonkey für Firefox/Linux

[MIT-lizenziert](LICENSE) · [Quellcode auf GitHub](https://github.com/kartenkarsten/youtube-to-mixxx)

Das Tampermonkey-Userscript ergänzt auf normalen YouTube-Videoseiten und in YouTube-Suchergebnissen eine Schaltfläche. Sie lädt die Audiospur über `yt-dlp`, konvertiert sie mit `ffmpeg` in MP3 und speichert sie im konfigurierten Ordner. Shorts und Live-Streams werden abgewiesen. Das Userscript bleibt nach der einmaligen Installation in Tampermonkey gespeichert und wird bei passenden YouTube-Seiten automatisch ausgeführt.

## Voraussetzungen

- Linux mit Firefox und installierter Tampermonkey-Erweiterung
- Python 3
- `yt-dlp` und `ffmpeg`
- systemd mit aktivem User-Manager (`systemctl --user`)
- Mixxx 2.5.6, wenn die gespeicherten Titel anschließend in Mixxx verwendet werden sollen

Unter Arch Linux lassen sich Firefox, Mixxx, ffmpeg und Git aus den offiziellen Paketquellen und `yt-dlp` aus dem AUR installieren:

```sh
sudo pacman -S firefox mixxx ffmpeg git
yay -S yt-dlp
```

Tampermonkey kann über [addons.mozilla.org](https://addons.mozilla.org/firefox/addon/tampermonkey/) installiert werden. Das Installationsskript dieses Projekts benötigt keine Root-Rechte und installiert keine Systempakete.

## Installation

1. Tampermonkey und die Systemabhängigkeiten installieren. Repository klonen und den lokalen Dienst einrichten:

   ```sh
   git clone https://github.com/kartenkarsten/youtube-to-mixxx.git
   cd youtube-to-mixxx
   ./install-tampermonkey.sh
   ```

   Das Skript kopiert den Downloader und die HTTP-Brücke nach `~/.local/lib/youtube-to-mixxx/` und richtet `youtube-to-mixxx-http.service` als systemd-User-Dienst ein. Der Dienst wird gestartet und bei künftigen Anmeldungen automatisch aktiviert. Beim ersten Start wird ein zufälliges Bridge-Token angelegt und mit Dateirechten `0600` gespeichert.

2. Das [Userscript direkt über GitHub installieren](https://raw.githubusercontent.com/kartenkarsten/youtube-to-mixxx/main/userscripts/youtube-to-mixxx.user.js). Tampermonkey zeigt die Installationsseite; dort **Installieren** auswählen.

   Wenn du noch die zuvor manuell eingefügte Userscript-Version verwendest, entferne diese zuerst in Tampermonkey, damit nicht die alte Version ohne Token-Anmeldung ausgeführt wird.

3. Falls Firefox oder Tampermonkey nach Zugriff auf `127.0.0.1` fragt, den Zugriff für das Userscript erlauben.

4. Eine normale YouTube-Videoseite oder Suchergebnisseite neu laden. Dort sollte **Als MP3 für Mixxx speichern** erscheinen.

## Lokaler Dienst

Das Userscript kann aus dem Browser heraus keine lokalen Programme starten. Es sendet deshalb den ausgewählten Videolink an die lokale HTTP-Brücke. Diese läuft als User-Dienst und lauscht nur auf `127.0.0.1:8765`. Downloads benötigen ein zufälliges Bearer-Token, das der Dienst pro Installation anlegt. Tampermonkey liest es über einen Endpunkt ohne CORS-Freigabe und speichert es in seinem lokalen Userscript-Speicher; gewöhnliche Webseiten können die Antwort dadurch nicht lesen. Die Token-Datei liegt unter `~/.config/youtube-to-mixxx/bridge-token` mit Dateirechten `0600`. Die Brücke prüft zusätzlich den YouTube-Link und weist normale Anfragen von anderen Website-Ursprüngen ab.

Das Token schützt die lokale Schnittstelle vor gewöhnlichen Cross-Site-Aufrufen. Es ist keine Sicherheitsgrenze gegenüber anderen Programmen oder Browser-Erweiterungen, die bereits mit denselben Benutzerrechten laufen. `yt-dlp` kommuniziert für den Download direkt mit YouTube; es gibt keinen separaten Projektserver.

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

Das Userscript enthält `@updateURL` und `@downloadURL` auf die GitHub-Raw-Datei. Tampermonkey kann neue Versionen anhand der erhöhten `@version` automatisch finden. Für Änderungen am lokalen Dienst:

```sh
git pull
./install-tampermonkey.sh
```

Der Installer kopiert die Dateien und startet den Dienst mit dem aktualisierten Code neu.

## Datenschutz, Nutzung und Abhängigkeiten

- Es gibt keine Analyse-, Telemetrie- oder Projektserver-Übermittlung. Die ausgewählte URL wird lokal verarbeitet; `yt-dlp` ruft YouTube auf.
- Lade nur Inhalte herunter, für deren Speicherung du berechtigt bist, und beachte die geltenden YouTube-Nutzungsbedingungen.
- Dieses Projekt steht unter der MIT-Lizenz. `yt-dlp`, FFmpeg, Firefox, Tampermonkey und Mixxx sind eigenständige Drittanbieterprojekte und werden nicht mit diesem Repository ausgeliefert. Hinweise und Links stehen in [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).
- Sicherheitslücken bitte gemäß [`SECURITY.md`](SECURITY.md) vertraulich melden.

## Veröffentlichung und Maintainer

Der Userscript-Link erwartet den GitHub-Branch `main`:

```text
https://raw.githubusercontent.com/kartenkarsten/youtube-to-mixxx/main/userscripts/youtube-to-mixxx.user.js
```

Bei Änderungen am Userscript die `@version` erhöhen und die Änderungen nach `main` veröffentlichen. Änderungen am lokalen Dienst werden über `install-tampermonkey.sh` verteilt. Vor einem Release Tests ausführen und Installation, HTTP-Dienst sowie einen erfolgreichen Download in Firefox/Tampermonkey praktisch prüfen.

```sh
python -m unittest discover -s tests -v
python -m py_compile local_service/downloader.py local_service/http_bridge.py
node --check userscripts/youtube-to-mixxx.user.js
bash -n install-tampermonkey.sh
```

Das GitHub-Repository `kartenkarsten/youtube-to-mixxx` muss als **öffentliches, leeres Repository** angelegt und der Branch `main` dorthin gepusht werden, bevor der URL-Installationslink erreichbar ist. Ein öffentliches Repository ist erforderlich, damit Tampermonkey das Userscript ohne GitHub-Anmeldung abrufen kann.

Für die erste Veröffentlichung aus diesem lokalen Repository:

```sh
git add -A
git commit -m "Prepare GitHub release"
git push -u origin main
```

## Fehlerbehebung

- **Der Button erscheint nicht:** Prüfen, ob das Userscript in Tampermonkey aktiviert ist und die YouTube-Seite neu laden. Unterstützt werden normale Videos und Suchergebnisse, keine Shorts oder Live-Streams.
- **„Lokaler Dienst nicht erreichbar“:** Status des Dienstes prüfen. Bei einem Fehler `journalctl --user -u youtube-to-mixxx-http.service` ansehen und den Dienst mit `systemctl --user restart youtube-to-mixxx-http.service` neu starten.
- **„Zugriff verweigert“:** Prüfen, ob die Bridge-Token-Datei existiert und der Dienst läuft. Bei einem verlorenen oder ungültigen Token den Dienst stoppen, `~/.config/youtube-to-mixxx/bridge-token` löschen und den Dienst neu starten. Das Userscript ruft beim nächsten Versuch ein neues Token ab.
- **Tampermonkey kann die lokale Adresse nicht aufrufen:** Prüfen, ob der Zugriff auf `127.0.0.1` in Tampermonkey/Firefox erlaubt ist und der Dienst auf Port `8765` läuft.
- **Download oder Konvertierung schlägt fehl:** Prüfen, ob `yt-dlp` und `ffmpeg` installiert sind. YouTube-Änderungen können ein Update von `yt-dlp` erfordern.
- **Mixxx zeigt den Titel nicht:** Prüfen, ob der Downloadordner in einem Mixxx-Musikordner liegt, danach **Library → Rescan Library** ausführen.
- **Protokolle:** Fehler und Zugriffe der HTTP-Brücke stehen im systemd-Journal des User-Dienstes.

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
