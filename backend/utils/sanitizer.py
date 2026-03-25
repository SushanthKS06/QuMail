import bleach
from bleach.css_sanitizer import CSSSanitizer

# Allowed tags and attributes for safe HTML rendering
ALLOWED_TAGS = [
    'a', 'abbr', 'acronym', 'b', 'blockquote', 'code', 'em', 'i', 'li', 'ol', 'strong', 'ul',
    'br', 'div', 'p', 'span', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'table', 'thead', 'tbody',
    'tr', 'th', 'td', 'img'
]

ALLOWED_ATTRIBUTES = {
    '*': ['class', 'style'],
    'a': ['href', 'title', 'target'],
    'img': ['src', 'alt', 'title', 'width', 'height'],
}

ALLOWED_STYLES = [
    'color', 'font-family', 'font-weight', 'font-size', 'text-align', 'text-decoration',
    'background-color', 'margin', 'padding', 'width', 'height'
]

def sanitize_html(html_content: str) -> str:
    """
    Sanitize HTML content to prevent XSS attacks while preserving basic formatting.
    Uses bleach to strip dangerous tags and attributes.
    """
    if not html_content:
        return ""
        
    css_sanitizer = CSSSanitizer(allowed_css_properties=ALLOWED_STYLES)
    return bleach.clean(
        html_content,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        css_sanitizer=css_sanitizer,
        strip=True
    )
