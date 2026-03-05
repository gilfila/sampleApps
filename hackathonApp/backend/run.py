import os

# Load backend/.env so DATABASE_URL and other config are set (e.g. when run without start-local.sh)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
except ImportError:
    pass

from app import create_app, socketio
from app.services.scheduler import start_scheduler

app = create_app(os.getenv('FLASK_ENV', 'development'))

# Start background scheduler (Workday sync only when configured)
start_scheduler(app)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=True, allow_unsafe_werkzeug=True)
