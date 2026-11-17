import re


def resolve_tracking_url(post_code: str | None) -> str | None:
    if not post_code:
        return None
    code = post_code.strip()
    if not code:
        return None

    # Russian Post: 14 digits or UPU format (e.g. RA123456789RU)
    if re.fullmatch(r"\d{14}", code) or re.fullmatch(
        r"[A-Za-z]{2}\d{9}[A-Za-z]{2}", code
    ):
        formatted_code = code.upper() if not code.isdigit() else code
        return f"https://www.pochta.ru/tracking#{formatted_code}"

    # CDEK: 10-12 digits
    if re.fullmatch(r"\d{10,12}", code):
        return f"https://www.cdek.ru/ru/tracking?order_id={code}"

    # Boxberry: 2-4 Latin letters followed by 7-12 digits
    if re.fullmatch(r"[A-Za-z]{2,4}\d{7,12}", code):
        return f"https://boxberry.ru/tracking-page?id={code.upper()}"

    return None
