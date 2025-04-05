# hrms/utils.py

from datetime import datetime
import re

def format_datetime(value, format='%Y-%m-%d %H:%M'):
    """Formats a datetime object into a string. Handles None values."""
    if isinstance(value, datetime):
        return value.strftime(format)
    return None # Or return "" or "N/A"

def format_date(value, format='%Y-%m-%d'):
    """Formats a datetime object into a date string. Handles None values."""
    if isinstance(value, datetime):
        return value.strftime(format)
    # If stored as string already, maybe just return it? Depends on storage.
    if isinstance(value, str):
         # Basic check if it resembles a date string
         if re.match(r'\d{4}-\d{2}-\d{2}', value):
              return value
    return None

def calculate_age(birth_date):
    """Calculates age from a birth date (datetime object)."""
    if not isinstance(birth_date, datetime):
        return None
    today = datetime.today()
    age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    return age

# Add other potential utilities:
# - Password strength checker
# - Slugify function for generating URL-friendly strings
# - Currency formatting
# - Function to calculate leave duration (considering weekends/holidays)