import sys
import threading
import logging
from gui import create_gui, update_server_status
from connection import connection_checker
from rfid import rfid_reader, monitor_rfid_thread  
from database import connect_to_database
import configparser

# Initialisiere den Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main_logger")

# Lade Gerätenamen aus der Konfigurationsdatei
config = configparser.ConfigParser()
config.read('config/config.cnf')
device_name = config['device']['name']

def on_close(root, conn_ref):
    """
    Wird aufgerufen, wenn das Fenster geschlossen wird. Beendet die Anwendung und schließt die Datenbankverbindung, falls sie noch offen ist.
    """
    logger.info("Anwendung wurde über den Fenster-Schließen-Button geschlossen.")

    try:
        conn = conn_ref.get('conn')
        # Prüfen, ob die Verbindung noch besteht, und schließen
        if conn and conn.is_connected():
            conn.close()
            logger.info("Datenbankverbindung wurde geschlossen.")
        else:
            logger.warning("Datenbankverbindung war bereits geschlossen oder nicht verfügbar.")
    except Exception as e:
        logger.error(f"Fehler beim Überprüfen oder Schließen der Verbindung: {e}")

    root.destroy()  # Schließt das GUI
    sys.exit()  # Beendet die Anwendung

# Haupteinstiegspunkt
if __name__ == '__main__':
    root = create_gui()  # Erstelle das GUI
    conn_ref = {'conn': None, 'is_connected': False}

    # Versuche, eine Verbindung zur Datenbank herzustellen
    conn_ref['conn'] = connect_to_database()
    if conn_ref['conn']:
        conn_ref['is_connected'] = True
        logger.info("[Main] Initiale Datenbankverbindung hergestellt.")
        update_server_status(True)  # Setze den Serverstatus auf "Online"
    else:
        conn_ref['is_connected'] = False
        logger.warning("[Main] Konnte keine initiale Datenbankverbindung herstellen. Offline-Modus aktiviert.")
        update_server_status(False)  # Setze den Serverstatus auf "Offline"

    # Starte die Threads für den Verbindungs-Checker und den RFID-Reader
    rfid_thread = threading.Thread(
        target=rfid_reader, 
        args=(conn_ref, root), 
        name="RFIDReaderThread", 
        daemon=True  # Daemon-Thread wird beendet, wenn das Hauptprogramm beendet wird
    )
    rfid_thread.start()

    # Starte den Watchdog-Thread, der den RFID-Reader überwacht
    watchdog_thread = threading.Thread(
        target=monitor_rfid_thread, 
        args=(rfid_reader, conn_ref, root), 
        name="WatchdogThread", 
        daemon=True
    )
    watchdog_thread.start()

    # Starte den Verbindungs-Checker-Thread
    threading.Thread(
        target=connection_checker, 
        args=(conn_ref, root, update_server_status), 
        name="ConnectionCheckerThread", 
        daemon=True  # Daemon-Thread wird beendet, wenn das Hauptprogramm beendet wird
    ).start()

    # Setze das Schließen-Verhalten der Anwendung, um die Verbindung korrekt zu beenden
    root.protocol("WM_DELETE_WINDOW", lambda: on_close(root, conn_ref))
    root.mainloop()  # Starte die Haupt-GUI-Schleife
