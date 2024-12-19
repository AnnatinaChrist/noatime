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
import locale
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


font_path = os.path.join(base_dir, "fonts", "Brother-1816-Regular.ttf")

custom_font = ImageFont.truetype(font_path, size=12)

# Utility Functions
def calculate_height(percent, screen_height):
    """Calculate height as a percentage of the screen height."""
    return int(screen_height * percent)

def resize_image(image_path, target_width):
    """Resize an image to a specific width, maintaining its aspect ratio."""
    image = Image.open(image_path)
    aspect_ratio = image.size[1] / image.size[0]
    target_height = int(target_width * aspect_ratio)
    return image.resize((target_width, target_height), Image.LANCZOS)

def get_image_path(filename):
    """Get the path to an image, handle missing files gracefully."""
    try:
        # Adjust the path to your environment
        return os.path.join("img", filename)
    except FileNotFoundError:
        print(f"Error: {filename} not found.")
        return None

def scale_font(base_size, screen_width, reference_width=800):
    """Scale font size based on the screen width."""
    return int(base_size * (screen_width / reference_width))



# GUI Components
def create_top_frame(root, screen_width, screen_height):
    """Create the top frame with a logo."""
    frame = tk.Frame(root, bg="white", height=calculate_height(0.2, screen_height), bd=0)
    frame.pack(side="top", fill="x")

    # Load and resize the logo
    logo_path = get_image_path("churwork_logo_claim.png")
    if logo_path:
        logo = resize_image(logo_path, int(screen_width * 0.8))
        logo_img = ImageTk.PhotoImage(logo)
        root.logo_img = logo_img  # Prevent garbage collection
        tk.Label(frame, image=logo_img, bg="white", bd=0).pack(side="top", pady=0)

    return frame




def create_center_frame(root, screen_width):
    """Create the center frame with a clock and instructions."""
    global clock_label, instruction_label

    frame = tk.Frame(root, bg="white", bd=0)
    frame.pack(expand=True, fill="both")

    # Scaled font size
    scaled_font_size = scale_font(16, screen_width)

    # Clock Label
    clock_label = tk.Label(frame, text="", bg="white", fg="black",
                           font=("Arial", scaled_font_size), anchor="center", bd=0)
    clock_label.pack(pady=(10, 5))

    # Instruction Label
    instruction_label = tk.Label(frame, text="Guten Tag", bg="white", fg="black",
                                  font=("Arial", scaled_font_size), bd=0)
    instruction_label.pack(expand=True)

    return frame


def create_bottom_frame(root, screen_width, screen_height):
    """Create the bottom frame with a status and a static corner graphic."""
    global server_status_label

    # Create the bottom frame
    frame = tk.Frame(root, bg="white", height=calculate_height(0.2, screen_height), bd=0)
    frame.pack(side="bottom", fill="x")

    # Load and resize the corner graphic (static PNG)
    swirl_path = get_image_path("swirl.png")
    if swirl_path and os.path.exists(swirl_path):  # Ensure the file exists
        scale_factor = 0.5
        swirl_width = int(screen_width * scale_factor)
        swirl = resize_image(swirl_path, swirl_width)
        swirl_img = ImageTk.PhotoImage(swirl)
        root.swirl_img = swirl_img  # Prevent garbage collection
        tk.Label(frame, image=swirl_img, bg="white", bd=0).pack(side="right", padx=0, pady=0)
    else:
        print("Error: PNG file not found or path is invalid:", swirl_path)

    return frame



# Update Functions
def update_time():
    """Update the clock label with the current time and date."""
    from datetime import datetime

    # Get the current time and date
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")  # Format the time
    current_day = now.strftime("%A, %d. %B %Y")  # Format the date (Swiss format)

    # Update the clock label with both date and time
    clock_label.config(text=f"{current_day}\n{current_time}")

    # Schedule the function to run again in 1 second
    clock_label.after(1000, update_time)

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
    


# Main GUI Creation
def create_gui():
    """
    Creates a borderless fullscreen GUI that adapts to screen size.
    """
    global instruction_label, server_status_label, clock_label

    # Root window configuration
    root = tk.Tk()
    root.title("Noatime Stempeluhr")
    root.attributes('-fullscreen', True)  # Fullscreen mode
    root.config(bg="white")  # Set background to white
   


    # Detect screen size
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    # Create GUI frames
    create_top_frame(root, screen_width, screen_height)
    create_center_frame(root, screen_width)
    create_bottom_frame(root, screen_width, screen_height)

    # Start updating the clock
    update_time()

    

    return root




