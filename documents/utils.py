# documents/utils.py
import re
import os

def sanitize_filename(filename: str) -> str:
    """Removes extension and replaces non-alphanumeric characters with underscores."""
    base = os.path.splitext(filename)[0]
    sanitized = re.sub(r"[^\w\-]+", "_", base)
    sanitized = re.sub(r"_+", "_", sanitized).strip("_")
    return sanitized if sanitized else "untitled"