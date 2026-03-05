import logging
import os
import sys

from flask import Blueprint, request, jsonify
from app import db
from app.models import Ticket, Worker, TicketStatus, TicketPriority
from flask_login import login_required, current_user
from datetime import datetime

bp = Blueprint('tickets', __name__, url_prefix='/api/tickets')
logger = logging.getLogger(__name__)


def _launch_create_ticket_orchestration(ticket):
    """
    Call the Workday CreateTicket orchestration after a ticket is saved.
    Uses workday_mcp_server env and modules. Best-effort: logs errors but does not raise.
    """
    _backend_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    hackathon_root = os.path.dirname(_backend_root)
    workday_dir = os.path.join(hackathon_root, "workday_mcp_server")
    workday_env = os.path.join(workday_dir, ".env")
    if hackathon_root not in sys.path:
        sys.path.insert(0, hackathon_root)
    try:
        from dotenv import load_dotenv
        load_dotenv(workday_env, override=True)
        from workday_mcp_server import workday_auth, workday_orchestrate
    except ImportError as e:
        logger.info("Workday orchestration not available (import failed): %s", e)
        return
    if not workday_orchestrate.get_orchestrate_config().get("base_url"):
        logger.info("WORKDAY_ORCHESTRATE_BASE_URL not set; skipping CreateTicket orchestration launch.")
        return
    reporter_email = ticket.reporter.email if ticket.reporter else None
    if not reporter_email:
        logger.warning("Cannot launch CreateTicket orchestration: ticket has no reporter email.")
        return
    body = {
        "reporter": reporter_email,
        "description": ticket.description or "",
        "status": (ticket.status.value or "open").upper(),
        "priority": (ticket.priority.value or "normal").upper(),
        "tableNumber": (ticket.location_table or "").strip(),
    }
    if ticket.assignee:
        body["assignee"] = ticket.assignee.email
    try:
        token = workday_auth.get_workday_bearer_token()
        workday_orchestrate.launch_orchestration(
            "CreateTicket",
            token,
            app_name="hackathontickets_svfbfp",
            json_body=body,
        )
        logger.info("CreateTicket orchestration launched for ticket %s", ticket.ticket_number)
    except Exception as e:
        logger.warning("CreateTicket orchestration failed for ticket %s: %s", ticket.ticket_number, e)


@bp.route('', methods=['GET'])
@login_required
def get_tickets():
    """Get all tickets with optional filtering"""
    status = request.args.get('status')
    assignee_id = request.args.get('assignee_id', type=int)
    reporter_id = request.args.get('reporter_id', type=int)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    query = Ticket.query

    if status:
        try:
            status_enum = TicketStatus(status)
            query = query.filter_by(status=status_enum)
        except ValueError:
            return jsonify({'error': 'Invalid status'}), 400

    if assignee_id:
        query = query.filter_by(assignee_id=assignee_id)

    if reporter_id:
        query = query.filter_by(reporter_id=reporter_id)

    # Get active tickets (open or in_progress) by default
    if not status:
        query = query.filter(Ticket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS]))

    query = query.order_by(Ticket.created_at.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    tickets = pagination.items

    return jsonify({
        'tickets': [ticket_to_dict(t) for t in tickets],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': pagination.total,
            'pages': pagination.pages
        }
    }), 200


@bp.route('/<int:ticket_id>', methods=['GET'])
@login_required
def get_ticket(ticket_id):
    """Get a specific ticket"""
    ticket = Ticket.query.get_or_404(ticket_id)
    return jsonify(ticket_to_dict(ticket)), 200


@bp.route('', methods=['POST'])
@login_required
# Rate limiting removed for development
def create_ticket():
    """Create a new ticket"""
    data = request.get_json()

    # Get description (sanitization optional for development)
    description = data.get('description', '').strip()[:5000] if data.get('description') else ''
    if not description:
        return jsonify({'error': 'Description is required'}), 400

    # Use PostgreSQL sequence for atomic ticket numbering -- safe under concurrent access
    result = db.session.execute(db.text("SELECT nextval('ticket_number_seq')"))
    ticket_number = result.scalar()

    # Auto-populate location from reporter's table if not provided
    location_table = data.get('location_table') or current_user.table

    ticket = Ticket(
        ticket_number=ticket_number,
        reporter_id=current_user.id,
        description=description,
        location_table=location_table,
        status=TicketStatus.OPEN,
        priority=TicketPriority(data.get('priority', 'normal')),
        ticket_opened=datetime.utcnow(),
    )

    db.session.add(ticket)
    db.session.commit()

    # Launch Workday CreateTicket orchestration (best-effort; does not fail the request)
    _launch_create_ticket_orchestration(ticket)

    return jsonify(ticket_to_dict(ticket)), 201


