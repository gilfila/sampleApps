import time
import zipfile
from io import BytesIO
from typing import Optional, Dict, Any
import bambulabs_api as bl
from config import Config


class PrinterController:
    def __init__(self):
        self.printer: Optional[bl.Printer] = None
        self.is_connected = False
        self.current_print: Optional[str] = None

    def connect(self) -> bool:
        try:
            print(f'Connecting to Bambu Lab P1S Printer at {Config.PRINTER_IP}')
            self.printer = bl.Printer(
                Config.PRINTER_IP,
                Config.PRINTER_ACCESS_CODE,
                Config.PRINTER_SERIAL
            )
            self.printer.connect()
            time.sleep(2)
            self.is_connected = True
            print('Successfully connected to printer')
            return True
        except Exception as e:
            print(f'Failed to connect to printer: {e}')
            self.is_connected = False
            return False

    def disconnect(self):
        if self.printer and self.is_connected:
            try:
                self.printer.disconnect()
                self.is_connected = False
                print('Disconnected from printer')
            except Exception as e:
                print(f'Error disconnecting from printer: {e}')

    def get_status(self) -> Dict[str, Any]:
        if not self.is_connected or not self.printer:
            return {'error': 'Printer not connected', 'connected': False}

        try:
            status = self.printer.get_state()
            return {
                'connected': True,
                'status': status,
                'current_print': self.current_print
            }
        except Exception as e:
            print(f'Error getting printer status: {e}')
            return {'error': str(e), 'connected': False}

    def is_printing(self) -> bool:
        if not self.is_connected or not self.printer:
            return False

        try:
            status = self.printer.get_state()
            gcode_state = status.get('gcode_state', '')

            # Check if printer is in a printing state
            printing_states = ['RUNNING', 'PREPARE', 'HEATING']
            return gcode_state in printing_states
        except Exception as e:
            print(f'Error checking print status: {e}')
            return False

    def is_idle(self) -> bool:
        if not self.is_connected or not self.printer:
            return False

        try:
            status = self.printer.get_state()
            gcode_state = status.get('gcode_state', '')

            # Printer is idle if it's in IDLE or FINISH state
            idle_states = ['IDLE', 'FINISH', 'FAILED']
            return gcode_state in idle_states
        except Exception as e:
            print(f'Error checking idle status: {e}')
            return False

    def create_3mf_from_gcode(self, gcode_content: str) -> BytesIO:
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            gcode_location = "Metadata/plate_1.gcode"
            zipf.writestr(gcode_location, gcode_content)
        zip_buffer.seek(0)
        return zip_buffer

    def start_print_job(self, file_path: str, file_name: str) -> Dict[str, Any]:
        if not self.is_connected or not self.printer:
            return {'success': False, 'error': 'Printer not connected'}

        try:
            # Check if file is already a .3mf file or gcode
            if file_path.endswith('.3mf'):
                # File is already a 3MF archive, read as binary
                with open(file_path, 'rb') as file:
                    io_file = BytesIO(file.read())
                upload_filename = file_name if file_name.endswith('.3mf') else f"{file_name}.3mf"
            else:
                # File is gcode, need to convert to 3MF
                with open(file_path, 'r') as file:
                    gcode = file.read()

                # Create 3MF archive with gcode
                io_file = self.create_3mf_from_gcode(gcode)
                upload_filename = file_name if file_name.endswith('.3mf') else f"{file_name}.3mf"

            # Upload file to printer
            print(f'Uploading {upload_filename} to printer...')
            result = self.printer.upload_file(io_file, upload_filename)

            if "226" not in result:
                return {
                    'success': False,
                    'error': f'Failed to upload file: {result}'
                }

            # Start the print job (plate_number = 1)
            print(f'Starting print job for {upload_filename}...')
            self.printer.start_print(upload_filename, 1)
            self.current_print = file_name

            return {
                'success': True,
                'message': f'Print job started successfully: {upload_filename}',
                'filename': upload_filename
            }

        except Exception as e:
            print(f'Error starting print job: {e}')
            return {
                'success': False,
                'error': str(e)
            }

    def get_print_completion_data(self) -> Dict[str, Any]:
        if not self.is_connected or not self.printer:
            return {'error': 'Printer not connected'}

        try:
            status = self.printer.get_state()

            completion_data = {
                'filename': self.current_print,
                'gcode_state': status.get('gcode_state', ''),
                'print_percentage': status.get('print_percentage', 0),
                'layer_num': status.get('layer_num', 0),
                'total_layer_num': status.get('total_layer_num', 0),
                'remaining_time': status.get('mc_remaining_time', 0),
                'print_error': status.get('print_error', 0),
                'subtask_name': status.get('subtask_name', ''),
            }

            return completion_data
        except Exception as e:
            print(f'Error getting completion data: {e}')
            return {'error': str(e)}

    def ensure_connected(self) -> bool:
        if not self.is_connected:
            return self.connect()
        return True
