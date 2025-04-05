# hrms/utils.py

from datetime import datetime, date, timedelta
import re
import unicodedata # For slugify

# --- Date/Time Formatting ---

def format_datetime(value, fmt='%Y-%m-%d %H:%M:%S', default="N/A"):
    """Formats a datetime object into a string. Handles None values and errors."""
    if isinstance(value, datetime):
        try:
            return value.strftime(fmt)
        except ValueError: # Handle potential formatting errors
             log.warning(f"Could not format datetime {value} with format '{fmt}'. Using default string.")
             return str(value) # Fallback to default string representation
    return default # Return default for None or non-datetime types

def format_date(value, fmt='%Y-%m-%d', default="N/A"):
    """Formats a datetime or date object into a date string. Handles None values."""
    if isinstance(value, datetime):
        try:
            return value.strftime(fmt)
        except ValueError:
             log.warning(f"Could not format datetime {value} as date with format '{fmt}'. Using default string.")
             return str(value.date())
    elif isinstance(value, date):
         try:
            return value.strftime(fmt)
         except ValueError:
             log.warning(f"Could not format date {value} with format '{fmt}'. Using default string.")
             return str(value)
    # Handle if it's already a string that looks like the target date format
    if isinstance(value, str) and re.match(r'\d{4}-\d{2}-\d{2}', value):
        # Basic validation - might need more robust parsing/validation if format varies
        return value
    return default

# --- Calculation Helpers ---

def calculate_age(birth_date):
    """Calculates age from a birth date (datetime or date object, or YYYY-MM-DD string)."""
    if not birth_date: return None

    if isinstance(birth_date, str):
        try:
            birth_date = datetime.strptime(birth_date, '%Y-%m-%d').date()
        except ValueError:
            log.warning(f"Invalid date string format for age calculation: {birth_date}")
            return None # Invalid string format
    elif isinstance(birth_date, datetime):
        birth_date = birth_date.date() # Convert datetime to date
    elif not isinstance(birth_date, date):
        log.warning(f"Invalid type for age calculation: {type(birth_date)}")
        return None # Not a date, datetime, or valid string

    today = date.today()
    # Calculate age accurately
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    return age if age >= 0 else 0 # Return 0 for edge cases like birth date in future

def calculate_days_between(start_date, end_date, include_end_date=True):
    """Calculates the number of days between two dates (datetime or date objects/strings)."""
    if not start_date or not end_date: return None

    for dt in [start_date, end_date]:
        if isinstance(dt, str):
            try:
                # Try parsing common formats, add more as needed
                if ' ' in dt: # Assume datetime string
                    dt_obj = datetime.strptime(dt.split(' ')[0], '%Y-%m-%d').date()
                else: # Assume date string
                    dt_obj = datetime.strptime(dt, '%Y-%m-%d').date()
            except ValueError:
                log.warning(f"Invalid date string format for days calculation: {dt}")
                return None
        elif isinstance(dt, datetime):
            dt_obj = dt.date()
        elif isinstance(dt, date):
            dt_obj = dt
        else:
            log.warning(f"Invalid type for days calculation: {type(dt)}")
            return None

        # Assign back to start/end after conversion
        if dt is start_date: start_date = dt_obj
        if dt is end_date: end_date = dt_obj

    if start_date > end_date:
        log.debug("Start date is after end date in calculate_days_between.")
        return 0 # Or None or raise error, depending on desired behavior

    delta = end_date - start_date
    return delta.days + 1 if include_end_date else delta.days


# --- String Helpers ---

def slugify(value, allow_unicode=False):
    """
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    (Adapted from Django's slugify utility)
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value.lower())
    return re.sub(r'[-\s]+', '-', value).strip('-_')


# --- Security & Input Handling ---
# These are very basic examples. Use dedicated libraries for robust handling.

def sanitize_string(input_string, strip=True):
    """Basic sanitation: strips whitespace."""
    if isinstance(input_string, str):
        return input_string.strip() if strip else input_string
    return input_string

# Example of a potential permission check structure (adapt as needed)
# from flask_login import current_user
# def check_permission(required_roles):
#     """Decorator or simple check function for role-based access."""
#     if not isinstance(required_roles, (list, tuple)):
#         required_roles = [required_roles]
#     if not current_user.is_authenticated or current_user.role not in required_roles:
#         return False # Or raise PermissionDenied or abort(403) in routes
#     return True

# --- Placeholder for other utilities ---
# def format_currency(value, currency_symbol='$'): ...
# def send_email(to, subject, body): ... (using Flask-Mail maybe)

# Setup logging for this utility module
log = logging.getLogger(__name__)