# hrms/routes/workforce.py
from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user
import logging

log = logging.getLogger(__name__)
workforce_bp = Blueprint('workforce', __name__, template_folder='../templates/workforce')

@workforce_bp.route('/')
@login_required
def index():
    log.debug(f"Accessing workforce index by user '{current_user.username}'")
    # Add role/permission checks if needed
    # if not current_user.role in ['admin', 'hr', 'manager']: abort(403)
    return render_template('index.html', title="Workforce Management")