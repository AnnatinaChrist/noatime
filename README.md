
Of course! Here's the German translation of the README in a format you can easily copy:

Noatime - RFID Zeiterfassung Anwendung
Projektübersicht
Noatime ist eine RFID-basierte Zeiterfassungsanwendung, die eine einfache Ein- und Ausstempelung über NFC-Karten ermöglicht. Die Anwendung interagiert mit einem PN532 RFID-Reader, verwaltet Verbindungen zu einer Datenbank für das Speichern von Zeitstempeln und unterstützt einen Offline-Modus, falls die Datenbank nicht verfügbar ist.

Funktionen
RFID Zeiterfassung: Verwendet einen NFC RFID-Reader (PN532), um Ein- und Ausstempelzeiten basierend auf RFID-Tag-Scans zu registrieren.
Datenbankintegration: Die Anwendung verbindet sich mit einer MySQL-Datenbank zum Speichern von Zeitstempeln.
Offline-Modus: Wenn die Datenbank nicht verfügbar ist, speichert die Anwendung die Zeitstempel in einer Backup-Datei für eine spätere Verarbeitung.
Health-Check: Periodische Prüfungen stellen sicher, dass der RFID-Reader reagiert. Falls er nicht funktioniert, wird ein Reset des Readers versucht.
Multithreaded-Architektur: Verwendet Python-Threads, um den RFID-Reader und die Überwachung der Datenbankverbindung gleichzeitig auszuführen.
Installation
Um Noatime auf deinem System einzurichten, folge diesen Schritten:

Voraussetzungen
Python 3.x: Stelle sicher, dass Python 3.6 oder höher installiert ist.
MySQL-Datenbank: Richte eine MySQL-Datenbank zum Speichern der Zeitstempel ein und konfiguriere deine Verbindungsdetails.
Setup
Repository klonen:

bash
Copy code
git clone https://github.com/deinbenutzername/noatime.git
cd noatime
Virtuelle Umgebung einrichten:

bash
Copy code
python3 -m venv venv
source venv/bin/activate  # Auf Windows benutze `venv\Scripts\activate`
Abhängigkeiten installieren:

bash
Copy code
pip install -r requirements.txt
Umgebungsvariablen einrichten:

Erstelle eine .env-Datei im Stammverzeichnis des Projekts, um deine Datenbank-Verbindungsdetails sicher zu speichern. Beispiel:

makefile
Copy code
DB_USER=dein_datenbank_benutzer
DB_PASSWORD=dein_datenbank_passwort
DB_HOST=dein_datenbank_host
DB_NAME=dein_datenbank_name
Hinweis: Füge die .env-Datei zu .gitignore hinzu, um zu verhindern, dass sensible Informationen in das Repository gelangen.

Die Anwendung konfigurieren:

Stelle sicher, dass die Datenbankkonfiguration korrekt in der .env-Datei oder den Umgebungsvariablen des Systems gesetzt ist.
Aktualisiere die config/config.cnf-Datei mit dem entsprechenden Gerätenamen und anderen Einstellungen.
Anwendung starten:

bash
Copy code
python main.py
Anwendung mit Systemd ausführen
Du kannst die Anwendung auch als Dienst mit systemd ausführen. Hier sind die Schritte, um es einzurichten:

Erstelle eine neue systemd-Dienstdatei (z. B. /etc/systemd/system/noatime.service):

ini
Copy code
[Unit]
Description=Noatime RFID Zeiterfassung
After=network.target

[Service]
User=dein_benutzer
WorkingDirectory=/pfad/zum/noatime
ExecStart=/pfad/zu/deinem/venv/bin/python /pfad/zum/noatime/main.py
EnvironmentFile=/pfad/zum/noatime/.env
Restart=always

[Install]
WantedBy=multi-user.target
Lade die systemd-Konfiguration neu und starte den Dienst:

bash
Copy code
sudo systemctl daemon-reload
sudo systemctl start noatime
sudo systemctl enable noatime
Nutzung
Ein- und Ausstempeln:

Halte deinen NFC RFID-Tag vor den Reader. Das System registriert den Zeitstempel und speichert ihn in der Datenbank oder in der Backup-Datei.
Offline-Modus:

Wenn die Anwendung keine Verbindung zur Datenbank herstellen kann, speichert sie die Zeitstempel in einer Backup-Datei. Sobald die Verbindung wiederhergestellt ist, wird das Backup verarbeitet.
Reset des Readers:

Die Anwendung überprüft regelmäßig den Status des RFID-Readers. Wenn Probleme festgestellt werden, wird versucht, den Reader zurückzusetzen, um die Funktionalität wiederherzustellen.
Konfiguration
config/config.cnf: Konfigurationsdatei für die Geräte-spezifischen Parameter wie Gerätename.
Umgebungsvariablen: Speichert sensible Informationen wie die Datenbank-Zugangsdaten in einer .env-Datei.
Lizenz
Dieses Projekt ist unter der MIT-Lizenz lizenziert - siehe die LICENSE-Datei für Details.

Mitwirkende
Fühle dich frei, Issues zu melden, das Repository zu forken und Pull Requests beizutragen. Bitte stelle sicher, dass du den Kodierungsrichtlinien folgst und aussagekräftige Commit-Nachrichten bereitstellst.

