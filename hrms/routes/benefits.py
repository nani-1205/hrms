# hrms/routes/benefits.py
from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user
import logging

log = logging.getLogger(__name__)
benefits_bp = Blueprint('benefits', __name__, template_folder='../templates/benefits')

@benefits_bp.route('/')
@login_required
def index():
    log.debug(f"Accessing benefits index by user '{current_user.username}'")
    # Add role/permission checks if needed
    # if not current_user.role in ['admin', 'hr']: abort(403)
    return render_template('index.html', title="Benefits Management")