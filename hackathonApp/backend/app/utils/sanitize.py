import bleach

# No HTML tags allowed -- plain text only
ALLOWED_TAGS = []
ALLOWED_ATTRIBUTES = {}


def sanitize_input(text, max_length=10000):
    """Sanitize user input: strip HTML tags, enforce length limit."""
    if text is None:
        return None
    if not isinstance(text, str):
        raise ValueError("Input must be a string")
    # Strip all HTML
    clean = bleach.clean(text, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES, strip=True)
    # Enforce length
    return clean[:max_length]


def sanitize_search(text, max_length=200):
    """Sanitize search input: strip HTML, escape LIKE wildcards."""
    if text is None:
        return None
    clean = bleach.clean(text, tags=[], attributes={}, strip=True)
    # Escape LIKE metacharacters to prevent LIKE-injection
    clean = clean.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
    return clean[:max_length]
