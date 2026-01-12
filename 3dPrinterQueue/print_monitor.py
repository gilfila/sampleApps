import time
import threading
from typing import Optional
from config import Config


class PrintMonitor:
    def __init__(self, printer_controller, print_queue):
        self.printer = printer_controller
        self.queue = print_queue
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.current_job_id: Optional[str] = None

    def start_monitoring(self):
        if self.monitoring:
            print('Monitor already running')
            return

        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        print('Print monitor started')

    def stop_monitoring(self):
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=10)
        print('Print monitor stopped')

    def _monitor_loop(self):
        while self.monitoring:
            try:
                self._check_and_process_queue()
                time.sleep(Config.MONITOR_INTERVAL)
            except Exception as e:
                print(f'Error in monitor loop: {e}')
                time.sleep(Config.MONITOR_INTERVAL)

    def _check_and_process_queue(self):
        # Ensure printer is connected
        if not self.printer.ensure_connected():
            print('Cannot process queue: printer not connected')
            return

        # If there's a current job, check its status
        if self.current_job_id:
            self._check_current_job()
        else:
            # No current job, try to start the next one
            self._start_next_job()

    def _check_current_job(self):
        try:
            # Check if printer is still printing
            if self.printer.is_printing():
                # Still printing, nothing to do
                status = self.printer.get_status()
                print(f'Current job {self.current_job_id} is printing... '
                      f'{status.get("status", {}).get("print_percentage", 0)}% complete')
                return

            # Check if printer is idle (finished or failed)
            if self.printer.is_idle():
                print(f'Print job {self.current_job_id} has completed')

                # Get completion data
                completion_data = self.printer.get_print_completion_data()

                # Check if print was successful
                gcode_state = completion_data.get('gcode_state', '')

                if gcode_state == 'FINISH':
                    print(f'Job {self.current_job_id} completed successfully')
                    self.queue.mark_job_completed(self.current_job_id, completion_data)
                elif gcode_state == 'FAILED':
                    error = completion_data.get('print_error', 'Unknown error')
                    print(f'Job {self.current_job_id} failed with error: {error}')
                    self.queue.mark_job_failed(self.current_job_id, f'Print failed: {error}')
                else:
                    # Unknown state, mark as completed with the state info
                    print(f'Job {self.current_job_id} ended with state: {gcode_state}')
                    self.queue.mark_job_completed(self.current_job_id, completion_data)

                # Clear current job
                self.current_job_id = None
                self.printer.current_print = None

        except Exception as e:
            print(f'Error checking current job: {e}')

    def _start_next_job(self):
        try:
            # Get next job from queue
            next_job = self.queue.get_next_job()

            if not next_job:
                # No jobs in queue
                return

            print(f'Starting next job: {next_job["id"]} - {next_job["file_name"]}')

            # Mark job as printing
            self.queue.mark_job_printing(next_job['id'])
            self.current_job_id = next_job['id']

            # Start the print job
            result = self.printer.start_print_job(
                next_job['file_path'],
                next_job['file_name']
            )

            if not result['success']:
                print(f'Failed to start print job: {result.get("error")}')
                self.queue.mark_job_failed(
                    next_job['id'],
                    f'Failed to start: {result.get("error")}'
                )
                self.current_job_id = None
            else:
                print(f'Successfully started print job: {next_job["file_name"]}')

        except Exception as e:
            print(f'Error starting next job: {e}')
            if self.current_job_id:
                self.queue.mark_job_failed(self.current_job_id, f'Error: {str(e)}')
                self.current_job_id = None

    def get_status(self):
        return {
            'monitoring': self.monitoring,
            'current_job_id': self.current_job_id,
            'printer_connected': self.printer.is_connected,
            'printer_printing': self.printer.is_printing() if self.printer.is_connected else False
        }
