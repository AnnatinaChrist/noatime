"""
===============================================================================
Projekt: Noatime
Dateiname: rfid_reader.py
Version: 1.3.0
Entwickler: Annatina Christ
Datum: 06.12.2024

Dieses Skript liest die RFID Badges und löst die entsprechenden 
Datenbankfunktionen oder ein Backup aus.

Changelog:
- [29.11.2024]: Erste Version.
- [02.12.2024]: Verbesserte Stabilität, Watchdog-Mechanismus, und Fehlerbehandlung.
- [05.12.2024]: Verbesserte Thread-Überwachung und Hardware-Sicherheit.
- [06.12.2024]: PN532 Health Check, Backup Lock, Thread Termination, und Cleanup.

===============================================================================
"""

import time
import logging
import threading
import signal
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
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# Console Handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
rfid_logger.addHandler(console_handler)

# File Handler
file_handler = logging.FileHandler("/home/pi_noatime/python/noatime/logs/rfid.log")
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)
rfid_logger.addHandler(file_handler)

# Global flags and locks
stop_flag = threading.Event()  # For clean thread termination
backup_lock = threading.Lock()  # For safe backup file operations

# State variables for debounce
last_uid = None
last_uid_time = 0


def is_pn532_responsive(pn532):
    """
    Checks if the PN532 module is responsive by issuing a basic command.
    """
    try:
        version = pn532.get_firmware_version()
        if version:
            rfid_logger.info(f"[RFID Reader] PN532 firmware version: {version}")
            return True
        else:
            rfid_logger.warning("[RFID Reader] PN532 is unresponsive.")
            return False
    except Exception as e:
        rfid_logger.error(f"[RFID Reader] Error checking PN532 status: {e}")
        return False


def initialize_pn532(hardware_lock):
    """
    Attempts to initialize the PN532 module with retries.
    """
    while not stop_flag.is_set():
        try:
            with hardware_lock:
                pn532 = PN532_UART(debug=False, reset=20)
                pn532.SAM_configuration()
            rfid_logger.info("[RFID Reader] PN532 successfully initialized.")
            return pn532
        except Exception as e:
            rfid_logger.error(f"[RFID Reader] Initialization failed: {e}. Retrying in 5 seconds...")
            time.sleep(5)
    return None


def rfid_reader(conn_ref, root, hardware_lock):
    """
    Main RFID reader logic with thread safety and error handling.
    """
    global last_uid, last_uid_time

    pn532 = initialize_pn532(hardware_lock)
    if not pn532:
        return

    rfid_logger.info("Waiting for RFID/NFC card...")
    while not stop_flag.is_set():
        try:
            uid = None
            with hardware_lock:
                try:
                    uid = pn532.read_passive_target(timeout=0.5)
                except Exception as read_error:
                    rfid_logger.warning(f"[RFID Reader] Error reading RFID tag: {read_error}")
                    pn532 = initialize_pn532(hardware_lock)

            if uid:
                uid_str = sanitize_uid(uid)
                current_time = time.time()

                # Debounce
                if uid_str == last_uid and current_time - last_uid_time < 2:
                    continue

                last_uid = uid_str
                last_uid_time = current_time
                rfid_logger.info(f"[RFID Reader] Found tag with UID: {uid_str}")

                if not conn_ref['is_connected']:
                    # Offline Mode
                    rfid_logger.info("[RFID Reader] No database connection. Writing to backup.")
                    with backup_lock:
                        write_to_backup_file(
                            "INSERT INTO stamp (sta_key_id, sta_ort, sta_stempel_zeit, sta_crt_usr) VALUES (%s, %s, NOW(), %s)",
                            (uid_str, device_name, "test_pi"),
                        )
                    root.after(0, update_instruction_label, "Eingestempelt.")
                else:
                    try:
                        with conn_ref['conn'].cursor() as cursor:
                            rfid_logger.info(f"[Debug] Checking if tag {uid_str} exists in database.")
                            if check_rfid_exists(cursor, uid_str):
                                rfid_logger.info(f"[Debug] Tag {uid_str} exists. Processing entry...")
                                first_name, last_name = get_person_name_from_uid(cursor, uid_str)
                                clock_count = get_time_clock_count(cursor, uid_str)

                                greeting = (
                                    f"Grüezi {first_name} {last_name}." if clock_count % 2 == 0
                                    else f"Uf Wiederluaga {first_name} {last_name}. Bis bald!"
                                )
                                root.after(0, update_instruction_label, greeting)
                                create_stamp_entry(conn_ref['conn'], cursor, uid_str)
                                rfid_logger.info(f"[Debug] Successfully inserted entry for tag {uid_str}.")
                            else:
                                rfid_logger.info(f"[Debug] Tag {uid_str} not found. Registering new tag.")
                                register_rfid_tag(conn_ref['conn'], cursor, uid_str)
                                create_stamp_entry(conn_ref['conn'], cursor, uid_str)

                        root.after(2000, reset_instruction_label)
                    except Exception as db_error:
                        rfid_logger.error(f"[RFID Reader] Database error: {db_error}")
                        with backup_lock:
                            write_to_backup_file(
                                "INSERT INTO stamp (sta_key_id, sta_ort, sta_stempel_zeit, sta_crt_usr) VALUES (%s, %s, NOW(), %s)",
                                (uid_str, "device_name", "test_pi"),
                            )
                        root.after(0, update_instruction_label, "Eingestempelt.")
        except Exception as e:
            rfid_logger.error(f"[RFID Reader] Unexpected error: {e}. Reinitializing PN532...")
            pn532 = initialize_pn532(hardware_lock)



def monitor_rfid_thread(rfid_thread_func, conn_ref, root):
    """
    Monitors the RFID thread and restarts it if it stops unexpectedly.
    """
    hardware_lock = threading.Lock()

    def start_thread():
        thread = threading.Thread(
            target=rfid_thread_func,
            args=(conn_ref, root, hardware_lock),
            daemon=True
        )
        thread.start()
        return thread

    rfid_thread = start_thread()

    while not stop_flag.is_set():
        if rfid_thread.is_alive():
            rfid_logger.info("[Watchdog] RFID thread is still running.")
        else:
            rfid_logger.warning("[Watchdog] RFID thread has stopped. Restarting...")
            rfid_thread = start_thread()
        time.sleep(10)


def cleanup(signal_received, frame):
    """
    Handles cleanup on program termination.
    """
    rfid_logger.info("[RFID Reader] Cleaning up resources...")
    stop_flag.set()
    time.sleep(1)  # Allow threads to terminate gracefully
    exit(0)


# Signal handling for cleanup
signal.signal(signal.SIGINT, cleanup)
signal.signal(signal.SIGTERM, cleanup)
