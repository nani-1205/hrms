# hrms/routes/training.py
from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user
import logging

log = logging.getLogger(__name__)
training_bp = Blueprint('training', __name__, template_folder='../templates/training')

@training_bp.route('/')
@login_required
def index():
    log.debug(f"Accessing training index by user '{current_user.username}'")
    # Add role/permission checks if needed
    return render_template('index.html', title="Training & Development")