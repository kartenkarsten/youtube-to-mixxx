# Implementierungsplan: YouTube-zu-Mixxx-Firefox-Erweiterung

## Ziel

Auf einer YouTube-Videoseite erscheint eine Aktion, die den ausgewählten Titel als MP3 in einem konfigurierbaren Verzeichnis ablegt und anschließend die Mixxx-Musikbibliothek aktualisieren lässt.

## Bestätigte Anforderungen

- Zielplattform ist Linux; die Erweiterung wird lokal installiert.
- Zielsystem ist Arch Linux; `yt-dlp` wird aus dem AUR bezogen.
- Ein lokaler Native-Messaging-Host ist akzeptiert.
- Der Button soll auf YouTube-Videoseiten und neben Videos in Suchergebnissen erscheinen.
- Unterstützt werden normale Videos, keine Shorts oder Live-Streams.
- Ein Klick startet den Vorgang unmittelbar.
- Der Zielpfad soll in der Erweiterung konfigurierbar sein; Standard: `~/Musik/YouTube`.
- Der konfigurierte Zielpfad liegt innerhalb eines in Mixxx eingetragenen Musikordners.
- Gewünscht sind sinnvolle Standardwerte für Qualität, Dateiname/Metadaten und Duplikate.
- Mixxx soll währenddessen weiterlaufen. Automatisches Aktualisieren ist bevorzugt; ein manueller Scan ist als Fallback akzeptabel.
- Verwendet wird die Mixxx-Version 2.5.6

## Technische Rahmenbedingungen

- Eine Firefox-WebExtension kann das YouTube-Video nicht selbst in MP3 umwandeln. Dafür braucht es einen lokalen Konverter/Downloader, zum Beispiel `yt-dlp` und `ffmpeg`.
- Eine Extension kann aus Sicherheitsgründen weder beliebige lokale Verzeichnisse beschreiben noch Mixxx direkt steuern. Deshalb wird ein lokal installierter Native-Messaging-Host für diese Aufgaben benötigt.
- Die konkrete, unterstützte Methode zum automatischen Aktualisieren der Mixxx-Bibliothek muss vor der Implementierung geprüft werden. Ein direkter Eingriff in Mixxx-Datenbankdateien ist nicht vorgesehen.
- Die Implementierung wird auf die von euch bestätigten Betriebssysteme, Installationsart und Anforderungen zugeschnitten.

## Vorgeschlagene Architektur

1. **Firefox-Erweiterung (Manifest V3)**
   - Content-Script blendet auf unterstützten YouTube-Videoseiten einen klar beschrifteten Button ein.
   - Der Button übergibt die Video-URL an den Native-Messaging-Host und zeigt Fortschritt, Erfolg oder einen verständlichen Fehler an.
   - Eine Optionsseite konfiguriert die Download-/Konvertierungseinstellungen, soweit diese nicht vom Begleitprogramm verwaltet werden.
2. **Lokaler Begleitdienst (Native Messaging Host)**
   - Prüft eingehende Nachrichten und akzeptiert nur die vorgesehene Aktion und gültige YouTube-URLs.
   - Lädt die Audioquelle herunter, konvertiert sie mit `yt-dlp`/`ffmpeg` in MP3 und speichert sie im konfigurierten Zielverzeichnis.
   - Meldet Status und Ergebnis an die Erweiterung zurück.
   - Stößt nach erfolgreichem Speichern die vereinbarte Mixxx-Aktualisierung an.
3. **Paketierung und Dokumentation**
   - Lokale Installationsanleitung für Erweiterung und Native-Messaging-Host einschließlich externer Abhängigkeiten.
   - Hinweise zur Konfiguration des Zielordners und zu Fehlerbehebung/Protokollen.

## Umsetzungsschritte

1. **Anforderungen festlegen**
   - Mixxx-Musikordner ermitteln und klären, ob der Standard-Zielordner bereits überwacht wird.
2. **Technischen Machbarkeitstest erstellen**
   - Native Messaging in den Zielversionen von Firefox testen.
   - Das vorgesehene AUR-Paket `yt-dlp` und `ffmpeg` mit einem Beispiel testen und Dateinamen, Tags sowie Fehlerfälle festlegen.
   - Einen unterstützten und zuverlässigen Weg zum Aktualisieren der Mixxx-Bibliothek ermitteln und praktisch testen. Falls Mixxx keinen geeigneten Automatisierungsweg bietet, die gewünschte Ersatzlösung mit euch abstimmen.
3. **Firefox-Erweiterung implementieren**
   - Manifest, Berechtigungen, YouTube-Seitenintegration, Button, Optionsseite und Native-Messaging-Kommunikation.
   - Statusanzeige und Behandlung von Abbruch, Duplikaten und Verbindungsfehlern.
4. **Begleitdienst implementieren**
   - Validierte Nachrichtenverarbeitung, Download/MP3-Konvertierung, konfigurierbarer Speicherort und Mixxx-Aktualisierung.
   - Sichere Prozessausführung ohne Shell-Interpolation von Videodaten; klare Fehlermeldungen und begrenzte Protokollierung.
5. **Prüfen und dokumentieren**
   - End-to-End-Test: Button → Download/MP3 → Zielordner → Mixxx sieht den Titel.
   - Tests für ungültige URLs, fehlende Abhängigkeiten, nicht erreichbares Mixxx, Schreibfehler und abgebrochene Downloads.
   - Installation, Konfiguration, unterstützte Plattformen und bekannte Grenzen dokumentieren.

## Verifikation

- Für Mixxx 2.5.6 ist kein unterstützter Remote-Aufruf des Bibliotheksscans dokumentiert. Der manuelle Scan ist deshalb umgesetzt; siehe `README.md`.
- Der End-to-End-Test mit einem konkreten YouTube-Video und der Mixxx-GUI ist noch manuell auszuführen.

## Umsetzungsstand

- Firefox-Erweiterung (Manifest V3) mit Aktionsbuttons auf Videoseiten und Suchergebnissen, Statusmeldungen und Optionsseite implementiert.
- Native-Messaging-Host mit URL-/Videoart-Prüfung, `yt-dlp`/`ffmpeg`, MP3-Metadaten/Cover, Duplikatarchiv und konfigurierbarem Downloadpfad implementiert.
- Host lokal registriert; Nachrichtenrahmen und Konfigurationsantwort wurden mit dem installierten Host geprüft.
- Mixxx 2.5.6, Firefox 156, yt-dlp und ffmpeg auf dem Zielsystem gefunden. Die Mixxx-Dokumentation beschreibt „Library → Rescan Library“, aber keinen unterstützten Remote-Aufruf des Scans; daher zeigt die Erweiterung den manuellen Scan als Fallback an.
- In der vorhandenen Mixxx-Datenbank war `~/Downloads` als Musikordner eingetragen. Für den festgelegten Standard `~/Musik/YouTube` muss `~/Musik` in Mixxx als Musikordner ergänzt werden.
- Automatisierte Tests für URL-Validierung, Einstellungen und Native-Messaging-Framing sind vorhanden. Ein tatsächlicher YouTube-Download und der anschließende Sichtbarkeitstest in der Mixxx-GUI benötigen einen ausgewählten Videolink und bleiben als manueller End-to-End-Test offen.
