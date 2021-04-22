""" Module for client registration """

import socket
import json
import struct
import io
import base64
import bz2
import sys

from enum import Enum, auto
from socket import socket as Socket
from typing import Callable, Optional, Dict, Tuple, List, Union

import pandas as pd  # type: ignore

from xdg import xdg_data_home
from zenlog import log  # type: ignore

from .job_config import JobConfig

# This is a bug in Pylint: https://github.com/PyCQA/pylint/issues/3882
# pylint: disable=unsubscriptable-object


class State(Enum):
    """ State Enum declaring the current message state """

    AUTHENTICATING: int = auto()
    HEARTBEAT: int = auto()
    READ_JOB: int = auto()
    PROCESSING: int = auto()


def load_access_token(email, model_name) -> Tuple[str, str]:
    """
    Loads the access token from XDG_DATA_HOME using email and model name

        Parameters:
            email (str): The email the model is registered with
            model_name (str): The name of the model to be loaded

        Returns:
            Tuple[str, str]: Tuple of access token and model id
        Raise:
            ValueError: raised if the model name and email pair is not found
                in XDG_DATA_HOME
            FileNotFoundError: raised if XDG_DATA_HOME/sybl.json is not found
                meaning no access token has been stored
    """
    model_key: str = f"{email}.{model_name}"

    path = xdg_data_home() / "sybl.json"
    with path.open("r") as f:  # pylint: disable=invalid-name

        file_contents: str = f.read()
        models_dict: Dict = json.loads(file_contents)

        try:
            model_data = models_dict[model_key]

            return model_data["access_token"], model_data["model_id"]
        except KeyError as e:  # pylint: disable=invalid-name
            log.error("Model not registered")
            raise ValueError(f"Model {model_name} not registered to {email}") from e


def prepare_datasets(train, prediction) -> Tuple[pd.DataFrame, pd.DataFrame, List]:
    """
    Take in datasets to be used in computation and prepares them by removing
    the record ids from each, saving and returning those from the prediction
    set, as they are needed after prediction is done.
    """
    if "record_id" in train.columns:
        # Take record ids from training set
        train.drop(["record_id"], axis=1, inplace=True)
        log.debug("Training Data: %s", train.head())

        # Take record ids from predict set and store for later
        predict_rids = prediction["record_id"].tolist()
        log.debug("Predict Record IDs: %s", predict_rids[:5])

        prediction = prediction.drop(["record_id"], axis=1)
        log.debug("Predict Data: %s", prediction.head())
    else:
        raise AttributeError("Datasets must have record ids for each row")

    return (train, prediction, predict_rids)


def decode_and_decompress(data: str) -> str:
    """
    Decodes the data using Base64 and decompresses it using `bzip2`.

    Args:
        data: The raw string to decode and decompress

    Returns: The decoded and decompressed string
    """
    decoded = base64.b64decode(data.encode())
    return bz2.decompress(decoded).decode()


def compress_and_encode(data: str) -> str:
    """
    Compresses the data using `bzip2` and encodes it using Base64.

    Args:
        data: The raw string to compress and encode

    Returns: A Base64 encoded version of the compressed data
    """
    compressed = bz2.compress(data.encode())
    return base64.b64encode(compressed).decode()


