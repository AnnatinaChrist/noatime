"""
===============================================================================
Projekt: Noatime
Dateiname: connection.py
Version: 1.0.0
Entwickler: Annatina Christ
Datum: 29.11.2024

Überprüft die Verbindungen  (Internet und Server/DB) und schreibt den alive check
in die Datenbank.

Changelog:
- [29.11.24]: Erste Version.
- [Datum]: Weitere Änderungen/Verbesserungen.

===============================================================================
"""


import logging
import time
import subprocess
from database import connect_to_database, process_backup_data

import os
import re
import threading
import configparser
from datetime import datetime

# Thread-Sicherheits-Lock
conn_lock = threading.Lock()

# Lade Gerätenamen aus der Konfigurationsdatei
config = configparser.ConfigParser()
config_path = 'config/config.cnf'
config.read(config_path)
device_name = config['device']['name']

# Initialisiere Logger
connection_logger = logging.getLogger("connection_logger")
connection_logger.setLevel(logging.INFO)
connection_file_handler = logging.FileHandler("logs/connection.log")
connection_logger.addHandler(connection_file_handler)


def get_default_gateway():
    """
    Ruft das Standard-Gateway des Systems ab.
    """
    try:
        
        result = subprocess.check_output("ip route show default", shell=True).decode()
        match = re.search(r'default via (\S+)', result)
        if match:
            return match.group(1)
        else:
            connection_logger.warning("[get_default_gateway] Standard-Gateway nicht gefunden.")
            return None
    except Exception as e:
        connection_logger.error(f"[get_default_gateway] Fehler beim Abrufen des Gateways: {e}")
        return None

def can_ping():
    """
    Überprüft, ob das Standard-Gateway erreichbar ist (Ping-Test).
    """
    gateway = get_default_gateway()
    if not gateway:
        connection_logger.warning("[can_ping] Standard-Gateway nicht gefunden. Offline-Modus aktiviert.")
        return False
    try:
        subprocess.run(["ping", "-c", "1", gateway], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except subprocess.CalledProcessError:
        connection_logger.warning(f"[can_ping] Gateway nicht erreichbar: {gateway}")
        return False

def is_connection_alive(conn):
    """
    Überprüft, ob die Datenbankverbindung aktiv ist.
    """
    try:
        conn.ping(reconnect=True)
        return True
    except Exception as e:
        connection_logger.error(f"[is_connection_alive] Fehler bei der Überprüfung der Verbindung: {e}")
        return False

def connection_checker(conn_ref, root):
    """
    Überprüft regelmäßig die Netzwerkverbindung und die Datenbankverbindung.
    Wenn die Verbindung verloren geht, wird sie wiederhergestellt und die Sicherung verarbeitet.
    """
    was_offline = False
    while True:
        try:
            # Überprüft die Netzwerkverbindung
            if not can_ping():
                if not was_offline:
                    connection_logger.warning("[Connection Checker] Ping fehlgeschlagen. Offline-Modus aktiviert.")
                    conn_ref['is_connected'] = False
                was_offline = True
                
                time.sleep(10)
                continue

            if was_offline:
                connection_logger.info("[Connection Checker] Ping erfolgreich. Verarbeite Sicherung.")
                process_backup_data(conn_ref.get('conn'))  # Daten verarbeiten, wenn wieder online
                was_offline = False
                

            with conn_lock:
                conn = conn_ref.get('conn')
                if conn is None or not is_connection_alive(conn):
                    connection_logger.warning("[Connection Checker] Datenbankverbindung verloren.")
                    conn_ref['conn'] = connect_to_database()

                    if conn_ref['conn']:
                        conn_ref['is_connected'] = True
                        connection_logger.info("[Connection Checker] Verbindung wiederhergestellt.")
                        insert_initial_log(conn_ref['conn'])  # Sicherstellen, dass der initiale Log-Eintrag existiert
                        
                    else:
                        conn_ref['is_connected'] = False
                        connection_logger.warning("[Connection Checker] Verbindung konnte nicht wiederhergestellt werden.")
                        
                else:
                    conn_ref['is_connected'] = True
                    # Aufruf von log_alive für die Lebenszeichen-Überprüfung
                    log_alive(conn)  # Dies wird das Lebenszeichen protokollieren und die Datenbank aktualisieren

        except Exception as e:
            connection_logger.error(f"[Connection Checker] Ausnahme aufgetreten: {e}")

        time.sleep(10)  # Verzögerung bis zur nächsten Iteration


def log_alive(conn):
    """
    Protokolliert ein Lebenszeichen für die Datenbank und aktualisiert die Lebenszeichen-Überprüfung.
    """
    connection_logger = logging.getLogger("connection_logger")
    
    # Loggt den Gerätenamen für die Lebenszeichen-Überprüfung
    connection_logger.info(f"[log_alive] Verwendeter Gerätename: {device_name}")
    
    # Wenn die Verbindung nicht aktiv ist, wird die Überprüfung übersprungen
    if conn is None or not conn.is_connected():
        connection_logger.warning("[log_alive] Verbindung ist nicht aktiv. Lebenszeichen-Überprüfung übersprungen.")
        return

    try:
        # Sicherstellen, dass der Geräte-Eintrag in der Datenbank vorhanden ist, bevor das Lebenszeichen aktualisiert wird
        insert_initial_log(conn)  # Fügt den Eintrag hinzu, falls er nicht existiert

        # Führen Sie nun die übliche Lebenszeichen-Protokollierung durch
        cursor = conn.cursor()
        sql_update = "UPDATE z_sys_alive_check SET alive_lastcheck = NOW() WHERE alive_system = %s"
        values = (device_name,)
        cursor.execute(sql_update, values)
        conn.commit()
        cursor.close()
        connection_logger.info(f"[log_alive] Lebenszeichen erfolgreich protokolliert für Gerät: {device_name}")

    except Exception as e:
        connection_logger.error(f"[log_alive] Fehler beim Protokollieren des Lebenszeichens: {e}")
        conn_ref['conn'] = None  # Markiere die Verbindung als verloren, falls ein Fehler auftritt

def insert_initial_log(conn):
    """
    Fügt eine erste Zeile in die Tabelle z_sys_alive_check ein, wenn sie noch nicht existiert.
    """
    try:
        # Loggt den Gerätenamen beim Einfügen oder Aktualisieren des Logs
        connection_logger.info(f"[insert_initial_log] Verwendeter Gerätename: {device_name}")
        
        cursor = conn.cursor()
        # Fügt den Eintrag für das System ein oder aktualisiert ihn
        sql_insert = """
        INSERT INTO z_sys_alive_check (alive_system, alive_lastcheck)
        VALUES (%s, NOW())
        ON DUPLICATE KEY UPDATE alive_lastcheck = NOW()
        """
        values = (device_name,)
        cursor.execute(sql_insert, values)
        conn.commit()
        cursor.close()
        connection_logger.info(f"Erster Lebenszeichen-Log für Gerät eingefügt oder aktualisiert: {device_name}")
    except Exception as e:
        connection_logger.error(f"Fehler beim Einfügen oder Aktualisieren des ersten Lebenszeichen-Logs für Gerät {device_name}: {e}")
