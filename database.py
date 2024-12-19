"""
===============================================================================
Projekt: Noatime
Dateiname: database.py
Version: 1.0.0
Entwickler: Annatina Christ
Datum: 29.11.2024

Hier werden alle Datenbankoperationen und die Verbindung zur Verfügung gestellt.

Changelog:
- [29.11.24]: Erste Version.
- [Datum]: Weitere Änderungen/Verbesserungen.

===============================================================================
"""

import logging
import json
import configparser
from mysql.connector import connect, Error
from logger_config import LoggerConfig
import os
import tempfile
from dotenv import load_dotenv

# Konfiguriere Logging
logger_config = LoggerConfig()
logger_config.configure()
sql_log = logger_config.get_logger("sql_logger")

# Lade Gerätenamen aus der Konfigurationsdatei
config = configparser.ConfigParser()
config_path = 'config/config.cnf'
config.read(config_path)
device_name = config['device']['name']
device_user = config['device']['username']


BACKUP_FILE = 'backup/backup.json'

# Load the .env file (automatically looks for a .env file in the root directory)
load_dotenv()  # This will load environment variables from the .env file into the environment
# Hilfsfunktionen
def sanitize_uid(uid):
    """
    Sanitisiert die UID, indem Rückwärtsschläge und einfache Anführungszeichen entfernt werden 
    und Bytes oder None-Werte behandelt werden.
    """
    if uid is None:
        raise ValueError("UID darf nicht None sein")
    if isinstance(uid, bytes):
        uid = uid.hex()  # Bytes in Hexadezimal-Format umwandeln
    return uid.replace("\\", "").replace("'", "")


def fetch_one(cursor, query, params):
    """
    Führt eine Abfrage aus und gibt ein einzelnes Ergebnis zurück.
    """
    cursor.execute(query, params)
    return cursor.fetchone()


def write_to_backup_file(sql, values):
    """
    Schreibt einen SQL-Befehl und seine Werte als JSON in die Backup-Datei.
    """
    
    if sql is None or values is None:
        print("Fehler: SQL-Befehl oder Werte sind None.")
        return
    
    try:
        with open(BACKUP_FILE, "a") as file:
            # Make sure the values are properly formatted
            json.dump({"sql": sql, "values": values}, file)
            file.write("\n")
        sql_log.info(f"Operation in Backup-Datei geschrieben: {sql} mit Werten {values}")
    except Exception as e:
        sql_log.error(f"Fehler beim Schreiben in die Backup-Datei: {e}")
        
def handle_backup(conn_ref, sql, values):
    """
    Handhabt die Backup-Logik, wenn keine Datenbankverbindung vorhanden ist.
    Schreibt den SQL-Befehl und die Werte in die Backup-Datei.
    """
    if conn_ref['conn'] is None or not conn_ref['conn'].is_connected():
        # Keine Datenbankverbindung: Schreibe den Befehl und die Werte in die Backup-Datei
        print("[Backup] Keine Datenbankverbindung. Schreibe ins Backup.")
        write_to_backup_file(sql, values)
        return True  # Gibt an, dass das Backup geschrieben wurde
    return False  # Kein Backup notwendig, wenn eine Verbindung vorhanden ist

def process_backup_data(conn):
    """
    Liest und verarbeitet Backup-Daten aus der Backup-Datei.
    Löscht jede Eintragung nach der Verarbeitung, um Duplikate zu vermeiden.
    """
    
    if not os.path.exists(BACKUP_FILE):
        sql_log.warning("[Backup] Keine Backup-Datei gefunden.")
        return

    try:
        sql_log.info("[Backup] Verarbeite Backup-Daten...")
        
        # Verwende eine temporäre Datei für sichere Updates
        with open(BACKUP_FILE, "r") as f, tempfile.NamedTemporaryFile("w", delete=False) as temp_file:
            temp_file_path = temp_file.name
            for line_num, line in enumerate(f, start=1):
                try:
                    entry = json.loads(line.strip())
                    sql = entry["sql"]
                    values = entry["values"]

                    cursor = conn.cursor()
                    cursor.execute(sql, values)
                    conn.commit()
                    sql_log.info(f"[Backup] Zeile {line_num}: Ausgeführt: {sql} mit Werten {values}")
                except json.JSONDecodeError:
                    sql_log.error(f"[Backup] Ungültiges JSON in Zeile {line_num}: {line.strip()}")
                    temp_file.write(line)  # Behalte fehlerhafte Zeilen für erneuten Versuch
                except Exception as e:
                    sql_log.error(f"[Backup] Fehler in Zeile {line_num}: {e}")
                    temp_file.write(line)  # Behalte fehlerhafte Zeilen für erneuten Versuch

        # Ersetze die alte Datei durch die temporäre Datei
        os.replace(temp_file_path, BACKUP_FILE)
        sql_log.info("[Backup] Backup-Verarbeitung abgeschlossen.")

    except Exception as e:
        sql_log.error(f"[Backup] Unerwarteter Fehler: {e}")


