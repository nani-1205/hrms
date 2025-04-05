# hrms/routes/compensation.py
from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user
import logging

log = logging.getLogger(__name__)
compensation_bp = Blueprint('compensation', __name__, template_folder='../templates/compensation')

@compensation_bp.route('/')
@login_required
def index():
    log.debug(f"Accessing compensation index by user '{current_user.username}'")
    # Add role/permission checks if needed
    # if not current_user.role in ['admin', 'hr', 'comp_admin']: abort(403)
    return render_template('index.html', title="Compensation Management")