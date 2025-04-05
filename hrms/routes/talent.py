# hrms/routes/talent.py
from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user
import logging

log = logging.getLogger(__name__)
talent_bp = Blueprint('talent', __name__, template_folder='../templates/talent')

@talent_bp.route('/')
@login_required
def index():
    log.debug(f"Accessing talent index by user '{current_user.username}'")
    # Add role/permission checks if needed
    # if not current_user.role in ['admin', 'hr', 'manager']: abort(403)
    return render_template('index.html', title="Talent Management")