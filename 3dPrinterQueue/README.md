# Bambu Lab P1S Print Queue Manager

A Python application for managing print jobs on your Bambu Lab P1S 3D printer with queue management, automatic print processing, and a REST API for remote control.

## Features

- **Print Queue Management**: Add multiple print jobs to a queue that processes automatically
- **Priority System**: Set priority levels for jobs to control print order
- **Automatic Processing**: Background monitor automatically starts the next print when the printer is idle
- **REST API**: Full REST API for remote queue management
- **Print Completion Tracking**: Stores completion data for each finished print job
- **Persistent Storage**: Queue data saved to JSON file and restored on restart
- **Status Monitoring**: Real-time printer status and print progress monitoring

## Requirements

- Python 3.7+
- Bambu Lab P1S 3D Printer
- Network access to your printer
- Printer Access Code (found in printer settings)

## Installation

1. Clone or download this repository

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create your configuration file:
```bash
cp .env.example .env
```

4. Edit the `.env` file with your printer details:
```env
PRINTER_IP=192.168.1.XXX
PRINTER_SERIAL=YOUR_SERIAL_NUMBER
PRINTER_ACCESS_CODE=YOUR_ACCESS_CODE
FLASK_PORT=5000
FLASK_DEBUG=True
QUEUE_DATA_FILE=queue_data.json
```

## Finding Your Printer Details

- **IP Address**: Check your router's connected devices or printer network settings
- **Serial Number**: Found on the printer label or in printer settings
- **Access Code**: Go to printer settings > Network > Access Code

## Usage

### Starting the Application

```bash
python main.py
```

The application will:
1. Connect to your printer
2. Load any existing queue data
3. Start the print monitor
4. Start the REST API server

### API Endpoints

#### Health Check
```bash
GET http://localhost:5000/health
```

#### Printer Status
```bash
GET http://localhost:5000/printer/status
```

#### Add Job to Queue
```bash
POST http://localhost:5000/queue/add
Content-Type: application/json

{
  "file_path": "/path/to/your/file.gcode",
  "file_name": "my_print",
  "priority": 0
}
```

#### Get Queue Status
```bash
GET http://localhost:5000/queue/status
```

#### Get Completed Jobs
```bash
GET http://localhost:5000/queue/completed?limit=10
```

#### Get Job Details
```bash
GET http://localhost:5000/queue/job/<job_id>
```

#### Remove Job from Queue
```bash
DELETE http://localhost:5000/queue/remove/<job_id>
```

#### Get Completion Data
```bash
GET http://localhost:5000/completion/<job_id>
```

#### Manually Connect/Disconnect Printer
```bash
POST http://localhost:5000/printer/connect
POST http://localhost:5000/printer/disconnect
```

## Examples

### Adding a Print Job with cURL

```bash
curl -X POST http://localhost:5000/queue/add \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "/Users/tony/prints/benchy.gcode",
    "file_name": "benchy_v1",
    "priority": 5
  }'
```

### Checking Queue Status with cURL

```bash
curl http://localhost:5000/queue/status
```

### Removing a Job with cURL

```bash
curl -X DELETE http://localhost:5000/queue/remove/JOB_20260106_120000_0001
```

### Python Script Example

```python
import requests

# Add a job
response = requests.post('http://localhost:5000/queue/add', json={
    'file_path': '/path/to/model.gcode',
    'file_name': 'my_model',
    'priority': 10
})
print(response.json())

# Check status
status = requests.get('http://localhost:5000/queue/status').json()
print(f"Queue length: {status['queue_length']}")
print(f"Current job: {status['current_job']}")
```

## How It Works

1. **Queue Management**: Jobs are stored in a priority queue with higher priority jobs printing first
2. **Print Monitor**: A background thread checks the printer status every 5 seconds
3. **Automatic Processing**: When the printer is idle and jobs are queued, the monitor starts the next print
4. **Completion Detection**: The monitor detects when prints finish and stores completion data
5. **Persistence**: All queue data is saved to a JSON file and restored on restart

## File Format Support

The application accepts G-code files (`.gcode`) and automatically converts them to the 3MF format required by Bambu Lab printers.

## Troubleshooting

### Printer Won't Connect
- Verify your printer IP address is correct
- Check that the access code matches your printer settings
- Ensure your printer is on the same network
- Verify the serial number is correct

### Jobs Not Starting
- Check that the print monitor is running (shown on startup)
- Verify the printer is connected: `GET /printer/status`
- Ensure file paths in jobs are valid and accessible
- Check the application logs for errors

### Queue Not Persisting
- Check file permissions for `queue_data.json`
- Verify the `QUEUE_DATA_FILE` path in `.env`

## Architecture

- **[main.py](main.py)**: Application entry point, initialization, and startup
- **[printer_controller.py](printer_controller.py)**: Handles printer communication and control
- **[print_queue.py](print_queue.py)**: Queue management and persistence
- **[print_monitor.py](print_monitor.py)**: Background monitoring and automatic job processing
- **[api_server.py](api_server.py)**: Flask REST API server
- **[config.py](config.py)**: Configuration management

## Security Notes

- The `.env` file contains sensitive printer credentials - keep it secure
- The API has no authentication by default - only run on trusted networks
- Consider adding authentication if exposing the API to the internet

## License

This project uses the unofficial Bambu Labs API library. Check the library's license and terms of use.

## Sources

- [bambulabs-api on PyPI](https://pypi.org/project/bambulabs-api/)
- [BambuTools/bambulabs_api GitHub](https://github.com/BambuTools/bambulabs_api)
- [BambuLabs API Documentation](https://bambutools.github.io/bambulabs_api/)
