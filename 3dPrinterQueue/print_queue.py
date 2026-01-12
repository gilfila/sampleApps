import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from threading import Lock
from config import Config


class PrintQueue:
    def __init__(self):
        self.queue: List[Dict[str, Any]] = []
        self.completed: List[Dict[str, Any]] = []
        self.lock = Lock()
        self.data_file = Config.QUEUE_DATA_FILE
        self.load_from_file()

    def add_to_queue(self, file_path: str, file_name: str, priority: int = 0) -> Dict[str, Any]:
        with self.lock:
            job_id = self._generate_job_id()

            job = {
                'id': job_id,
                'file_path': file_path,
                'file_name': file_name,
                'priority': priority,
                'status': 'queued',
                'added_at': datetime.now().isoformat(),
                'started_at': None,
                'completed_at': None,
                'error': None
            }

            self.queue.append(job)

            # Sort by priority (higher priority first)
            self.queue.sort(key=lambda x: x['priority'], reverse=True)

            self.save_to_file()

            return {
                'success': True,
                'job_id': job_id,
                'position': self.queue.index(job) + 1,
                'message': f'Job added to queue at position {self.queue.index(job) + 1}'
            }

    def remove_from_queue(self, job_id: str) -> Dict[str, Any]:
        with self.lock:
            for i, job in enumerate(self.queue):
                if job['id'] == job_id:
                    if job['status'] == 'printing':
                        return {
                            'success': False,
                            'error': 'Cannot remove job that is currently printing'
                        }

                    removed_job = self.queue.pop(i)
                    self.save_to_file()

                    return {
                        'success': True,
                        'message': f'Job {job_id} removed from queue',
                        'job': removed_job
                    }

            return {
                'success': False,
                'error': f'Job {job_id} not found in queue'
            }

    def get_next_job(self) -> Optional[Dict[str, Any]]:
        with self.lock:
            for job in self.queue:
                if job['status'] == 'queued':
                    return job
            return None

    def mark_job_printing(self, job_id: str) -> bool:
        with self.lock:
            for job in self.queue:
                if job['id'] == job_id:
                    job['status'] = 'printing'
                    job['started_at'] = datetime.now().isoformat()
                    self.save_to_file()
                    return True
            return False

    def mark_job_completed(self, job_id: str, completion_data: Optional[Dict[str, Any]] = None) -> bool:
        with self.lock:
            for i, job in enumerate(self.queue):
                if job['id'] == job_id:
                    job['status'] = 'completed'
                    job['completed_at'] = datetime.now().isoformat()

                    if completion_data:
                        job['completion_data'] = completion_data

                    completed_job = self.queue.pop(i)
                    self.completed.append(completed_job)

                    self.save_to_file()
                    return True
            return False

    def mark_job_failed(self, job_id: str, error: str) -> bool:
        with self.lock:
            for i, job in enumerate(self.queue):
                if job['id'] == job_id:
                    job['status'] = 'failed'
                    job['completed_at'] = datetime.now().isoformat()
                    job['error'] = error

                    failed_job = self.queue.pop(i)
                    self.completed.append(failed_job)

                    self.save_to_file()
                    return True
            return False

    def get_queue_status(self) -> Dict[str, Any]:
        with self.lock:
            return {
                'queue': self.queue.copy(),
                'queue_length': len(self.queue),
                'completed_count': len(self.completed),
                'current_job': next((job for job in self.queue if job['status'] == 'printing'), None)
            }

    def get_completed_jobs(self, limit: int = 10) -> List[Dict[str, Any]]:
        with self.lock:
            return self.completed[-limit:][::-1]  # Return last N jobs in reverse order

    def get_job_by_id(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            for job in self.queue:
                if job['id'] == job_id:
                    return job.copy()

            for job in self.completed:
                if job['id'] == job_id:
                    return job.copy()

            return None

    def _generate_job_id(self) -> str:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        counter = len(self.queue) + len(self.completed)
        return f"JOB_{timestamp}_{counter:04d}"

    def save_to_file(self):
        try:
            data = {
                'queue': self.queue,
                'completed': self.completed
            }
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f'Error saving queue data to file: {e}')

    def load_from_file(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    self.queue = data.get('queue', [])
                    self.completed = data.get('completed', [])

                    # Reset any jobs that were marked as printing
                    for job in self.queue:
                        if job['status'] == 'printing':
                            job['status'] = 'queued'
                            job['started_at'] = None

                print(f'Loaded queue data from {self.data_file}')
            except Exception as e:
                print(f'Error loading queue data from file: {e}')
                self.queue = []
                self.completed = []
        else:
            print(f'No existing queue data file found, starting fresh')
