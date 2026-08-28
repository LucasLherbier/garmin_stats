from datetime import date, timedelta


def pace_to_seconds(pace):
    """Convert pace string (mm:ss) to seconds."""
    h, m, s = map(int, pace.split(':'))
    return m * 60 + s

def format_to_mmss(t):
    try:
        parts = t.split(':')
        s = int(float(parts[-1])) + int(parts[-2])*60
        return f"{s//60:02d}:{s%60:02d}"
    except:
        return "00:00"


def format_duration(seconds):
    if seconds is None:
        return "0:00:00"
    return str(timedelta(seconds=int(seconds))).split(".")[0]

def format_duration_delta(seconds):
    if seconds is None:
        return "0:00:00"
    sign = "+" if seconds > 0 else ""
    return f"{sign}{format_duration(abs(seconds))}"

def safe_format(value, fmt="{:.2f}", default="N/A"):
    if value is None:
        return default
    try:
        return fmt.format(value)
    except (ValueError, TypeError):
        return default
    
    
def format_duration_no_days(seconds):
    if seconds is None:
        return "00:00:00"
    if isinstance(seconds, str) and ":" in seconds:
        return seconds
    try:
        seconds = int(float(seconds))
    except (ValueError, TypeError):
        return str(seconds)
        
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    sec = seconds % 60
    return f"{hours:02}:{minutes:02}:{sec:02}"


def get_monday(d):
    return d - timedelta(days=d.weekday())

def compute_date_range(key):
    today = date.today()
    end = get_monday(today)

    if key == "8_weeks":
        start = end - timedelta(weeks=8)

    elif key == "6_months":
        # Approx 6 months = 26 weeks (close enough for rolling charts)
        start = end - timedelta(weeks=26)

    elif key == "ytd":
        start = get_monday(date(today.year, 1, 1))

    elif key == "all":
        start = get_monday(date(1970, 1, 1))

    else:
        start = None

    return start, end
