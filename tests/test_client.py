"""
Test the client module in Sybl, tests the correct of the state machine
and correct responses to messages sent from the DCL
"""

import os
import tempfile
from unittest.mock import Mock

import pytest

from mocket.mocket import mocketize  # type: ignore

from sybl.client import Sybl
from sybl.client.sybl_client import State, load_access_token
from sybl.authenticate import Authentication

# pylint: disable=protected-access
# pylint: disable=missing-function-docstring


@pytest.fixture(scope="function")
def sybl():
    sybl_instance = Sybl()
    sybl_instance._sock = Mock()
    sybl_instance.model_name = "Test Model"
    sybl_instance.email = "model@email"
    sybl_instance._send_message = Mock(name="send_message")

    return sybl_instance


@pytest.fixture
def valid_dataset():

    dataset = {
        "Dataset": {
            "train": """record_id,a,b,c,d,e,f
            0,1,2,3,4,5
            0,1,2,3,4,5
            0,1,2,3,4,5
            """,
            "predict": """record_id,a,b,c,d,e,f
            0,1,2,3,4,
            0,1,2,3,4,
            0,1,2,3,4,
            """,
        }
    }

    return dataset


def test_valid_connect(sybl_instance):
    sybl_instance._access_token = "12345"
    sybl_instance._model_id = "45678"
    sybl_instance.callback = Mock()
    sybl_instance._is_authenticated = Mock(name="_is_authenticated", return_value=True)
    sybl_instance._begin_state_machine = Mock(name="_begin_state_machine")

    assert sybl_instance._state == State.AUTHENTICATING

    sybl_instance.connect()

    assert sybl_instance._state == State.HEARTBEAT

    assert sybl_instance._is_authenticated.called
    assert sybl_instance._begin_state_machine.called


def test_unauthenticated_connect(sybl_instance):
    sybl_instance._access_token = "12345"
    sybl_instance._model_id = "45678"
    sybl_instance.callback = Mock()
    sybl_instance._is_authenticated = Mock(name="_is_authenticated", return_value=False)

    with pytest.raises(
        PermissionError, match="Model access token has not been authenticated"
    ):
        sybl_instance.connect()

    assert sybl_instance._state == State.AUTHENTICATING


def test_no_callback_connect(sybl_instance):

    with pytest.raises(AttributeError, match="Callback has not been registered"):
        sybl_instance.connect()

    assert sybl_instance._state == State.AUTHENTICATING


def test_no_model_id_connect(sybl_instance):
    sybl_instance.callback = Mock()

    with pytest.raises(
        AttributeError, match="Model access token and ID have not been loaded"
    ):
        sybl_instance.connect()

    assert sybl_instance._state == State.AUTHENTICATING


def test_authentication(sybl_instance):
    sybl_instance._read_message = Mock(
        return_value={"message": "Authentication successful"}
    )

    assert sybl_instance._is_authenticated()


def test_not_authentication(sybl_instance):
    sybl_instance._read_message = Mock(
        return_value={"message": "Authentication unsuccessful"}
    )

    assert not sybl_instance._is_authenticated()


def test_bad_response_authentication(sybl_instance):
    sybl_instance._read_message = Mock(return_value={"bad": "response"})

    assert not sybl_instance._is_authenticated()


def test_reject_bad_config(sybl_instance):

    bad_config = "Im not a JobConfig"

    with pytest.raises(AttributeError):
        sybl_instance.load_config(bad_config)


def test_heartbeat(sybl_instance):

    responses = [
        ({"Alive": ""}, State.HEARTBEAT),
        ({"JobConfig": ""}, State.READ_JOB),
        ({"Dataset": ""}, State.PROCESSING),
    ]

    for response in responses:
        sybl_instance._read_message = Mock(return_value=response[0])

        sybl_instance._heartbeat()
        assert sybl_instance._state == response[1]


def test_accept_job_config(sybl_instance):

    sybl_instance._message_stack.append({"JobConfig": {"Test config"}})
    sybl_instance.config.compare = Mock(return_value=True)

    sybl_instance._process_job_config()

    sybl_instance._send_message.assert_called_with({"ConfigResponse": {"accept": True}})
    assert sybl_instance._state == State.HEARTBEAT


def test_reject_job_config(sybl_instance):

    sybl_instance._message_stack.append({"JobConfig": {"Test config"}})
    sybl_instance.config.compare = Mock(return_value=False)

    sybl_instance._process_job_config()

    sybl_instance._send_message.assert_called_with(
        {"ConfigResponse": {"accept": False}}
    )
    assert sybl_instance._state == State.HEARTBEAT


def test_empty_message_stack(sybl_instance):

    sybl_instance._process_job_config()

    assert sybl_instance._state == State.HEARTBEAT


@mocketize
def test_load_access_token(sybl_instance):

    with tempfile.TemporaryDirectory() as directory:
        os.environ["XDG_DATA_HOME"] = directory
        instance = Authentication("model@email", "Test Model")
        instance.access_token = ""
        instance.model_id = "2344423"
        instance.save_access_tokens()

        access_token, model_id = load_access_token(
            sybl_instance.email, sybl_instance.model_name
        )

    assert access_token == ""
    assert model_id == "2344423"


@mocketize
def test_bad_model_name(sybl_instance):

    with tempfile.TemporaryDirectory() as directory:
        os.environ["XDG_DATA_HOME"] = directory
        instance = Authentication("model@email", "Test Model")
        instance.access_token = ""
        instance.model_id = "2344423"
        instance.save_access_tokens()

        with pytest.raises(
            ValueError,
            match=f"Model Nothing here not registered to {sybl_instance.email}",
        ):
            load_access_token(sybl_instance.email, "Nothing here")


def test_file_does_not_exist(sybl_instance):

    with pytest.raises(FileNotFoundError):
        load_access_token(sybl_instance.email, sybl_instance.model_name)