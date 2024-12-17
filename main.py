"""
===============================================================================
Projekt: Noatime
Dateiname: main.py
Version: 1.0.0
Entwickler: Annatina Christ
Datum: 29.11.2024
Haupt Einstiegspunkt baut das GUI auf und startet Threads für den Reader und
für die Überwachung der Verbindung.

Changelog:
- [29.11.24]: Erste Version.
- [11.12.24]: Kommentare und Beschreibungen auf Deutsch

===============================================================================
"""

import sys
import threading
import logging
from gui import create_gui
from connection import connection_checker
from rfid import rfid_reader
from database import connect_to_database, process_backup_data
from pn532 import PN532_UART
import configparser

# Initialisiere Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main_logger")

# Konfigurationsdateien laden
config = configparser.ConfigParser()
config_path = 'config/config.cnf'
config.read(config_path)
device_name = config['device']['name']  # Lade den Gerätenamen aus der Konfigurationsdatei

# Initialisiere den PN532 RFID-Reader
pn532 = PN532_UART(debug=False, reset=20)
pn532.SAM_configuration()  # Konfiguriere den PN532 RFID-Reader
pn532_ref = {"pn532": pn532}
hardware_lock = threading.Lock()  # Lock für Hardwareoperationen

def on_close(root, conn_ref):
    """
    Verarbeitet das Schließen der Anwendung und bereinigt Ressourcen.
    
    Diese Funktion schließt die Datenbankverbindung, wenn eine aktive 
    Verbindung besteht, und beendet die Anwendung sauber.
    """
    logger.info("Anwendung wird heruntergefahren.")

    try:
        conn = conn_ref.get('conn')
        if conn and conn.is_connected():
            conn.close()
            logger.info("Datenbankverbindung geschlossen.")
        else:
            logger.warning("Keine aktive Datenbankverbindung zum Schließen.")
    except Exception as e:
        logger.error(f"Fehler beim Schließen der Datenbankverbindung: {e}")

    root.destroy()
    sys.exit()

# Hauptprogramm-Einstiegspunkt
if __name__ == '__main__':
    # Erstelle das GUI
    root = create_gui()
    
    # Initialisiere die Referenz für die Datenbankverbindung
    conn_ref = {'conn': None, 'is_connected': False}
    conn_lock = threading.Lock()  # Erstelle einen Lock für die gemeinsame Nutzung von Datenbank- und Hardware-Operationen

    # Versuche, eine Verbindung zur Datenbank herzustellen
    conn_ref['conn'] = connect_to_database()
    if conn_ref['conn']:
        conn_ref['is_connected'] = True
        logger.info("[Main] Datenbankverbindung erfolgreich hergestellt.")
        # Verarbeite Backup-Daten, falls vorhanden
        process_backup_data(conn_ref['conn'])

        
        
    else:
        conn_ref['is_connected'] = False
        logger.warning("[Main] Fehler bei der Datenbankverbindung. Anwendung läuft im Offline-Modus.")
        

    # Starte den RFID-Reader-Thread
    rfid_thread = threading.Thread(
        target=rfid_reader,
        args=(conn_ref, root, conn_lock, device_name, pn532_ref),  # Übergibt notwendige Argumente
        name="RFIDReaderThread",
        daemon=True  # Der Thread wird beendet, wenn das Hauptprogramm beendet wird
    )
    rfid_thread.start()
    
    # Starte den Verbindung-Checker-Thread
    threading.Thread(
        target=connection_checker,
        args=(conn_ref, root),
        name="ConnectionCheckerThread",
        daemon=True  # Der Thread wird beendet, wenn das Hauptprogramm beendet wird
    ).start()
   
    # Definiere das Verhalten beim Schließen der Anwendung
    root.protocol("WM_DELETE_WINDOW", lambda: on_close(root, conn_ref))
    
    # Starte die Haupt-GUI-Schleife
    root.mainloop()