# Datenbankinteraktionsfunktionen
def check_rfid_exists(cursor, uid):
    """
    Überprüft, ob die RFID UID bereits in der Datenbank existiert.
    """
    sanitized_uid = sanitize_uid(uid)
    query = "SELECT peke_id FROM person_key WHERE peke_key_id = %s"
    return fetch_one(cursor, query, (sanitized_uid,))


def create_stamp_entry(conn, cursor, peke_key_id):
   
    """
    Erstellt einen Stempel-Eintrag für die gegebene `peke_key_id`.
    """
    sanitized_peke_key_id = sanitize_uid(peke_key_id)
    sql = "INSERT INTO stamp (sta_key_id, sta_ort, sta_stempel_zeit, sta_crt_usr) VALUES (%s, %s, NOW(), %s)"
    values = (sanitized_peke_key_id, device_name, device_user)

    if conn:
        try:
            cursor.execute(sql, values)
            conn.commit()
            sql_log.info(f"Stempel-Eintrag für Schlüssel-ID {sanitized_peke_key_id} erstellt.")
        except Exception as e:
            sql_log.error(f"Fehler beim Ausführen des SQL: {e}")
    else:
        write_to_backup_file(sql, values)


def register_rfid_tag(conn, cursor, uid):
    
    """
    Registriert ein RFID-Tag in der Datenbank, wenn es noch nicht existiert.
    """
    try:
        sanitized_uid = sanitize_uid(uid)

        if not check_rfid_exists(cursor, sanitized_uid):
            sql = "INSERT INTO person_key (peke_key_id, peke_typ, peke_crt_user) VALUES (%s, %s, %s)"
            values = (sanitized_uid, "rfid", device_user)

            if conn:
                cursor.execute(sql, values)
                conn.commit()
                sql_log.info(f"RFID-Tag {sanitized_uid} erfolgreich registriert.")
            else:
                print(f"Keine aktive Verbindung, um RFID-Tag {sanitized_uid} zu registrieren. Operation übersprungen.")
        else:
            sql_log.warning(f"RFID-Tag {sanitized_uid} existiert bereits.")
            peke_key_id = get_peke_key_id(cursor, sanitized_uid)
            create_stamp_entry(conn, cursor, peke_key_id)
    except Exception as e:
        sql_log.error(f"Fehler bei der Registrierung des RFID-Tags: {e}")


def get_peke_key_id(cursor, uid):
    """
    Holt die `peke_key_id` für die gegebene RFID UID aus `person_key`.
    """
    sanitized_uid = sanitize_uid(uid)
    query = "SELECT peke_key_id FROM person_key WHERE peke_key_id = %s"
    result = fetch_one(cursor, query, (sanitized_uid,))
    return result[0] if result else None


def get_person_name_from_uid(cursor, uid):
    """
    Holt den Vor- und Nachnamen der Person für die gegebene RFID UID.
    """
    sanitized_uid = sanitize_uid(uid)
    query = """
        SELECT p.pers_vorname, p.pers_nachname
        FROM person_key pk
        JOIN person p ON pk.peke_pers_id = p.pers_id
        WHERE pk.peke_key_id = %s
    """
    result = fetch_one(cursor, query, (sanitized_uid,))
    return result if result else (None, None)


def get_time_clock_count(cursor, peke_key_id):
    """
    Holt die Anzahl der Male, die eine Person heute gestempelt hat.
    """
    query = """
        SELECT COUNT(*) 
        FROM stamp
        WHERE sta_key_id = %s 
          AND DATE(sta_stempel_zeit) = CURDATE();
    """
    result = fetch_one(cursor, query, (peke_key_id,))
    return result[0] if result else 0

def connect_to_database():
    """
    Connect to the database using environment variables for credentials.
    """
    try:
        # Fetch the database connection info from environment variables
        db_user = os.getenv("DB_USER")
        db_password = os.getenv("DB_PASSWORD")
        db_host = os.getenv("DB_HOST")
        db_name = os.getenv("DB_NAME")

        # Check that all necessary environment variables are set
        if not all([db_user, db_password, db_host, db_name]):
            raise ValueError("Missing one or more required database configuration values in environment variables.")

        # Attempt to establish a database connection
        conn = connect(
            user=db_user,
            password=db_password,
            host=db_host,
            database=db_name,            
            connection_timeout=10  # Set a timeout to avoid hanging
        )
        logging.info("Database connection established.")
        return conn
    except Error as e:
        logging.error(f"Error establishing database connection: {e}")
        return None
    except ValueError as e:
        logging.error(f"Configuration error: {e}")
        return None

