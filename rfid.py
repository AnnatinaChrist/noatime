"""
===============================================================================
Projekt: Noatime
Dateiname: rfid_reader.py
Version: 1.2.0
Entwickler: Annatina Christ
Datum: 05.12.2024

Dieses Skript liest die RFID Badges und löst die entsprechenden 
Datenbankfunktionen oder ein Backup aus.

Changelog:
- [29.11.2024]: Erste Version.
- [02.12.2024]: Verbesserte Stabilität, Watchdog-Mechanismus, und Fehlerbehandlung.
- [05.12.2024]: Verbesserte Thread-Überwachung und Hardware-Sicherheit.

===============================================================================
"""

import time
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

# Initialize logger
rfid_logger = logging.getLogger("rfid_logger")
rfid_logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
rfid_logger.addHandler(console_handler)

# State variables for debounce
last_uid = None
last_uid_time = 0


def rfid_reader(conn_ref, root, hardware_lock):
    """
    Main RFID reader logic with thread safety and error handling.
    """
    global last_uid, last_uid_time

    def initialize_pn532():
        """
        Attempts to initialize the PN532 module with retries.
        """
        while True:
            try:
                with hardware_lock:
                    pn532 = PN532_UART(debug=False, reset=20)
                    pn532.SAM_configuration()
                rfid_logger.info("[RFID Reader] PN532 successfully initialized.")
                return pn532
            except Exception as e:
                rfid_logger.error(f"[RFID Reader] Initialization failed: {e}. Retrying in 5 seconds...")
                time.sleep(5)

    # Initialize PN532
    pn532 = initialize_pn532()
    rfid_logger.info("Waiting for RFID/NFC card...")

    while True:
        try:
            uid = None
            with hardware_lock:
                try:
                    uid = pn532.read_passive_target(timeout=0.5)
                except Exception as read_error:
                    rfid_logger.warning(f"[RFID Reader] Error while reading RFID tag: {read_error}")
                    rfid_logger.warning("[RFID Reader] Reinitializing PN532 due to persistent errors...")
                    pn532 = initialize_pn532()

            if uid:
                uid_str = sanitize_uid(uid)
                current_time = time.time()

                # Debounce: Process the same UID only if it hasn't been processed recently
                if uid_str == last_uid and current_time - last_uid_time < 2:
                    continue

                last_uid = uid_str
                last_uid_time = current_time
                rfid_logger.info(f"[RFID Reader] Found tag with UID: {uid_str}")

                with conn_lock:
                    if conn_ref['conn'] is None or not conn_ref['is_connected']:
                        rfid_logger.info("[RFID Reader] No database connection. Writing to backup.")
                        write_to_backup_file(
                            "INSERT INTO stamp (sta_key_id, sta_ort, sta_stempel_zeit, sta_crt_usr) VALUES (%s, %s, NOW(), %s)",
                            (uid_str, "device_name", "test_pi"),
                        )
                        root.after(0, update_instruction_label, "Eingestempelt.")
                    else:
                        try:
                            with conn_ref['conn'].cursor() as cursor:
                                if check_rfid_exists(cursor, uid_str):
                                    first_name, last_name = get_person_name_from_uid(cursor, uid_str)
                                    clock_count = get_time_clock_count(cursor, uid_str)

                                    greeting = (
                                        f"Grüezi {first_name} {last_name}." if clock_count % 2 == 0
                                        else f"Uf Wiederluaga {first_name} {last_name}. Bis bald!"
                                    )
                                    root.after(0, update_instruction_label, greeting)
                                    create_stamp_entry(conn_ref['conn'], cursor, uid_str)
                                else:
                                    rfid_logger.info("[RFID Reader] Tag not found in database. Registering tag.")
                                    register_rfid_tag(conn_ref['conn'], cursor, uid_str)
                                    create_stamp_entry(conn_ref['conn'], cursor, uid_str)

                            root.after(2000, reset_instruction_label)
                        except Exception as db_error:
                            rfid_logger.error(f"[RFID Reader] Database error: {db_error}")
                            write_to_backup_file(
                                "INSERT INTO stamp (sta_key_id, sta_ort, sta_stempel_zeit, sta_crt_usr) VALUES (%s, %s, NOW(), %s)",
                                (uid_str, "device_name", "test_pi"),
                            )
                            root.after(0, update_instruction_label, "Eingestempelt.")

            time.sleep(0.1)  # Short delay to reduce CPU usage

        except Exception as e:
            rfid_logger.error(f"[RFID Reader] Error during processing: {e}. Attempting reinitialization...")
            try:
                pn532 = initialize_pn532()
            except Exception as reinit_error:
                rfid_logger.error(f"[RFID Reader] Reinitialization failed: {reinit_error}")
                time.sleep(5)  # Wait before retrying initialization


def monitor_rfid_thread(rfid_thread_func, conn_ref, root):
    """
    Monitors the RFID thread and restarts it if it stops unexpectedly.
    Logs the status of the RFID thread for debugging purposes.
    """
    hardware_lock = threading.Lock()  # Lock for hardware access

    def start_thread():
        thread = threading.Thread(
            target=rfid_thread_func,
            args=(conn_ref, root, hardware_lock),
            daemon=True
        )
        thread.start()
        return thread

    rfid_thread = start_thread()

    while True:
        # Check if the RFID thread is alive and log its status
        if rfid_thread.is_alive():
            rfid_logger.info("[Watchdog] RFID thread is still running.")
        else:
            rfid_logger.warning("[Watchdog] RFID thread has stopped. Restarting...")

        if not rfid_thread.is_alive():
            rfid_thread = start_thread()

        time.sleep(10)  # Check thread status every 10 seconds


