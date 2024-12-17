"""
===============================================================================
Projekt: Noatime
Dateiname: gpio_setup.py
Version: 1.0.0
Entwickler: Annatina Christ
Datum: 29.11.2024

Changelog:
- [29.11.2024]: Erste Version.
- [Datum]: Weitere Änderungen/Verbesserungen.

===============================================================================
"""

import RPi.GPIO as GPIO
import time

# GPIO-Modus festlegen (BCM für Broadcom-Nummerierung oder BOARD für physische Pin-Nummern)
GPIO.setmode(GPIO.BCM)  # oder GPIO.setmode(GPIO.BOARD)

# Beispiel: Konfiguration eines Pins (z.B. GPIO 18) als Ausgang
GPIO.setup(18, GPIO.OUT)

# Beispielhafte Nutzung des GPIO
GPIO.output(18, GPIO.HIGH)  # Setze Pin 18 auf HIGH (ein)
time.sleep(1)  # Warte 1 Sekunde
GPIO.output(18, GPIO.LOW)   # Setze Pin 18 auf LOW (aus)

# Bereinige GPIO am Ende des Programms
GPIO.cleanup()  # Schaltet alle verwendeten Pins zurück in den Eingangszustand
