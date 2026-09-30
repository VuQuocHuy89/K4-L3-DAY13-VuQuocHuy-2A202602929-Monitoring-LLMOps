from app.logging_config import scrub_event
from app.pii import scrub_text


def test_scrub_email() -> None:
    out = scrub_text("Email me at student@vinuni.edu.vn")
    assert "student@" not in out
    assert "REDACTED_EMAIL" in out


def test_scrub_common_vietnamese_phone_formats() -> None:
    phone_numbers = (
        "0901234567",
        "090 123 4567",
        "090.123.4567",
        "090-123-4567",
        "+84 90 123 4567",
    )

    for phone_number in phone_numbers:
        out = scrub_text(f"Contact: {phone_number}")
        assert phone_number not in out
        assert "REDACTED_PHONE_VN" in out


def test_scrub_vietnamese_identity_number() -> None:
    identity_number = "079123456789"
    out = scrub_text(f"CCCD: {identity_number}")

    assert identity_number not in out
    assert "REDACTED_CCCD" in out


def test_scrub_payment_card_number() -> None:
    card_number = "4111 1111 1111 1111"
    out = scrub_text(f"Card: {card_number}")

    assert card_number not in out
    assert "REDACTED_CREDIT_CARD" in out


def test_logging_processor_scrubs_nested_values_before_rendering() -> None:
    event = {
        "event": "request_received",
        "payload": {"metadata": ["student@vinuni.edu.vn", "090 123 4567"]},
    }

    scrubbed = scrub_event(None, "info", event)
    text = str(scrubbed)

    assert "student@vinuni.edu.vn" not in text
    assert "090 123 4567" not in text
    assert "REDACTED_EMAIL" in text
    assert "REDACTED_PHONE_VN" in text
