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
- [06.12.24]: Datum und Uhr Anzeige
- [10.12.24]: Dateipfade geändert, Datum ist nun auf Deutsch

===============================================================================
"""


import tkinter as tk
from PIL import Image, ImageTk
import configparser
import time
import datetime  # For date and time
import locale
from tkinter import font
from PIL import ImageFont
import os
import sys

# Determine the base directory of the project
if getattr(sys, 'frozen', False):  # If bundled with PyInstaller
    base_dir = sys._MEIPASS  # Path where PyInstaller unpacks files
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))  # Location of the script

# Globale Variablen für die Labels
global instruction_label
global server_status_label
global clock_label

# Version aus der Konfigurationsdatei entnehmen
config = configparser.ConfigParser()
config_path = 'config/config.cnf'
config.read(config_path)
version = config['version']['version_number']
version_name = config['version']['version_name']

locale.setlocale(locale.LC_TIME, "de_CH")

image_path = os.path.join(base_dir, "img", "churwork_logo_claim.png")
font_path = os.path.join(base_dir, "fonts", "Brother-1816-Regular.ttf")

custom_font = ImageFont.truetype(font_path, size=12)
    
def update_time():
    """
    Aktualisiert das Datum und die Uhrzeit.
    """
    now = datetime.datetime.now()
    date_str = now.strftime("%A, %d. %B %Y")  # Schweizer Datumsformat
    time_str = now.strftime("%H:%M:%S")  # 24-hour time format
    clock_label.config(text=f"{date_str}\n{time_str}")
    clock_label.after(1000, update_time)  # Ein Mal pro Sekunde aktualisieren


def create_gui():
    """
    Erstellt das Haupt-GUI-Fenster für die Stempeluhr.
    Das Fenster enthält das Logo, eine Anleitung, die Uhrzeit und das Datum.
    """
    global instruction_label, server_status_label, clock_label

    # Root window configuration
    root = tk.Tk()
    root.title("Noatime Stempeluhr")
    root.attributes('-zoomed', True)  # Fullscreen mode
    root.config(bg="white")  # Set background to white

    # Top Frame (Logo)
    top_frame = tk.Frame(root, bg="white")
    top_frame.pack(side="top", fill="x", expand=False)

    # Load and resize the logo
    logo = Image.open(image_path)
    logo_width = int(root.winfo_screenwidth() * 0.4)
    logo_height = int(logo.size[1] * (logo_width / logo.size[0]))
    logo = logo.resize((logo_width, logo_height), Image.LANCZOS)
    logo_img = ImageTk.PhotoImage(logo)
    root.logo_img = logo_img  # Prevent garbage collection
    logo_label = tk.Label(top_frame, image=logo_img, bg="white")
    logo_label.pack(side="left", padx=10)

    # Center Frame
    center_frame = tk.Frame(root, bg="white")
    center_frame.pack(expand=True, fill="both")

    # Clock Label (Date and Time)
    clock_label = tk.Label(center_frame, text="", bg="white", fg="black",
                           font=(custom_font, 24), anchor="center")
    clock_label.pack(pady=(10, 5))  # Add padding above the instruction label

    # Instruction Label
    instruction_label = tk.Label(center_frame, text="Guten Tag",
                                  bg="white", fg="black", font=(custom_font, 24))
    instruction_label.pack(expand=True)

    # Bottom Frame (Version and Server Status)
    bottom_frame = tk.Frame(root, bg="white")
    bottom_frame.pack(side="bottom", fill="x", expand=False)

    # Version Label
    version_label = tk.Label(bottom_frame, text=f"{version} - {version_name}",
                              bg="white", fg="gray", font=("FreeMono", 12))
    version_label.pack(side="right", padx=10, pady=10)

    # Server Status Label
    server_status_label = tk.Label(bottom_frame, text="Server Status",
                                    bg="white", fg="white", font=("Arial", 12))
    server_status_label.pack(side="left", padx=10, pady=10)

    # Start updating time
    update_time()

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