@bp.route('/<int:ticket_id>', methods=['PUT'])
@login_required
def update_ticket(ticket_id):
    """Update a ticket"""
    ticket = Ticket.query.get_or_404(ticket_id)
    data = request.get_json()

    # Check if user is expert or admin
    if current_user.role.value not in ['expert', 'admin']:
        return jsonify({'error': 'Only experts and admins can update tickets'}), 403

    # Update fields
    if 'status' in data:
        try:
            ticket.status = TicketStatus(data['status'])
            if ticket.status == TicketStatus.CLOSED:
                ticket.ticket_closed = datetime.utcnow()
                # Calculate time to closed
                if ticket.ticket_opened:
                    delta = ticket.ticket_closed - ticket.ticket_opened
                    hours = int(delta.total_seconds() // 3600)
                    minutes = int((delta.total_seconds() % 3600) // 60)
                    ticket.time_to_closed = f"{hours}:{minutes}"
        except ValueError:
            return jsonify({'error': 'Invalid status'}), 400

    if 'assignee_id' in data:
        if data['assignee_id']:
            assignee = Worker.query.get(data['assignee_id'])
            if not assignee:
                return jsonify({'error': 'Assignee not found'}), 404
            ticket.assignee_id = data['assignee_id']
        else:
            ticket.assignee_id = None

    if 'priority' in data:
        try:
            ticket.priority = TicketPriority(data['priority'])
        except ValueError:
            return jsonify({'error': 'Invalid priority'}), 400

    if 'description' in data:
        # Sanitize description on update as well
        ticket.description = data['description'].strip()[:5000] if data.get('description') else ticket.description

    ticket.updated_at = datetime.utcnow()

    db.session.commit()

    return jsonify(ticket_to_dict(ticket)), 200


@bp.route('/<int:ticket_id>/assign', methods=['POST'])
@login_required
def assign_ticket(ticket_id):
    """Assign ticket to current user (expert self-assignment)"""
    ticket = Ticket.query.get_or_404(ticket_id)

    if current_user.role.value not in ['expert', 'admin']:
        return jsonify({'error': 'Only experts and admins can assign tickets'}), 403

    ticket.assignee_id = current_user.id
    ticket.status = TicketStatus.IN_PROGRESS
    ticket.updated_at = datetime.utcnow()

    db.session.commit()

    return jsonify(ticket_to_dict(ticket)), 200


@bp.route('/dashboard', methods=['GET'])
@login_required
def get_dashboard():
    """Get ticket dashboard data"""
    active_tickets = Ticket.query.filter(
        Ticket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS])
    ).order_by(Ticket.created_at.desc()).all()

    return jsonify({
        'active_tickets': [ticket_to_dict(t) for t in active_tickets],
        'count': len(active_tickets)
    }), 200


@bp.route('/leaderboard', methods=['GET'])
@login_required
def get_leaderboard():
    """Get expert leaderboard"""
    from sqlalchemy import func

    closed_tickets = Ticket.query.filter_by(status=TicketStatus.CLOSED).all()

    # Aggregate by assignee
    leaderboard = {}
    for ticket in closed_tickets:
        if ticket.assignee_id:
            assignee_id = ticket.assignee_id
            if assignee_id not in leaderboard:
                leaderboard[assignee_id] = 0
            leaderboard[assignee_id] += 1

    # Get worker details and sort
    leaderboard_data = []
    for assignee_id, count in sorted(leaderboard.items(), key=lambda x: x[1], reverse=True):
        worker = Worker.query.get(assignee_id)
        if worker:
            leaderboard_data.append({
                'worker_id': worker.id,
                'name': worker.name,
                'email': worker.email,
                'closed_count': count
            })

    return jsonify({'leaderboard': leaderboard_data}), 200


def ticket_to_dict(ticket):
    """Convert ticket model to dictionary"""
    return {
        'id': ticket.id,
        'ticket_number': ticket.ticket_number,
        'reporter': {
            'id': ticket.reporter.id,
            'name': ticket.reporter.name,
            'email': ticket.reporter.email
        },
        'description': ticket.description,
        'location_table': ticket.location_table,
        'status': ticket.status.value,
        'priority': ticket.priority.value,
        'assignee': {
            'id': ticket.assignee.id,
            'name': ticket.assignee.name,
            'email': ticket.assignee.email
        } if ticket.assignee else None,
        'time_to_closed': ticket.time_to_closed,
        'ticket_opened': ticket.ticket_opened.isoformat() if ticket.ticket_opened else None,
        'ticket_closed': ticket.ticket_closed.isoformat() if ticket.ticket_closed else None,
        'ticket_thread_link': ticket.ticket_thread_link,
        'created_at': ticket.created_at.isoformat() if ticket.created_at else None,
        'updated_at': ticket.updated_at.isoformat() if ticket.updated_at else None
    }
