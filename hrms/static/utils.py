# hrms/utils.py

import logging # <--- Added Import
from datetime import datetime, date, timedelta
import re
import unicodedata # For slugify

# --- Setup logging for this utility module ---
# Get logger instance. Configured in __init__.py, but get it here too.
log = logging.getLogger(__name__)

# --- Date/Time Formatting ---

def format_datetime(value, fmt='%Y-%m-%d %H:%M:%S', default="N/A"):
    """Formats a datetime object into a string. Handles None values and errors."""
    if isinstance(value, datetime):
        try:
            return value.strftime(fmt)
        except ValueError: # Handle potential formatting errors
             log.warning(f"Could not format datetime {value} with format '{fmt}'. Using default string.")
             return str(value) # Fallback to default string representation
    elif value is None:
        return default # Return default if input is None
    else:
        log.debug(f"format_datetime received non-datetime value: {type(value)}. Returning default.")
        return default # Return default for non-datetime types

def format_date(value, fmt='%Y-%m-%d', default="N/A"):
    """Formats a datetime or date object into a date string. Handles None values."""
    dt_obj = None
    if isinstance(value, datetime):
        dt_obj = value.date()
    elif isinstance(value, date):
        dt_obj = value
    elif isinstance(value, str):
        # Basic check for YYYY-MM-DD format before trying to parse
        if re.match(r'\d{4}-\d{2}-\d{2}', value):
             try:
                 dt_obj = datetime.strptime(value, '%Y-%m-%d').date()
             except ValueError:
                 log.warning(f"String '{value}' looks like a date but failed to parse.")
                 return default # Failed parse
        else:
            return default # String doesn't match expected format
    elif value is None:
         return default
    else:
        log.debug(f"format_date received unexpected type: {type(value)}. Returning default.")
        return default

    # If we have a valid date object now
    if dt_obj:
        try:
            return dt_obj.strftime(fmt)
        except ValueError:
            log.warning(f"Could not format date {dt_obj} with format '{fmt}'. Using default string.")
            return str(dt_obj) # Fallback to default string representation
    else:
         return default # Should not happen if logic above is correct, but as fallback


# --- Calculation Helpers ---

def calculate_age(birth_date):
    """Calculates age from a birth date (datetime or date object, or YYYY-MM-DD string)."""
    if not birth_date: return None
    bday = None

    if isinstance(birth_date, str):
        try:
            bday = datetime.strptime(birth_date.strip(), '%Y-%m-%d').date()
        except ValueError:
            log.warning(f"Invalid date string format for age calculation: {birth_date}")
            return None # Invalid string format
    elif isinstance(birth_date, datetime):
        bday = birth_date.date() # Convert datetime to date
    elif isinstance(birth_date, date):
        bday = birth_date # Already a date object
    else:
        log.warning(f"Invalid type for age calculation: {type(birth_date)}")
        return None # Not a date, datetime, or valid string

    today = date.today()
    # Calculate age accurately, considering month and day
    try:
        age = today.year - bday.year - ((today.month, today.day) < (bday.month, bday.day))
        return age if age >= 0 else 0 # Return 0 for edge cases like birth date in future
    except TypeError: # Catch comparison errors if dates are somehow invalid
        log.error(f"Error comparing dates for age calculation: today={today}, bday={bday}")
        return None

def calculate_days_between(start_date, end_date, include_end_date=True):
    """Calculates the number of days between two dates (datetime or date objects/strings)."""
    dt_start, dt_end = None, None # Initialize
    if not start_date or not end_date: return None

    # Helper to parse date/datetime into date object
    def parse_to_date(input_val):
        if isinstance(input_val, str):
            try:
                # Try parsing YYYY-MM-DD directly
                return datetime.strptime(input_val.strip(), '%Y-%m-%d').date()
            except ValueError:
                try:
                     # Try parsing if it looks like YYYY-MM-DD HH:MM:SS...
                     return datetime.strptime(input_val.strip().split(' ')[0], '%Y-%m-%d').date()
                except ValueError:
                    log.warning(f"Invalid date string format for days calculation: {input_val}")
                    return None
        elif isinstance(input_val, datetime):
            return input_val.date()
        elif isinstance(input_val, date):
            return input_val
        else:
            log.warning(f"Invalid type for days calculation: {type(input_val)}")
            return None

    dt_start = parse_to_date(start_date)
    dt_end = parse_to_date(end_date)

    if dt_start is None or dt_end is None:
        return None # Parsing failed for one or both dates

    if dt_start > dt_end:
        log.debug("Start date is after end date in calculate_days_between.")
        return 0 # Or handle as error?

    try:
        delta = dt_end - dt_start
        return delta.days + 1 if include_end_date else delta.days
    except TypeError:
        log.error(f"Error calculating timedelta between: {dt_start} and {dt_end}")
        return None


# --- String Helpers ---

def slugify(value, allow_unicode=False):
    """
    Convert string to URL slug.
    Handles unicode, converts spaces/dashes to single dash, removes invalid chars, lowercases.
    (Adapted from Django's slugify utility)
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        # Normalize, encode to ASCII ignoring errors, decode back to string
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    # Remove characters that aren't alphanumerics, underscores, or hyphens
    value = re.sub(r'[^\w\s-]', '', value).strip().lower()
    # Replace whitespace and repeated dashes with single dash
    return re.sub(r'[-\s]+', '-', value).strip('-_')


# --- Security & Input Handling ---

def sanitize_string(input_string, strip=True):
    """Basic sanitation: primarily strips leading/trailing whitespace."""
    # Add more sophisticated sanitation (like HTML escaping) if needed
    if isinstance(input_string, str):
        return input_string.strip() if strip else input_string
    # Return non-strings as is, or handle based on needs
    return input_string

# --- Add other utilities below as needed ---
# Example:
# def format_currency(value, currency_symbol='$', precision=2):
#     if isinstance(value, (int, float)):
#         return f"{currency_symbol}{value:,.{precision}f}"
#     return value # Return original if not numeric