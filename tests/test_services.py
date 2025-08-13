from src.data.services import get_service_summary
from src.app.context_models import BookingContext


def test_get_service_summary_defaults_to_shekel():
    services = [
        {"title": "خدمة", "price": "100", "duration": "00:30"}
    ]
    summary = get_service_summary(services)
    assert "₪" in summary
    assert "د.ك" not in summary


def test_get_service_summary_uses_ctx_currency():
    services = [
        {"title": "خدمة", "price": "100", "duration": "00:30"}
    ]
    ctx = BookingContext(price_currency="KWD")
    summary = get_service_summary(services, ctx)
    assert "د.ك" in summary
    assert "₪" not in summary
