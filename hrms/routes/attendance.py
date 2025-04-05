# hrms/routes/attendance.py
from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user
import logging

log = logging.getLogger(__name__)
attendance_bp = Blueprint('attendance', __name__, template_folder='../templates/attendance')

@attendance_bp.route('/')
@login_required
def index():
    log.debug(f"Accessing attendance index by user '{current_user.username}'")
    return render_template('index.html', title="Time & Attendance")