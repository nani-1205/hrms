# hrms/routes/documents.py
from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user
import logging

log = logging.getLogger(__name__)
documents_bp = Blueprint('documents', __name__, template_folder='../templates/documents')

@documents_bp.route('/')
@login_required
def index():
    log.debug(f"Accessing documents index by user '{current_user.username}'")
    # Add role/permission checks if needed
    return render_template('index.html', title="Document Management")