import sys
import threading
import logging
from gui import create_gui, update_server_status
from connection import connection_checker
from rfid import rfid_reader
from database import connect_to_database
from pn532 import PN532_UART
import configparser

# Initialize Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main_logger")

# Load Configurations
config = configparser.ConfigParser()
config_path = 'config/config.cnf'
config.read(config_path)
device_name = config['device']['name']  # Load device name

# Initialize the PN532
pn532 = PN532_UART(debug=False, reset=20)
pn532.SAM_configuration()
pn532_ref = {"pn532": pn532}
hardware_lock = threading.Lock()

def on_close(root, conn_ref):
    """
    Handles application closure by cleaning up resources.
    """
    logger.info("Application is shutting down.")

    try:
        conn = conn_ref.get('conn')
        if conn and conn.is_connected():
            conn.close()
            logger.info("Database connection closed.")
        else:
            logger.warning("No active database connection to close.")
    except Exception as e:
        logger.error(f"Error while closing the database connection: {e}")

    root.destroy()
    sys.exit()

# Main Entry Point
if __name__ == '__main__':
    root = create_gui()  # Create the GUI
    conn_ref = {'conn': None, 'is_connected': False}
    conn_lock = threading.Lock()  # Create a shared lock for database and hardware

    # Connect to the database
    conn_ref['conn'] = connect_to_database()
    if conn_ref['conn']:
        conn_ref['is_connected'] = True
        logger.info("[Main] Database connection established.")
        update_server_status(True)  # Update GUI server status
    else:
        conn_ref['is_connected'] = False
        logger.warning("[Main] Database connection failed. Running in offline mode.")
        update_server_status(False)  # Update GUI server status

    # Start RFID reader thread
    rfid_thread = threading.Thread(
        target=rfid_reader,
        args=(conn_ref, root, conn_lock, device_name, pn532_ref),  # Pass the necessary arguments
        name="RFIDReaderThread",
        daemon=True
    )
    rfid_thread.start()
    
    # Start connection checker thread
    threading.Thread(
        target=connection_checker,
        args=(conn_ref, root, update_server_status),
        name="ConnectionCheckerThread",
        daemon=True
    ).start()
   
    # Set close behavior for the application
    root.protocol("WM_DELETE_WINDOW", lambda: on_close(root, conn_ref))
    root.mainloop()
