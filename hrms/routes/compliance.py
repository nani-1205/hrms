# hrms/routes/compliance.py
from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user
import logging

log = logging.getLogger(__name__)
compliance_bp = Blueprint('compliance', __name__, template_folder='../templates/compliance')

@compliance_bp.route('/')
@login_required
def index():
    log.debug(f"Accessing compliance index by user '{current_user.username}'")
    # Add role/permission checks if needed
    # if not current_user.role in ['admin', 'hr', 'compliance_officer']: abort(403)
    return render_template('index.html', title="Compliance")