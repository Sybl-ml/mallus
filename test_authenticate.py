import pytest

from authenticate import Authentication

def test_authenticator_parses_messages_correctly():
    instance = Authentication("email", "model_name")
    message = {"variant": {"key": "value"}}
    variant, data = instance.parse_message(message)

    assert variant == "variant"
    assert data == {"key": "value"}

def test_invalid_messages_fail_to_parse():
    instance = Authentication("email", "model_name")
    message = {"variant": {"key": "value"}, "another": "value"}

    with pytest.raises(IndexError):
        variant, data = instance.parse_message(message)

def test_empty_messages_fail_to_parse():
    instance = Authentication("email", "model_name")
    message = {}

    with pytest.raises(IndexError):
        variant, data = instance.parse_message(message)
