# hrms/utils.py

import logging # <--- ADD THIS LINE AT THE TOP
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
             # Use logger defined at the end of the file
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
    dt_start, dt_end = None, None # Initialize
    if not start_date or not end_date: return None

    # Convert start_date
    if isinstance(start_date, str):
        try:
            dt_start = datetime.strptime(start_date.split(' ')[0], '%Y-%m-%d').date()
        except ValueError: pass # Try next format or fail
    elif isinstance(start_date, datetime): dt_start = start_date.date()
    elif isinstance(start_date, date): dt_start = start_date

    # Convert end_date
    if isinstance(end_date, str):
        try:
            dt_end = datetime.strptime(end_date.split(' ')[0], '%Y-%m-%d').date()
        except ValueError: pass
    elif isinstance(end_date, datetime): dt_end = end_date.date()
    elif isinstance(end_date, date): dt_end = end_date

    if dt_start is None or dt_end is None:
        log.warning(f"Could not parse dates for days_between: {start_date}, {end_date}")
        return None

    if dt_start > dt_end:
        log.debug("Start date is after end date in calculate_days_between.")
        return 0

    delta = dt_end - dt_start
    return delta.days + 1 if include_end_date else delta.days

# --- String Helpers ---

def slugify(value, allow_unicode=False):
    """
    Convert string to URL slug.
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

def sanitize_string(input_string, strip=True):
    """Basic sanitation: strips whitespace."""
    if isinstance(input_string, str):
        return input_string.strip() if strip else input_string
    return input_string

# --- Placeholder for other utilities ---
# def format_currency(value, currency_symbol='$'): ...
# def send_email(to, subject, body): ...

# --- Setup logging for this utility module ---
# This logger can be used by functions within this file
log = logging.getLogger(__name__)