import re
import secrets


def slugify_title(title: str) -> str:
    collapsed = re.sub(r"[^a-zA-Z0-9]+", "-", title.strip().lower()).strip("-")
    return collapsed[:48] or "gift"


def generate_share_slug(title: str) -> str:
    return f"{slugify_title(title)}-{secrets.token_hex(3)}"
