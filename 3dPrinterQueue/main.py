import signal
import sys
from config import Config
from printer_controller import PrinterController
from print_queue import PrintQueue
from print_monitor import PrintMonitor
from api_server import APIServer


def signal_handler(sig, frame):
    print('\nShutting down gracefully...')
    monitor.stop_monitoring()
    printer.disconnect()
    sys.exit(0)


if __name__ == '__main__':
    print('=' * 60)
    print('Bambu Lab P1S Print Queue Manager')
    print('=' * 60)

    # Initialize components
    print('\nInitializing components...')
    printer = PrinterController()
    queue = PrintQueue()
    monitor = PrintMonitor(printer, queue)
    api = APIServer(queue, printer)

    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Connect to printer
    print('\nConnecting to printer...')
    if printer.connect():
        print('Successfully connected to Bambu Lab P1S')
    else:
        print('Warning: Failed to connect to printer')
        print('The application will continue, but printing will not work until connected')

    # Start print monitor
    print('\nStarting print monitor...')
    monitor.start_monitoring()

    # Show queue status
    print('\nQueue Status:')
    status = queue.get_queue_status()
    print(f'  Jobs in queue: {status["queue_length"]}')
    print(f'  Completed jobs: {status["completed_count"]}')

    # Start API server
    print('\n' + '=' * 60)
    print(f'Starting API server on port {Config.FLASK_PORT}...')
    print('=' * 60)
    print('\nAPI Endpoints:')
    print(f'  GET  http://localhost:{Config.FLASK_PORT}/health')
    print(f'  GET  http://localhost:{Config.FLASK_PORT}/printer/status')
    print(f'  POST http://localhost:{Config.FLASK_PORT}/printer/connect')
    print(f'  POST http://localhost:{Config.FLASK_PORT}/printer/disconnect')
    print(f'  POST http://localhost:{Config.FLASK_PORT}/queue/add')
    print(f'  GET  http://localhost:{Config.FLASK_PORT}/queue/status')
    print(f'  GET  http://localhost:{Config.FLASK_PORT}/queue/completed')
    print(f'  GET  http://localhost:{Config.FLASK_PORT}/queue/job/<job_id>')
    print(f'  DELETE http://localhost:{Config.FLASK_PORT}/queue/remove/<job_id>')
    print(f'  GET  http://localhost:{Config.FLASK_PORT}/completion/<job_id>')
    print('\nPress Ctrl+C to stop the server')
    print('=' * 60 + '\n')

    try:
        api.run(host='0.0.0.0', port=Config.FLASK_PORT, debug=Config.FLASK_DEBUG)
    except Exception as e:
        print(f'\nError running API server: {e}')
        monitor.stop_monitoring()
        printer.disconnect()
        sys.exit(1)
