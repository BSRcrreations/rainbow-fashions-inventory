from __future__ import annotations

import re


def normalize_customer_phone(value: str | None) -> str | None:
    """Return the store's canonical phone key, or ``None`` for an empty value.

    The POS is used in India, so a 10 digit number and its +91/0091 form refer
    to the same customer. Keeping one canonical value makes store-scoped
    duplicate checks reliable while still accepting normal cashier input.
    """
    if value is None:
        return None
    digits = re.sub(r"\D", "", value)
    if digits.startswith("00"):
        digits = digits[2:]
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    if not digits:
        return None
    if not 8 <= len(digits) <= 15:
        raise ValueError("Phone number must contain 8 to 15 digits")
    return digits
