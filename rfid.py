import time
import logging
from pn532 import PN532_UART
from database import (
    check_rfid_exists,
    create_stamp_entry,
    sanitize_uid,
    write_to_backup_file,
    get_person_name_from_uid,
    get_time_clock_count,
    register_rfid_tag,
)
from gui import update_instruction_label, reset_instruction_label
from datetime import datetime
from log import LoggerConfig

# Initialize and configure the loggers
logger_config = LoggerConfig()
logger_config.configure()

# Fetch the RFID logger
rfid_logger = logger_config.get_logger("rfid_logger")

# Use the logger in your RFID module
rfid_logger.info("RFID logger initialized successfully.")
rfid_logger.error("This is a sample error log.")

# Debounce variables
last_uid = None
last_uid_time = 0

# Capture the exact time the badge was read
badge_read_time = datetime.now()

# Format the timestamp for SQL (if needed)
formatted_time = badge_read_time.strftime('%Y-%m-%d %H:%M:%S')

def rfid_reader(conn_ref, root, conn_lock, device_name, pn532_ref):
    """
    Reads RFID tags and processes them with the database logic, including error handling
    and PN532 reset attempts when necessary.
    """
    global last_uid, last_uid_time

    pn532 = pn532_ref["pn532"]  # Use the passed PN532 reference
    rfid_logger.info("PN532 initialized. Waiting for RFID/NFC cards...")

    retry_count = 3  # Number of retries before resetting the PN532
    max_read_failures = 5  # Max consecutive read failures before reset
    read_failures = 0  # Track consecutive failures
    last_health_check_time = time.time()  # Track the last health check timestamp

    while True:
        try:
            # Perform health check every ~20 seconds
            current_time = time.time()
            if current_time - last_health_check_time >= 20:
                try:
                    # Simple health check: Check if we can get firmware version
                    firmware_version = pn532.get_firmware_version()
                    rfid_logger.info(f"RFID Reader is responsive. Firmware version: {firmware_version}")
                except Exception as e:
                    rfid_logger.error(f"RFID Reader health check failed: {e}")
                    # If health check fails, try to reset the reader
                    rfid_logger.error("Attempting to reset the PN532...")
                    try:
                        pn532.SAM_configuration()  # Reconfigure the PN532
                        time.sleep(5)  # Give it time to reset
                        pn532._wakeup()  # Wake it up again
                        time.sleep(2)  # Allow additional time for the reset
                    except Exception as reset_error:
                        rfid_logger.error(f"Failed to reset PN532: {reset_error}")
                last_health_check_time = current_time  # Update the last health check time

            # Try reading an RFID tag
            uid = None
            for attempt in range(retry_count):
                try:
                    # Read RFID tag with a timeout
                    uid = pn532.read_passive_target(timeout=0.5)
                    if uid:
                        read_failures = 0  # Reset failure count if successful
                        break
                except Exception as e:
                    rfid_logger.error(f"Attempt {attempt + 1} to read RFID failed: {e}")
                    if attempt == retry_count - 1:
                        # Last attempt, reset PN532 if all attempts fail
                        rfid_logger.error("Max retries reached, resetting PN532...")
                        try:
                            pn532.SAM_configuration()  # Make sure PN532 is configured correctly
                            time.sleep(5)  # Give it more time to reset
                            pn532._wakeup()  # Try waking it up again after reset
                            time.sleep(2)  # Allow additional time for the reset
                        except Exception as reset_error:
                            rfid_logger.error(f"Failed to reset PN532: {reset_error}")
                        read_failures += 1
                        if read_failures >= max_read_failures:
                            rfid_logger.critical("Too many consecutive failures. Manual intervention required.")
                            return  # Exit if too many read failures

            if uid:
                # Sanitize and process the UID
                uid_str = sanitize_uid(uid)
                current_time = time.time()

                # Debounce check: Ignore reads that are too close to the previous one
                if uid_str == last_uid and current_time - last_uid_time < 2:
                    continue

                last_uid = uid_str
                last_uid_time = current_time
                rfid_logger.info(f"Found tag with UID: {uid_str}")

                # Process the UID and interact with the database
                with conn_lock:
                    if conn_ref['conn'] is None or not conn_ref['is_connected']:
                        # No database connection, write to backup file
                        rfid_logger.info("No database connection. Writing to backup.")
                        write_to_backup_file(
                            "INSERT INTO stamp (sta_key_id, sta_ort, sta_stempel_zeit, sta_crt_usr) VALUES (%s, %s, %s, %s)",
                            (uid_str, device_name,formatted_time, "test_pi"),
                        )
                        root.after(0, update_instruction_label, "Eingestempelt.")
                        
                    else:
                        try:
                            cursor = conn_ref['conn'].cursor()

                            # Check if the RFID tag exists in the database
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
                                rfid_logger.info("Tag not found in database. Registering tag.")
                                register_rfid_tag(conn_ref['conn'], cursor, uid_str)
                                create_stamp_entry(conn_ref['conn'], cursor, uid_str)

                            root.after(2000, reset_instruction_label)
                        except Exception as e:
                            rfid_logger.error(f"Error while processing RFID tag: {e}")
                            write_to_backup_file(
                                "INSERT INTO stamp (sta_key_id, sta_ort, sta_stempel_zeit, sta_crt_usr) VALUES (%s, %s, %s, %s)",
                                (uid_str, device_name, formatted_time, "test_pi"),
                            )
                            root.after(0, update_instruction_label, "Eingestempelt.")
                            
                            
            else:
                time.sleep(0.1)
        except Exception as e:
            rfid_logger.error(f"Error in RFID reader: {e}")
            time.sleep(1)


