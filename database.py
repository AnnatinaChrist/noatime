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
from config_loader import load_config
from log import LoggerConfig


# Konfiguriere Logging
logger_config = LoggerConfig()
logger_config.configure()

# Lade Gerätenamen aus der Konfigurationsdatei
config = configparser.ConfigParser()
config_path = 'config/config.cnf'
config.read(config_path)
device_name = config['device']['name']


BACKUP_FILE = 'backup/backup.json'

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
        print(f"Operation in Backup-Datei geschrieben: {sql} mit Werten {values}")
    except Exception as e:
        print(f"Fehler beim Schreiben in die Backup-Datei: {e}")
        
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
    sql_log = logging.getLogger("sql_logger")
    try:
        sql_log.info("[Backup] Verarbeite Backup-Daten...")
        with open(BACKUP_FILE, "r") as f:
            lines = f.readlines()

        with open(BACKUP_FILE, "w") as f:
            for line in lines:
                try:
                    entry = json.loads(line.strip())
                    sql = entry["sql"]
                    values = entry["values"]

                    cursor = conn.cursor()
                    cursor.execute(sql, values)
                    conn.commit()
                    sql_log.info(f"[Backup] Ausgeführt: {sql} mit Werten {values}")
                except Exception as e:
                    sql_log.error(f"[Backup] Fehler bei der Verarbeitung des Eintrags: {e}")
                    f.write(line)  # Fehlerhafte Einträge zum erneuten Versuch wiederholen

        sql_log.info("[Backup] Backup-Verarbeitung abgeschlossen.")
    except FileNotFoundError:
        sql_log.warning("[Backup] Keine Backup-Datei gefunden.")
    except Exception as e:
        sql_log.error(f"[Backup] Fehler: {e}")

# Datenbankinteraktionsfunktionen
def check_rfid_exists(cursor, uid):
    """
    Überprüft, ob die RFID UID bereits in der Datenbank existiert.
    """
    sanitized_uid = sanitize_uid(uid)
    query = "SELECT peke_id FROM person_key WHERE peke_key_id = %s"
    return fetch_one(cursor, query, (sanitized_uid,))


def create_stamp_entry(conn, cursor, peke_key_id):
    sql_log = logging.getLogger("sql_logger")
    """
    Erstellt einen Stempel-Eintrag für die gegebene `peke_key_id`.
    """
    sanitized_peke_key_id = sanitize_uid(peke_key_id)
    sql = "INSERT INTO stamp (sta_key_id, sta_ort, sta_stempel_zeit, sta_crt_usr) VALUES (%s, %s, NOW(), %s)"
    values = (sanitized_peke_key_id, device_name, "test_pi")

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
    sql_log = logging.getLogger("sql_logger")
    """
    Registriert ein RFID-Tag in der Datenbank, wenn es noch nicht existiert.
    """
    try:
        sanitized_uid = sanitize_uid(uid)

        if not check_rfid_exists(cursor, sanitized_uid):
            sql = "INSERT INTO person_key (peke_key_id, peke_typ, peke_crt_user) VALUES (%s, %s, %s)"
            values = (sanitized_uid, "rfid", "test_pi")

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
    Stellt eine Verbindung zur Datenbank mithilfe der Konfigurationsdatei her.
    """
    try:
        config = load_config("config.cnf")  # Lade die Konfigurationsdatei
        db_config = config.get("client", {})
        if not db_config:
            raise ValueError("Die Client-Konfiguration ist entweder leer oder fehlt.")

        # Versuche, eine Verbindung herzustellen
        conn = connect(
            user=db_config.get("user"),
            password=db_config.get("password"),
            host=db_config.get("host"),
            database=db_config.get("database"),
            connection_timeout=10  # Setze ein Timeout, um ein Hängen zu vermeiden
        )
        logging.info("Datenbankverbindung hergestellt.")
        return conn
    except Error as e:
        logging.error(f"Verbindung zur Datenbank konnte nicht hergestellt werden: {e}")
        return None
