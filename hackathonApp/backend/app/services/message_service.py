from app import db
from app.models import ChatMessage, ChatLog, MessageType
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class MessageService:
    """Service for message business logic"""
    
    def log_event(self, event_type, worker_id=None, details=None, error_message=None):
        """Log a chat event"""
        try:
            log_entry = ChatLog(
                event_type=event_type,
                worker_id=worker_id,
                details=details,
                error_message=error_message,
                timestamp=datetime.utcnow()
            )
            db.session.add(log_entry)
            db.session.commit()
        except Exception as e:
            logger.error(f"Error logging chat event: {str(e)}")
