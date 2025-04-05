# hrms/routes/payroll.py
from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user
import logging

log = logging.getLogger(__name__)
payroll_bp = Blueprint('payroll', __name__, template_folder='../templates/payroll')

@payroll_bp.route('/')
@login_required
def index():
    log.debug(f"Accessing payroll index by user '{current_user.username}'")
    # Add role/permission checks if needed
    # if not current_user.role in ['admin', 'hr', 'payroll_specialist']: abort(403)
    return render_template('index.html', title="Payroll Management")