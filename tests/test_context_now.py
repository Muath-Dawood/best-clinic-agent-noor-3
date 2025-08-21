from src.app.context_models import BookingContext

def test_now_factory_changes_between_instances():
    a = BookingContext().current_datetime
    b = BookingContext().current_datetime
    assert a != "" and b != "" and a != b
