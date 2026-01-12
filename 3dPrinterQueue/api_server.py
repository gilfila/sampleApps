from flask import Flask, request, jsonify
from typing import Dict, Any
import os


class APIServer:
    def __init__(self, print_queue, printer_controller):
        self.app = Flask(__name__)
        self.queue = print_queue
        self.printer = printer_controller
        self._setup_routes()

    def _setup_routes(self):
        @self.app.route('/health', methods=['GET'])
        def health():
            return jsonify({
                'status': 'healthy',
                'printer_connected': self.printer.is_connected
            }), 200

        @self.app.route('/printer/status', methods=['GET'])
        def printer_status():
            status = self.printer.get_status()
            return jsonify(status), 200

        @self.app.route('/queue/add', methods=['POST'])
        def add_to_queue():
            data = request.json

            if not data or 'file_path' not in data:
                return jsonify({
                    'success': False,
                    'error': 'file_path is required'
                }), 400

            file_path = data['file_path']

            if not os.path.exists(file_path):
                return jsonify({
                    'success': False,
                    'error': f'File not found: {file_path}'
                }), 404

            file_name = data.get('file_name', os.path.basename(file_path))
            priority = data.get('priority', 0)

            result = self.queue.add_to_queue(file_path, file_name, priority)
            return jsonify(result), 201 if result['success'] else 400

        @self.app.route('/queue/remove/<job_id>', methods=['DELETE'])
        def remove_from_queue(job_id):
            result = self.queue.remove_from_queue(job_id)
            return jsonify(result), 200 if result['success'] else 400

        @self.app.route('/queue/status', methods=['GET'])
        def queue_status():
            status = self.queue.get_queue_status()
            return jsonify(status), 200

        @self.app.route('/queue/job/<job_id>', methods=['GET'])
        def get_job(job_id):
            job = self.queue.get_job_by_id(job_id)

            if job:
                return jsonify(job), 200
            else:
                return jsonify({
                    'error': f'Job {job_id} not found'
                }), 404

        @self.app.route('/queue/completed', methods=['GET'])
        def get_completed_jobs():
            limit = request.args.get('limit', 10, type=int)
            completed = self.queue.get_completed_jobs(limit)
            return jsonify({
                'completed_jobs': completed,
                'count': len(completed)
            }), 200

        @self.app.route('/completion/<job_id>', methods=['GET'])
        def get_completion_data(job_id):
            job = self.queue.get_job_by_id(job_id)

            if not job:
                return jsonify({
                    'error': f'Job {job_id} not found'
                }), 404

            if job['status'] != 'completed':
                return jsonify({
                    'error': f'Job {job_id} is not completed yet',
                    'current_status': job['status']
                }), 400

            return jsonify({
                'job_id': job_id,
                'completion_data': job.get('completion_data', {}),
                'completed_at': job.get('completed_at')
            }), 200

        @self.app.route('/printer/connect', methods=['POST'])
        def connect_printer():
            success = self.printer.connect()
            return jsonify({
                'success': success,
                'connected': self.printer.is_connected
            }), 200 if success else 500

        @self.app.route('/printer/disconnect', methods=['POST'])
        def disconnect_printer():
            self.printer.disconnect()
            return jsonify({
                'success': True,
                'connected': self.printer.is_connected
            }), 200

    def run(self, host='0.0.0.0', port=5000, debug=False):
        self.app.run(host=host, port=port, debug=debug, use_reloader=False)
