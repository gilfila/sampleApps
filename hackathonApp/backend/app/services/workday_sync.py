import requests
import logging
from app import db
from app.models import Worker, WorkerRole
from datetime import datetime

logger = logging.getLogger(__name__)


class WorkdaySync:
    """Service for syncing worker data from Workday. No-ops when Workday is not configured."""

    def __init__(self, config=None):
        self._config = config
        self.access_token = None
        self._apply_config(self._config or {})

    def _apply_config(self, c):
        self.tenant = c.get("tenant") or ""
        self.client_id = c.get("client_id") or ""
        self.client_secret = c.get("client_secret") or ""
        self.refresh_token = c.get("refresh_token") or ""
        self.custom_object_name = c.get("custom_object_name") or ""
        self.base_url = f"https://{self.tenant}.workday.com" if self.tenant else ""

    def _ensure_config(self):
        """Load config from app/env if not set; return True if configured."""
        if self._config is None:
            try:
                from app.services.workday_config import get_workday_config, is_workday_configured
                self._config = get_workday_config()
                self._apply_config(self._config)
                if not is_workday_configured():
                    return False
            except Exception as e:
                logger.debug("Workday config load: %s", e)
                return False
        tenant = self._config.get("tenant") if isinstance(self._config, dict) else None
        if not tenant or not self._config.get("client_id") or not self._config.get("client_secret") or not self._config.get("refresh_token"):
            return False
        return True

    def get_access_token(self):
        """Get OAuth2 access token using refresh token. Raises if not configured."""
        if not self._ensure_config():
            raise ValueError("Workday integration is not configured. Set it in Administration.")
        try:
            url = f"{self.base_url}/ccx/service/customreport2/{self.tenant}/RaaS/oauth2/token"
            
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': self.refresh_token,
                'client_id': self.client_id,
                'client_secret': self.client_secret
            }
            
            response = requests.post(url, data=data)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data.get('access_token')
            return self.access_token
            
        except Exception as e:
            logger.error(f"Error getting Workday access token: {str(e)}")
            raise
    
    def fetch_single_worker(self, workday_id):
        """Fetch a single worker from Workday by workday_id."""
        if not self.access_token:
            self.get_access_token()

        try:
            url = f"{self.base_url}/ccx/service/customreport2/{self.tenant}/RaaS/Worker"
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            params = {'Worker_ID': workday_id}

            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            entries = data.get('Report_Entry', [])
            if not entries:
                raise ValueError(f"Worker {workday_id} not found in Workday")
            return entries[0]

        except Exception as e:
            logger.error(f"Error fetching single worker {workday_id}: {e}")
            raise

    def fetch_workers(self):
        """Fetch all workers from Workday"""
        if not self.access_token:
            self.get_access_token()
        
        try:
            # This is a placeholder - actual Workday API endpoint will vary
            # Based on Workday REST API documentation
            url = f"{self.base_url}/ccx/service/customreport2/{self.tenant}/RaaS/Worker"
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            workers_data = response.json()
            return workers_data
            
        except Exception as e:
            logger.error(f"Error fetching workers from Workday: {str(e)}")
            raise
    
    def fetch_worker_custom_object(self, worker_id):
        """Fetch custom object data for a worker"""
        if not self.access_token:
            self.get_access_token()
        
        try:
            # Placeholder for custom object API call
            # Actual endpoint will depend on Workday custom object configuration
            url = f"{self.base_url}/ccx/service/customreport2/{self.tenant}/RaaS/{self.custom_object_name}"
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            params = {
                'Worker_ID': worker_id
            }
            
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            custom_data = response.json()
            return custom_data
            
        except Exception as e:
            logger.error(f"Error fetching custom object for worker {worker_id}: {str(e)}")
            return None
    
    def sync_workers(self):
        """Sync all workers from Workday to database. No-op when not configured."""
        if not self._ensure_config():
            logger.info("Workday not configured; skipping worker sync")
            return
        try:
            workers_data = self.fetch_workers()
            
            # Process workers data
            # This will need to be adapted based on actual Workday API response structure
            for worker_data in workers_data.get('Report_Entry', []):
                workday_id = worker_data.get('Worker_ID')
                if not workday_id:
                    continue
                
                # Check if worker exists
                worker = Worker.query.filter_by(workday_id=workday_id).first()
                
                if not worker:
                    worker = Worker(workday_id=workday_id)
                
                # Update worker fields from Workday
                worker.name = worker_data.get('Name', worker.name)
                worker.email = worker_data.get('Email', worker.email)
                worker.employee_id = worker_data.get('Employee_ID', worker.employee_id)
                worker.department = worker_data.get('Department', worker.department)
                worker.job_title = worker_data.get('Job_Title', worker.job_title)
                worker.manager = worker_data.get('Manager', worker.manager)
                worker.updated_at = datetime.utcnow()
                
                # Fetch custom object data
                custom_data = self.fetch_worker_custom_object(workday_id)
                if custom_data:
                    worker.table = custom_data.get('Table', worker.table)
                    worker.team_name = custom_data.get('Team_Name', worker.team_name)
                    worker.tenant_url = custom_data.get('Tenant_URL', worker.tenant_url)
                    worker.company = custom_data.get('Company', worker.company)
                
                # Set default role if not set
                if not worker.role:
                    worker.role = WorkerRole.HACKER
                
                db.session.add(worker)
            
            db.session.commit()
            logger.info(f"Synced {len(workers_data.get('Report_Entry', []))} workers from Workday")
            
        except Exception as e:
            logger.error(f"Error syncing workers from Workday: {str(e)}")
            db.session.rollback()
            raise
