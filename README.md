# YouTube zu Mixxx

Dieses Projekt besteht aus einem Tampermonkey-Userscript und einem lokalen Dienst. Das Userscript ergänzt auf normalen YouTube-Videoseiten und in Suchergebnissen einen Button. Der lokale Dienst lädt die Audiospur mit `yt-dlp`, wandelt sie mit `ffmpeg` in MP3 um und speichert sie im gewählten Ordner.

Unterstützt werden normale Videos, keine Shorts oder Live-Streams. Das Projekt steht unter der [MIT-Lizenz](LICENSE).

## Voraussetzungen

- Linux mit systemd und einem aktiven User-Dienstmanager
- Firefox mit installierter [Tampermonkey-Erweiterung](https://addons.mozilla.org/firefox/addon/tampermonkey/)
- Python 3, `yt-dlp` und `ffmpeg`
- Mixxx 2.5.6, falls du die heruntergeladenen Titel in Mixxx verwenden möchtest

Unter Arch Linux kannst du die offiziellen Pakete so installieren:

```sh
sudo pacman -S firefox git mixxx ffmpeg python
```

Installiere `yt-dlp` aus dem AUR mit deinem AUR-Helfer, zum Beispiel `yay -S yt-dlp`. Installiere außerdem Tampermonkey in Firefox, falls es noch nicht installiert ist.

## Erstinstallation

### 1. Lokalen Dienst installieren

Öffne ein Terminal und klone das Repository:

```sh
git clone https://github.com/kartenkarsten/youtube-to-mixxx.git
cd youtube-to-mixxx
./install-tampermonkey.sh
```

Das Skript installiert den Downloader und die HTTP-Brücke in `~/.local/lib/youtube-to-mixxx/` und richtet den systemd-User-Dienst `youtube-to-mixxx-http.service` ein. Es benötigt keine Root-Rechte. Der Dienst wird sofort gestartet und bei zukünftigen Anmeldungen automatisch gestartet.

Prüfe, dass der Dienst läuft:

```sh
systemctl --user status youtube-to-mixxx-http.service
```

### 2. Userscript über URL installieren

Öffne den folgenden Link in Firefox:

[YouTube zu Mixxx in Tampermonkey installieren](https://raw.githubusercontent.com/kartenkarsten/youtube-to-mixxx/main/userscripts/youtube-to-mixxx.user.js)

Tampermonkey zeigt eine Installationsseite. Wähle dort **Installieren**. Erlaube den Zugriff auf `127.0.0.1`, falls Tampermonkey danach fragt. Falls du noch eine ältere, manuell eingefügte Version dieses Scripts hast, entferne diese zuerst in Tampermonkey.

### 3. Installation prüfen

Lade eine normale YouTube-Videoseite oder Suchergebnisseite neu. Neben dem Video sollte **Als MP3 für Mixxx speichern** erscheinen. Der erste Download funktioniert nur, wenn der lokale Dienst läuft.

## Bridge-Token: keine manuelle Eingabe nötig

Das Token verbindet das Userscript mit dem lokalen Dienst. Du musst es **nicht selbst erzeugen, kopieren oder in den Script-Code eintragen**.

1. Beim ersten Start des lokalen Dienstes wird automatisch ein zufälliges Token erzeugt.
2. Es wird lokal unter `~/.config/youtube-to-mixxx/bridge-token` gespeichert. Die Datei ist nur für deinen Benutzer lesbar und schreibbar (`0600`). Das Token bleibt bei Dienst- und Rechnerneustarts erhalten.
3. Beim ersten Download fragt das Tampermonkey-Userscript das Token beim lokalen Dienst ab und speichert es in seinem eigenen Speicher.
4. Bei jedem Download sendet das Userscript das Token zur Authentifizierung an `127.0.0.1`. Der Token-Endpunkt gibt keine CORS-Freigabe, sodass gewöhnliche Webseiten das Token nicht auslesen können.

Das Token wird nicht in GitHub, in den öffentlichen Userscript-Code oder an einen Projektserver übertragen. Gib die Datei `bridge-token` nicht weiter und veröffentliche ihren Inhalt nicht. Das Token schützt gegen gewöhnliche websitebasierte Zugriffe, aber nicht gegen andere Programme oder Browser-Erweiterungen, die bereits mit deinem Benutzerkonto laufen.

### Token neu erzeugen

Falls die Token-Datei gelöscht oder beschädigt wurde, stoppe den Dienst, lösche die Datei und starte den Dienst neu:

```sh
systemctl --user stop youtube-to-mixxx-http.service
rm -f ~/.config/youtube-to-mixxx/bridge-token
systemctl --user start youtube-to-mixxx-http.service
```

Der Dienst erzeugt beim Start ein neues Token. Das Userscript erkennt das alte Token beim nächsten Download, ruft das neue automatisch ab und speichert es.

Wenn der systemd-User-Dienst mit `XDG_CONFIG_HOME` gestartet wird, liegen Token, Einstellungen und Download-Archiv unter `$XDG_CONFIG_HOME/youtube-to-mixxx/` statt unter `~/.config/youtube-to-mixxx/`.

## Downloadordner und Mixxx

Der Standardordner ist `~/Musik/YouTube`. Wenn du einen anderen Ordner möchtest, lege die Datei `~/.config/youtube-to-mixxx/config.json` mit folgendem Inhalt an und ersetze den Pfad:

```json
{
  "downloadPath": "~/Musik/YouTube"
}
```

Der Ordner wird beim Download bei Bedarf angelegt. Er muss innerhalb eines in Mixxx eingetragenen Musikordners liegen. Trage zum Beispiel `~/Musik` in Mixxx unter **Preferences → Library → Music Directories** ein.

Mixxx 2.5.6 bietet keinen dokumentierten unterstützten Remote-Aufruf zum Aktualisieren der Bibliothek. Nach dem Download zeigt der Button deshalb den Hinweis, in Mixxx **Library → Rescan Library** auszuführen. Alternativ kannst du **Rescan on startup** aktivieren. Mixxx-Datenbankdateien werden nicht direkt verändert.

## Downloadverhalten

- MP3 mit 192 kbit/s; verfügbare Metadaten und Thumbnail-Cover werden eingebettet.
- Der Uploader wird als Interpret verwendet; der Dateiname enthält Titel und YouTube-ID.
- Das Archiv `~/.config/youtube-to-mixxx/downloaded-ids.txt` verhindert erneute Downloads desselben Videos.
- Nach Erfolg oder erkanntem Duplikat wird der Button deaktiviert. Nach einem Seitenneuladen kann er wieder erscheinen; das Archiv verhindert weiterhin einen erneuten Download.
- YouTube und Live-Streams werden vom lokalen Downloader geprüft; unterstützt werden nur normale YouTube-Videos.

## Aktualisieren

Tampermonkey kann Userscript-Updates über GitHub automatisch finden. Für Updates des lokalen Dienstes:

```sh
cd ~/youtube-to-mixxx
git pull
./install-tampermonkey.sh
```

Der Installer kopiert die aktualisierten Dateien und startet den Dienst neu.

## Fehlerbehebung

- **Der Button erscheint nicht:** Prüfe, ob Tampermonkey und das Userscript aktiviert sind; lade YouTube anschließend neu.
- **„Lokaler Dienst nicht erreichbar“:** Prüfe den Dienststatus und das Journal:

  ```sh
  systemctl --user status youtube-to-mixxx-http.service
  journalctl --user -u youtube-to-mixxx-http.service
  ```

- **„Zugriff verweigert“:** Prüfe, ob der Dienst läuft. Das Userscript versucht ein ungültiges oder veraltetes Token automatisch zu erneuern. Falls nötig, folge den Schritten unter [Token neu erzeugen](#token-neu-erzeugen).
- **Tampermonkey kann `127.0.0.1` nicht aufrufen:** Erlaube den lokalen Zugriff, falls Firefox oder Tampermonkey danach fragt, und prüfe, ob der Dienst auf Port `8765` läuft.
- **Download oder Konvertierung schlägt fehl:** Prüfe, ob `yt-dlp` und `ffmpeg` installiert sind. Bei Änderungen an YouTube kann ein Update von `yt-dlp` nötig sein.
- **Mixxx zeigt den Titel nicht:** Prüfe, ob der Downloadordner in Mixxx als Musikordner erfasst wird, und führe **Library → Rescan Library** aus.

## Datenschutz und Drittanbieter

Die ausgewählte YouTube-URL wird an den lokalen Dienst auf deinem Rechner übergeben. `yt-dlp` kommuniziert für den Download direkt mit YouTube. Es gibt keine Analyse- oder Telemetrieübertragung und keinen Projektserver.

Lade nur Inhalte herunter, für deren Speicherung du berechtigt bist, und beachte die geltenden YouTube-Nutzungsbedingungen. `yt-dlp`, FFmpeg, Firefox, Tampermonkey und Mixxx sind eigenständige Drittanbieterprojekte und werden nicht mit diesem Repository ausgeliefert. Weitere Hinweise stehen in [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

## Deinstallation

1. Entferne oder deaktiviere **YouTube zu Mixxx** in Tampermonkey.
2. Stoppe den Dienst und entferne seinen Autostart:

   ```sh
   systemctl --user disable --now youtube-to-mixxx-http.service
   rm -f ~/.config/systemd/user/youtube-to-mixxx-http.service
   systemctl --user daemon-reload
   ```

3. Entferne die installierten Programmdateien:

   ```sh
   rm -rf ~/.local/lib/youtube-to-mixxx
   ```

Einstellungen, Token und Download-Archiv bleiben dabei unter `~/.config/youtube-to-mixxx/` erhalten. Wenn du auch diese löschen möchtest:

```sh
rm -rf ~/.config/youtube-to-mixxx
```
