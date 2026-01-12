import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Printer Configuration
    PRINTER_IP = os.getenv('PRINTER_IP', '192.168.1.200')
    PRINTER_SERIAL = os.getenv('PRINTER_SERIAL', 'AC12309BH109')
    PRINTER_ACCESS_CODE = os.getenv('PRINTER_ACCESS_CODE', '12347890')

    # Flask Configuration
    FLASK_PORT = int(os.getenv('FLASK_PORT', 5000))
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'

    # Queue Configuration
    QUEUE_DATA_FILE = os.getenv('QUEUE_DATA_FILE', 'queue_data.json')

    # Print Monitoring
    MONITOR_INTERVAL = 5  # seconds between status checks
