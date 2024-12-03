"""
===============================================================================
Projekt: Noatime
Dateiname: gui.py
Version: 1.0.0
Entwickler: Annatina Christ
Datum: 29.11.2024
Hier sind alle Elemente für das GUI und Funktionen für die dynamische Darstell-
ung von graphischen Elementen.

Changelog:
- [29.11.24]: Erste Version.
- [Datum]: Weitere Änderungen/Verbesserungen.

===============================================================================
"""


import tkinter as tk
from PIL import Image, ImageTk
import configparser


from time import strftime

# Globale Variablen für die Labels
global instruction_label
global server_status_label

# Version aus der Konfigurationsdatei entnehmen
config = configparser.ConfigParser()
config.read('config/config.cnf')
version = config['version']['version_number']



def create_gui():
    """
    Erstellt das Haupt-GUI-Fenster für die RFID Time Clock.
    Das Fenster enthält das Logo, eine Anleitung und eine Versionsanzeige.
    """
    global instruction_label
    global server_status_label
    root = tk.Tk()
    root.title("Noatime Stempeluhr")  # Setzt den Fenstertitel
    root.attributes('-zoomed', True)  # Maximiert das Fenster
    root.config(bg="white")  # Setzt den Hintergrund auf weiß

    # Hole Bildschirmdimensionen für responsives Design
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    # Erstelle ein Frame, um das Logo oben zu platzieren
    top_frame = tk.Frame(root, bg="white")
    top_frame.pack(side="top", fill="x", expand=False)

    # Lade und passe das Logo an die Bildschirmgröße an
    logo = Image.open('/home/pi_noatime/python/noa_time_alpha/img/churwork_logo_claim.png')
    logo_width = int(screen_width * 0.5)  # Setze die Logo-Breite auf 50% der Bildschirmbreite
    logo_height = int(logo.size[1] * (logo_width / logo.size[0]))  # Behalte das Seitenverhältnis bei
    logo = logo.resize((logo_width, logo_height), Image.LANCZOS)
    logo = ImageTk.PhotoImage(logo)

    # Speichere eine Referenz zum Logo, um eine versehentliche Müllsammlung zu verhindern
    root.logo = logo

    # Zeige das Logo in einem Label innerhalb des Top-Frames an
    logo_label = tk.Label(top_frame, image=logo, bg="white")
    logo_label.pack(pady=10)  # Optionaler Abstand um das Logo

    # Erstelle ein Frame für das Anleitungs-Label
    center_frame = tk.Frame(root, bg="white")
    center_frame.pack(expand=True, fill="both")

    # Füge das Anleitungs-Label hinzu, das sich in der Mitte des Fensters ausdehnt
    instruction_label = tk.Label(center_frame, text="Bitte RFID Tag an Lesegerät halten",
                                 bg="white", fg="black",
                                 font=("Arial", int(screen_height * 0.05), "bold"))  # Schriftgröße abhängig von der Bildschirmhöhe
    instruction_label.pack(expand=True)

    # Erstelle ein Frame für das Versions-Label unten rechts
    bottom_frame = tk.Frame(root, bg="white")
    bottom_frame.pack(side="bottom", fill="x", expand=False)

    # Versions-Label in der unteren rechten Ecke
    version_label = tk.Label(bottom_frame, text=version, 
                             bg="white", fg="gray",
                             font=("FreeMono", 12))  # Kleine Schriftgröße
    version_label.pack(side="right", anchor="se", padx=10, pady=10)  # Positioniere es unten rechts mit Abstand
    
    # Server-Status-Label
    server_status_label = tk.Label(bottom_frame, text="Server Status",
                                   bg="white", fg="white",
                                   font=("Arial", 12))
    server_status_label.pack(side="left", anchor="sw", padx=10, pady=10)
    
    return root

def update_instruction_label(message, duration=2000):
    """
    Aktualisiert das Anleitungs-Label mit einer neuen Nachricht.
    Nach einer bestimmten Dauer (Standard: 2000ms) wird das Label wieder zurückgesetzt.
    """
    instruction_label.config(text=message)
    instruction_label.after(duration, reset_instruction_label)  # Setzt das Label nach der angegebenen Zeit zurück

def reset_instruction_label():
    """
    Setzt das Anleitungs-Label zurück auf die ursprüngliche Nachricht.
    """
    instruction_label.config(text="Bitte RFID Tag an Lesegerät halten")

def update_server_status(is_connected):
    """
    Aktualisiert das Server-Status-Label basierend auf der Verbindung zum Server.
    Zeigt 'Online' in grüner Farbe oder 'Offline' in roter Farbe an.
    """
    if is_connected:
        server_status_label.config(text="Online", bg="green")  # Server ist online
    else:
        server_status_label.config(text="Offline", bg="red")  # Server ist offline
