"""
Test the client module in Sybl, tests the correct of the state machine
and correct responses to messages sent from the DCL
"""

import os
import tempfile
from unittest import mock
from unittest.mock import Mock

import pytest

from mocket.mocket import mocketize  # type: ignore

from sybl.client import JobConfig, Sybl
from sybl.client.sybl_client import State, load_access_token
from sybl.authenticate import Authentication


@pytest.fixture(scope="function")
def sybl():
    sybl = Sybl()
    sybl._sock = Mock()
    sybl.model_name = "Test Model"
    sybl.email = "model@email"
    sybl._send_message = Mock(name="send_message")

    return sybl


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


def test_valid_connect(sybl):
    sybl._access_token = "12345"
    sybl._model_id = "45678"
    sybl.callback = Mock()
    sybl._is_authenticated = Mock(name="_is_authenticated", return_value=True)
    sybl._begin_state_machine = Mock(name="_begin_state_machine")

    assert sybl._state == State.AUTHENTICATING

    sybl.connect()

    assert sybl._state == State.HEARTBEAT

    assert sybl._is_authenticated.called
    assert sybl._begin_state_machine.called


def test_unauthenticated_connect(sybl):
    sybl._access_token = "12345"
    sybl._model_id = "45678"
    sybl.callback = Mock()
    sybl._is_authenticated = Mock(name="_is_authenticated", return_value=False)

    with pytest.raises(
        PermissionError, match="Model access token has not been authenticated"
    ):
        sybl.connect()

    assert sybl._state == State.AUTHENTICATING


def test_no_callback_connect(sybl):

    with pytest.raises(AttributeError, match="Callback has not been registered"):
        sybl.connect()

    assert sybl._state == State.AUTHENTICATING


def test_no_model_id_connect(sybl):
    sybl.callback = Mock()

    with pytest.raises(
        AttributeError, match="Model access token and ID have not been loaded"
    ):
        sybl.connect()

    assert sybl._state == State.AUTHENTICATING


def test_authentication(sybl):
    sybl._read_message = Mock(return_value={"message": "Authentication successful"})

    assert sybl._is_authenticated()


def test_not_authentication(sybl):
    sybl._read_message = Mock(return_value={"message": "Authentication unsuccessful"})

    assert not sybl._is_authenticated()


def test_bad_response_authentication(sybl):
    sybl._read_message = Mock(return_value={"bad": "response"})

    assert not sybl._is_authenticated()


def test_reject_bad_config(sybl):

    bad_config = "Im not a JobConfig"

    with pytest.raises(AttributeError):
        sybl.load_config(bad_config)


def test_heartbeat(sybl):

    responses = [
        ({"Alive": ""}, State.HEARTBEAT),
        ({"JobConfig": ""}, State.READ_JOB),
        ({"Dataset": ""}, State.PROCESSING),
    ]

    for response in responses:
        sybl._read_message = Mock(return_value=response[0])

        sybl._heartbeat()
        assert sybl._state == response[1]


def test_accept_job_config(sybl):

    sybl._message_stack.append({"JobConfig": {"Test config"}})
    sybl.config.compare = Mock(return_value=True)

    sybl._process_job_config()

    sybl._send_message.assert_called_with({"ConfigResponse": {"accept": True}})
    assert sybl._state == State.HEARTBEAT


def test_reject_job_config(sybl):

    sybl._message_stack.append({"JobConfig": {"Test config"}})
    sybl.config.compare = Mock(return_value=False)

    sybl._process_job_config()

    sybl._send_message.assert_called_with({"ConfigResponse": {"accept": False}})
    assert sybl._state == State.HEARTBEAT


def test_empty_message_stack(sybl):

    sybl._process_job_config()

    assert sybl._state == State.HEARTBEAT


@pytest.fixture(scope="function")
@mocketize
def temporary_access_file(tmpdir_factory):
    directory = tmpdir_factory.mktemp("xdg")
    os.environ["XDG_DATA_HOME"] = str(directory)

    instance = Authentication("model@email", "Test Model")
    instance.access_token = ""
    instance.model_id = "2344423"
    instance.save_access_tokens()

    return directory


@mocketize
def test_load_access_token(sybl):

    with tempfile.TemporaryDirectory() as directory:
        os.environ["XDG_DATA_HOME"] = directory
        instance = Authentication("model@email", "Test Model")
        instance.access_token = ""
        instance.model_id = "2344423"
        instance.save_access_tokens()

        access_token, model_id = load_access_token(sybl.email, sybl.model_name)

    assert access_token == ""
    assert model_id == "2344423"


@mocketize
def test_bad_model_name(sybl):

    with tempfile.TemporaryDirectory() as directory:
        os.environ["XDG_DATA_HOME"] = directory
        instance = Authentication("model@email", "Test Model")
        instance.access_token = ""
        instance.model_id = "2344423"
        instance.save_access_tokens()

        with pytest.raises(
            ValueError, match=f"Model Nothing here not registered to {sybl.email}"
        ):
            load_access_token(sybl.email, "Nothing here")


def test_file_does_not_exist(sybl):

    with pytest.raises(FileNotFoundError):
        load_access_token(sybl.email, sybl.model_name)