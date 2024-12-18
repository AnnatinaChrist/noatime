Noatime - RFID Time Tracking Application
Project Overview
Noatime is an RFID-based time tracking application designed for easy clock-in and clock-out using NFC cards. The application interacts with a PN532 RFID reader, manages connections to a database for storing time stamps, and supports offline functionality for situations where the database is unavailable.

Features
RFID Time Tracking: Uses an NFC RFID reader (PN532) to register clock-in and clock-out times based on RFID tag scans.
Database Integration: The application connects to a MySQL database for saving time stamps.
Offline Mode: If the database is unavailable, the application stores the time stamps in a backup file for later processing.
Health Monitoring: Periodic checks ensure that the RFID reader is responsive, and it attempts to reset the reader if it stops working.
Threaded Architecture: Utilizes Python's threading to run the RFID reader and database connection monitoring concurrently.
