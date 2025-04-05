# hrms/routes/ess.py
from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user
import logging

log = logging.getLogger(__name__)

# --- Define the Blueprint for Employee Self Service ---
ess_bp = Blueprint(
    'ess',
    __name__,
    template_folder='../templates/ess' # Point to the correct template folder
)
# ---------------------------------------------------

@ess_bp.route('/')
@login_required
def index():
    """Placeholder index route for Employee Self Service module."""
    log.debug(f"Accessing ESS index by user '{current_user.username}'")
    # Usually accessible by all logged-in employees
    return render_template('index.html', title="Employee Self Service")

# Add other ESS routes later, e.g., viewing profile, payslips, updating info
# @ess_bp.route('/my-profile')
# def my_profile(): ...