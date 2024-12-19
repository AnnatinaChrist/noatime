"""
===============================================================================
Projekt: Noatime
Dateiname: config_loader.py
Version: 1.0.0
Entwickler: Annatina Christ
Datum: 29.11.2024

Beschreibung:
Lädt die Konfigurationsdatei damit diese dann in den andere Skripts verwendet
werden kann.

Changelog:
- [29.11.24]: Erste Version.
- [02.12.24]: Config Datei ist nun im Ordner Config.

===============================================================================
"""
import os

def load_config(file_name="config.cnf"):
    """
    Load configuration from a .cnf file located in the 'config' directory 
    and return a dictionary grouped by sections.
    """
    config = {}
    current_section = None

    # Get the current script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config", file_name)

    try:
        with open(config_path, "r") as f:
            for line in f:
                line = line.strip()

                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue

                # Handle sections
                if line.startswith("[") and line.endswith("]"):
                    current_section = line[1:-1].strip()
                    config[current_section] = {}
                    continue

                # Handle key-value pairs
                if "=" in line:
                    key, value = line.split("=", 1)

                    # If value references an environment variable, resolve it
                    if value.startswith("${") and value.endswith("}"):
                        env_var = value[2:-1]  # Extract the variable name
                        value = os.getenv(env_var, '')  # Resolve the variable
                        if not value:
                            raise ValueError(f"Environment variable {env_var} is not set.")

                    # Add to the current section or the main config
                    if current_section:
                        config[current_section][key.strip()] = value.strip()
                    else:
                        config[key.strip()] = value.strip()
                else:
                    print(f"Skipping invalid line (no '=' found): {line}")
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file {file_name} not found in the 'config' folder.")
    except Exception as e:
        raise Exception(f"Error reading configuration file: {e}")

    return config





