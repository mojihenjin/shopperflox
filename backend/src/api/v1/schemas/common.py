from typing import Annotated

from pydantic import AfterValidator


def validate_safe_url(v: str) -> str:
    val = v.strip()
    if not val:
        return ""
    if any(ch.isspace() or ord(ch) < 32 for ch in val):
        raise ValueError("URL must not contain whitespace or control characters")
    lower = val.lower()
    if lower.startswith(("javascript:", "data:", "vbscript:", "file:")):
        raise ValueError("URL scheme is forbidden")
    if not (lower.startswith("http://") or lower.startswith("https://")):
        raise ValueError("URL must start with http:// or https://")
    return val


def validate_safe_media_or_http_url(v: str) -> str:
    val = v.strip()
    if not val:
        raise ValueError("URL cannot be empty")
    if any(ch.isspace() or ord(ch) < 32 for ch in val):
        raise ValueError("URL must not contain whitespace or control characters")
    lower = val.lower()
    if lower.startswith(("javascript:", "data:", "vbscript:", "file:")):
        raise ValueError("URL scheme is forbidden")
    if (
        lower.startswith("http://")
        or lower.startswith("https://")
        or val.startswith("/media/")
    ):
        return val
    raise ValueError("URL must start with http://, https://, or /media/")


SafeUrl = Annotated[str, AfterValidator(validate_safe_url)]
SafeMediaOrHttpUrl = Annotated[str, AfterValidator(validate_safe_media_or_http_url)]