class Sybl:
    """ Main sybl class for a client to use to process data """

    # pylint: disable=too-many-instance-attributes
    def __init__(
        self,
        email: Optional[str] = None,
        model_name: Optional[str] = None,
        callback: Optional[Callable] = None,
        job_config: JobConfig = JobConfig(),
        address: Tuple[str, int] = ("sybl.tech", 7000),
    ) -> None:

        self.email: Optional[str] = email
        self.model_name: Optional[str] = model_name

        self._access_token: Optional[str] = None
        self._model_id: Optional[str] = None
        if email and model_name:
            self._access_token, self._model_id = load_access_token(email, model_name)

        self._sock: Socket = Socket(socket.AF_INET, socket.SOCK_STREAM)
        self._state: State = State.AUTHENTICATING
        self._address: Tuple[str, int] = address

        if callback:
            self.register_callback(callback)
        else:
            self.callback: Optional[Callable] = None

        self.config: JobConfig = job_config
        self.recv_job_config: Optional[Dict] = None

        self._message_stack: List[Dict] = []

    def register_callback(self, callback: Callable):
        """
        Registers the callback for the client

            Parameters:
                callback (Callable): The machine learning callback

            Returns:
                None

            Raise:
                TypeError: If the argument provided is not a callback
        """

        if not callable(callback):
            raise TypeError("Callback provided is not callable")

        self.callback = callback

    def connect(self):
        """
        Connects to the Sybl service

            Parametes:
                None

            Returns:
                None

            Raises:
                AttributeError: raised when accesstoken or model id has not been loaded
                PermissionError: raised when the accesstoken cannot be authorized

        """
        # Check the user has specified a callback here
        if self.callback is None:
            raise AttributeError("Callback has not been registered")

        if not self._access_token or not self._model_id:
            log.error("Model has not been loaded")
            raise AttributeError("Model access token and ID have not been loaded")

        self._sock.connect(self._address)
        log.info("Connected")

        if not self._is_authenticated():
            raise PermissionError("Model access token has not been authenticated")

        self._state = State.HEARTBEAT
        self._begin_state_machine()

    def _begin_state_machine(self):
        # Check the message for authentication successfull

        while True:

            # Keep looping while heartbeating
            while self._state == State.HEARTBEAT:
                self._message_control()

            # If it is a job config, evaluate it
            if self._state == State.READ_JOB:
                self._process_job_config()
            # Otherwise it is data, which should be used in callback
            elif self._state == State.PROCESSING:
                self._process_job()

    def _is_authenticated(self) -> bool:

        response = {
            "AccessToken": {
                "id": self._model_id,
                "token": self._access_token,
            }
        }

        self._send_message(response)
        message = self._read_message()
        try:
            if message["message"] == "Authentication successful":
                return True
        except KeyError:
            pass

        log.error("Authentication not successful")
        return False

    def load_config(self, config: JobConfig) -> None:
        """
        Load the clients job config

            Parameters:
                JobConfig: The clients job config

            Returns:
                None
        """
        if isinstance(config, JobConfig):
            self.config = config
        else:
            raise AttributeError("Config must be valid JobConfig")

    def load_model(self, email: str, model_name: str) -> None:
        """
        Load the model ID and Access Token from xdg_data_home using email.model_name as
        primary key

            Parameters:
                email: email the model is registered
                model_name: Name of the model they want to load

            Returns:
                None
        """

        self._access_token, self._model_id = load_access_token(email, model_name)

        self.email = email
        self.model_name = model_name

    def _process_job(self) -> None:
        log.info("PROCCESSING JOB")

        # Get message from message stack
        data: Dict = self._message_stack.pop()

        # Make sure the dataset ia actually there
        assert "Dataset" in data

        # Get training and prediction datasets
        train = decode_and_decompress(data["Dataset"]["train"])
        predict = decode_and_decompress(data["Dataset"]["predict"])

        train_pd = pd.read_csv(io.StringIO(train))
        predict_pd = pd.read_csv(io.StringIO(predict))

        # Prepare the datasets for callback
        train_pd, predict_pd, predict_rids = prepare_datasets(train_pd, predict_pd)

        # Check the user has specified a callback here to satisfy mypy
        assert self.callback is not None

        predictions = self.callback(train_pd, predict_pd, self.recv_job_config)

        log.debug("Predictions: %s", predictions.head())

        # Attatch record ids onto predictions
        predictions["record_id"] = predict_rids
        cols = predictions.columns.tolist()
        cols.insert(0, cols.pop())
        predictions = predictions[cols]

        assert len(predictions.index) == len(predict_pd.index)

        compressed_predictions: str = compress_and_encode(
            predictions.to_csv(index=False)
        )

        message = {"Predictions": compressed_predictions}
        self._send_message(message)
        self._state = State.HEARTBEAT

    def _message_control(self) -> None:

        response: Dict = self._read_message()

        log.debug("HEARTBEAT")

        if "Alive" in response.keys():
            # Write it back
            self._state = State.HEARTBEAT
            self._send_message(response)
        elif "JobConfig" in response.keys():
            log.info("RECIEVED JOB CONFIG")
            self._state = State.READ_JOB
            self._message_stack.append(response)
        elif "Dataset" in response.keys():
            log.info("RECIEVED DATASET")
            self._state = State.PROCESSING
            self._message_stack.append(response)

    def _process_job_config(self) -> None:
        if self._message_stack:
            job_config = self._message_stack.pop()
        else:
            log.error("Empty Message Stack!\n RETURNING TO HEARTBEAT")
            self._state = State.HEARTBEAT
            return

        assert self.config is not None
        if "JobConfig" not in job_config:
            log.warning("Invalid Job Config Message")
            self._state = State.HEARTBEAT
            return

        accept_job: bool = self.config.compare(job_config["JobConfig"])

        if not accept_job:
            self._send_message({"ConfigResponse": {"accept": False}})
            log.info("REJECTING JOB")
        else:
            self._send_message({"ConfigResponse": {"accept": True}})
            self.recv_job_config = job_config["JobConfig"]
            log.info("ACCEPTING JOB")

        self._state = State.HEARTBEAT

    def _read_message(self) -> Dict:
        size_bytes = self._sock.recv(4)
        # print("size_bytes: {}".format(size_bytes))

        size = struct.unpack(">I", size_bytes)[0]
        log.debug("Message size: %d", size)

        if size > 4096:
            remaining_size = size
            buf: List[int] = []

            while remaining_size > 0:
                chunk = self._sock.recv(4096)
                buf.extend(chunk)

                remaining_size -= 4096

            return json.loads(bytes(buf))

        message: Dict = json.loads(self._sock.recv(size))
        # Error handle
        if "Server" in message.keys():
            # There has been an error in authentication
            if "text" in message["Server"].keys():
                payload: Dict = json.loads(message["Server"]["text"])
                code = message["Server"]["code"]
                self._handle_server_error(code, payload)

        log.info(message)
        return message

    def _send_message(self, message: Union[Dict, str]):
        data = json.dumps(message) if isinstance(message, dict) else message
        encoded = data.encode("utf-8")

        length = (len(data)).to_bytes(4, byteorder="big")

        self._sock.send(length + encoded)

    def _handle_server_error(self, code: str, payload: Dict):
        log.error(f"Error Code In Message: {code}")

        if "message" in payload.keys():
            if payload["message"] == "Locked":
                log.error("Model needs to be unlocked to run")
                sys.exit(1)
        else:
            log.error("Unspecified error given found in communication, closing")
            sys.exit(1)
