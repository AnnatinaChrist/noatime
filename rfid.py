"""
===============================================================================
Projekt: Noatime
Dateiname: rfid_reader.py
Version: 1.1.0
Entwickler: Annatina Christ
Datum: 29.11.2024

Dieses Skript liest die RFID Badges und löst die entsprechenden 
Datenbankfunktionen oder ein Backup aus.

Changelog:
- [29.11.2024]: Erste Version.
- [02.12.2024]: Verbesserte Stabilität, Watchdog-Mechanismus, und Fehlerbehandlung.

===============================================================================
"""

import time
import datetime
import logging
import threading
from pn532 import PN532_UART
from database import (
    check_rfid_exists,
    create_stamp_entry,
    register_rfid_tag,
    sanitize_uid,
    write_to_backup_file,
    get_person_name_from_uid,
    get_time_clock_count
)
from connection import conn_lock
from gui import update_instruction_label, reset_instruction_label
import configparser


# Lade den Gerätenamen aus der Konfigurationsdatei
config = configparser.ConfigParser()
config.read('config/config.cnf')
device_name = config['device']['name']

# Initialisiere Logger für RFID-Prozesse
rfid_logger = logging.getLogger("rfid_logger")
rfid_logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
rfid_logger.addHandler(console_handler)

# Zustandsvariablen für das Entprellen (Debounce) der RFID-Tags
last_uid = None
last_uid_time = 0

# Load device name from configuration
config = configparser.ConfigParser()
config.read('config/config.cnf')
device_name = config['device']['name']

# Initialize logger for RFID processes
rfid_logger = logging.getLogger("rfid_logger")
rfid_logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
rfid_logger.addHandler(console_handler)

# State variables for RFID tag debounce
last_uid = None
last_uid_time = 0

def safe_read_passive_target(pn532, timeout=0.5, retries=3):
    """
    Sicheres Lesen eines RFID-Tags mit Wiederholungsversuchen bei Fehlern.
    """
    for attempt in range(retries):
        try:
            uid = pn532.read_passive_target(timeout=timeout)
            if uid:
                return uid
        except Exception as e:
            rfid_logger.error(f"[RFID Reader] Leseversuch {attempt + 1} fehlgeschlagen: {e}")
            time.sleep(1)  # Delay before retry
    return None





def rfid_reader(conn_ref, root):
    """
    Liest RFID/NFC-Tags und führt je nach Vorhandensein in der Datenbank
    bestimmte Aktionen aus. Entprellung sorgt dafür, dass ein Tag nicht mehrfach
    innerhalb kurzer Zeit verarbeitet wird.
    """
    global last_uid, last_uid_time

    # Initialisiere PN532 mit Fehlerbehandlung
    while True:
        try:
            pn532 = PN532_UART(debug=False, reset=20)
            pn532.SAM_configuration()
            rfid_logger.info("[RFID Reader] PN532 erfolgreich initialisiert.")
            break
        except Exception as e:
            rfid_logger.error(f"[RFID Reader] Fehler bei der Initialisierung: {e}")
            time.sleep(5)  # Wartezeit vor erneutem Initialisierungsversuch

    while True:
        try:
            # Lese das nächste RFID-Tag
            uid = safe_read_passive_target(pn532)
            if uid:
                uid_str = sanitize_uid(uid)  # UID sanitieren
                current_time = time.time()  # Aktuelle Zeit für Entprellung

                # Entprellung: Verarbeite die UID nur, wenn sie nicht kürzlich verarbeitet wurde
                if uid_str == last_uid and current_time - last_uid_time < 2:
                    continue

                last_uid = uid_str
                last_uid_time = current_time
                rfid_logger.info(f"[RFID Reader] Tag mit UID gefunden: {uid_str}")

                with conn_lock:
                    # Überprüfe, ob eine Verbindung zur Datenbank besteht
                    if conn_ref['conn'] is None or not conn_ref['is_connected']:
                        rfid_logger.info("[RFID Reader] Keine Datenbankverbindung. Schreibe in Backup.")
                        current_timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        write_to_backup_file(
                            "INSERT INTO stamp (sta_key_id, sta_ort, sta_stempel_zeit, sta_crt_usr) VALUES (%s, %s, %s, %s)",
                            (uid_str, device_name, current_timestamp, "test_pi")
                        )
                        root.after(0, update_instruction_label, "Eingestempelt.")  # Update GUI
                    else:
                        try:
                            cursor = conn_ref['conn'].cursor()

                            # Überprüfe, ob das RFID-Tag bereits in der Datenbank vorhanden ist
                            if check_rfid_exists(cursor, uid_str):
                                first_name, last_name = get_person_name_from_uid(cursor, uid_str)
                                clock_count = get_time_clock_count(cursor, uid_str)

                                # Begrüßung basierend auf der Anzahl der Stempelzeiten
                                greeting = (
                                    f"Grüezi {first_name} {last_name}." if clock_count % 2 == 0
                                    else f"Uf Wiederluaga {first_name} {last_name}. Bis bald!"
                                )
                                root.after(0, update_instruction_label, greeting)  # Update GUI mit Begrüßung
                                create_stamp_entry(conn_ref['conn'], cursor, uid_str)  # Stempel-Eintrag erstellen
                            else:
                                rfid_logger.info("[RFID Reader] Tag nicht in der Datenbank gefunden. Tag wird registriert.")
                                register_rfid_tag(conn_ref['conn'], cursor, uid_str)  # Tag registrieren
                                create_stamp_entry(conn_ref['conn'], cursor, uid_str)  # Stempel-Eintrag erstellen

                            root.after(2000, reset_instruction_label)  # Setzt das Anleitungs-Label nach 2 Sekunden zurück

                        except Exception as e:
                            rfid_logger.error(f"[RFID Reader] Fehler: {e}")
                            write_to_backup_file(
                                "INSERT INTO stamp (sta_key_id, sta_ort, sta_stempel_zeit, sta_crt_usr) VALUES (%s, %s, NOW(), %s)",
                                (uid_str, device_name, "test_pi"),
                            )
                            root.after(0, update_instruction_label, "Eingestempelt.")  # Update GUI bei Fehler

            time.sleep(3)  # Wartezeit vor der nächsten RFID-Lesung
        except Exception as e:
            rfid_logger.error(f"[RFID Reader] Fehler während der Verarbeitung: {e}")
            try:
                # Neuinitialisierung bei Fehler
                pn532 = PN532_UART(debug=False, reset=20)
                pn532.SAM_configuration()
                rfid_logger.info("[RFID Reader] PN532 wurde erfolgreich neu initialisiert.")
            except Exception as reinit_error:
                rfid_logger.error(f"[RFID Reader] Fehler bei der Neuinitialisierung: {reinit_error}")
                time.sleep(5)  # Wartezeit vor erneutem Initialisierungsversuch


def monitor_rfid_thread(rfid_thread_func, conn_ref, root):
    """
    Überwacht den RFID-Thread und startet ihn neu, falls er abstürzt.
    """
    while True:
        if not rfid_thread.is_alive():
            rfid_logger.warning("[Watchdog] RFID-Thread ist abgestürzt. Neustart wird versucht.")
            rfid_thread = threading.Thread(target=rfid_thread_func, args=(conn_ref, root), daemon=True)
            rfid_thread.start()
        time.sleep(10)




