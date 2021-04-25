"""
Tests the Authenticate module, such as the `parse_message` function and
ensuring proper handling of `sybl.json`.
"""

# Tests probably don't need a docstring
# pylint: disable=missing-function-docstring

# pylint: disable=redefined-outer-name

import os
import shutil
import tempfile
from unittest.mock import patch

import pytest

from sybl.authenticate import Authentication, parse_message, load_priv_key


@pytest.fixture
def authentication_instance():

    with patch("sybl.authenticate.load_priv_key"):
        instance = Authentication(
            "email", "password", "model_name", address=("ip", 1000)
        )
    instance.access_token = ""
    instance.model_id = 2344423

    return instance


def test_messages_are_parsed_correctly():
    message = {"variant": {"key": "value"}}
    variant, data = parse_message(message)

    assert variant == "variant"
    assert data == {"key": "value"}


def test_invalid_messages_fail_to_parse():
    message = {"variant": {"key": "value"}, "another": "value"}

    with pytest.raises(IndexError):
        parse_message(message)


def test_empty_messages_fail_to_parse():
    message = {}

    with pytest.raises(IndexError):
        parse_message(message)


def test_authentication_creates_sybl_json(authentication_instance):
    # Set the environment variable to a temporary directory
    with tempfile.TemporaryDirectory() as directory:
        os.environ["XDG_DATA_HOME"] = directory

        authentication_instance.save_access_tokens()

        expected_path = os.path.join(directory, "sybl.json")
        assert os.path.isfile(expected_path)


def test_authentication_creates_xdg_data_home(authentication_instance):
    # Set the environment variable to a temporary directory and delete it
    with tempfile.TemporaryDirectory() as directory:
        os.environ["XDG_DATA_HOME"] = directory
        shutil.rmtree(directory)

        authentication_instance.save_access_tokens()

        # Check that the directory exists
        assert os.path.isdir(directory)

        # Check that the file got created
        expected_path = os.path.join(directory, "sybl.json")
        assert os.path.isfile(expected_path)
