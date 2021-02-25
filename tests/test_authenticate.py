"""
Tests the Authenticate module, such as the `parse_message` function and
ensuring proper handling of `sybl.json`.
"""

# Tests probably don't need a docstring
# pylint: disable=missing-function-docstring

import os
import shutil
import tempfile

import pytest

from mocket.mocket import mocketize  # type: ignore

from sybl.authenticate import Authentication, parse_message


@mocketize
def test_messages_are_parsed_correctly():
    message = {"variant": {"key": "value"}}
    variant, data = parse_message(message)

    assert variant == "variant"
    assert data == {"key": "value"}


@mocketize
def test_invalid_messages_fail_to_parse():
    message = {"variant": {"key": "value"}, "another": "value"}

    with pytest.raises(IndexError):
        parse_message(message)


@mocketize
def test_empty_messages_fail_to_parse():
    message = {}

    with pytest.raises(IndexError):
        parse_message(message)


@mocketize
def test_authentication_creates_sybl_json():
    # Set the environment variable to a temporary directory
    with tempfile.TemporaryDirectory() as directory:
        os.environ["XDG_DATA_HOME"] = directory

        instance = Authentication("email", "model_name")
        instance.access_token = ""
        instance.model_id = 2344423

        instance.save_access_tokens()

        expected_path = os.path.join(directory, "sybl.json")
        assert os.path.isfile(expected_path)


@mocketize
def test_authentication_creates_xdg_data_home():
    # Set the environment variable to a temporary directory and delete it
    with tempfile.TemporaryDirectory() as directory:
        os.environ["XDG_DATA_HOME"] = directory
        shutil.rmtree(directory)

        instance = Authentication("email", "model_name")
        instance.access_token = ""
        instance.model_id = 2344423

        instance.save_access_tokens()

        # Check that the directory exists
        assert os.path.isdir(directory)

        # Check that the file got created
        expected_path = os.path.join(directory, "sybl.json")
        assert os.path.isfile(expected_path)
