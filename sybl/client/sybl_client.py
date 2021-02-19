""" Module for client registration """
import socket
import json
import struct
import logging
import io

from enum import Enum, auto
from socket import socket as Socket
from typing import Callable, Optional, Dict, Tuple, List, Union

import pandas as pd  # type: ignore

from xdg import xdg_data_home

from .job_config import JobConfig

# This is a bug in Pylint: https://github.com/PyCQA/pylint/issues/3882
# pylint: disable=unsubscriptable-object

SYBL_IP: str = "127.0.0.1"
DCL_SOCKET: int = 7000

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
formatter = logging.Formatter("%(levelname)s:%(module)s %(message)s")
ch.setFormatter(formatter)
logger.addHandler(ch)


class State(Enum):
    """ State Enum declaring the current message state """

    AUTHENTICATING: int = auto()
    HEARTBEAT: int = auto()
    READ_JOB: int = auto()
    PROCESSING: int = auto()


class Sybl:
    """ Main sybl class for a client to use to process data """

    # pylint: disable=too-many-instance-attributes
    def __init__(self) -> None:

        self.model_name: Optional[str] = None
        self.email: Optional[str] = None

        self._access_token: Optional[str] = None
        self._model_id: Optional[str] = None

        self._sock: Socket = Socket(socket.AF_INET, socket.SOCK_STREAM)
        self._state: State = State.AUTHENTICATING

        self.callback: Optional[Callable] = None
        self.config: JobConfig = JobConfig()

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
        assert self.callback is not None

        self._sock.connect((SYBL_IP, DCL_SOCKET))
        logger.info("Connected")

        if not self._access_token or not self._model_id:
            logger.error("Model has not been loaded")
            raise AttributeError("Model access token and ID have not been loaded")

        if not self._is_authenticated():
            raise PermissionError("Model access token has not been authenticated")

        # Check the message for authentication successfull
        self._state = State.HEARTBEAT

        while True:
            while self._state == State.HEARTBEAT:
                self._heartbeat()

            if self._process_job_config():
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
        if message["message"] != "Authentication successful":
            logger.error("Authentication not successful")
            return False

        return True

    def load_config(self, config: JobConfig) -> None:
        """
        Load the clients job config

            Parameters:
                JobConfig: The clients job config

            Returns:
                None
        """
        self.config = config

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

        self._access_token, self._model_id = self._load_access_token(email, model_name)

        self.email = email
        self.model_name = model_name

    def _process_job(self) -> None:
        logger.info("PROCCESSING JOB")
        while self._state == State.PROCESSING:

            data: Dict = self._read_message()

            train = data["Dataset"]["train"]
            predict = data["Dataset"]["predict"]

            train_pd = pd.read_csv(io.StringIO(train))
            predict_pd = pd.read_csv(io.StringIO(predict))

            predict_rids = None

            if "record_id" in train_pd.columns:
                # Take record ids from training set
                train_pd = train_pd.drop(["record_id"], axis=1)
                print("Training Data: {}".format(train_pd))

                # Take record ids from predict set and store for later
                predict_rids = predict_pd[["record_id"]]
                print("Predict Record IDs: {}".format(predict_rids))

                predict_pd = predict_pd.drop(["record_id"], axis=1)
                print("Predict Data: {}".format(predict_pd))
            else:
                raise AttributeError("Datasets must have record ids for each row")

            # Check the user has specified a callback here to satisfy mypy
            assert self.callback is not None

            predictions = self.callback(train_pd, predict_pd)

            # Attatch record ids onto predictions
            if predict_rids is not None:
                predictions["record_id"] = predict_rids
                cols = predictions.columns.tolist()
                cols = cols[-1:] + cols[:-1]
                predictions = predictions[cols]

            message = {"Predictions": predictions.to_csv(index=False)}
            self._send_message(message)
            self._state = State.HEARTBEAT

    def _heartbeat(self) -> None:

        response: Dict = self._read_message()

        logger.debug("HEARTBEAT")

        if "Alive" in response.keys():
            # Write it back
            self._send_message(response)
        elif "JobConfig" in response.keys():
            logger.info("RECIEVED JOB CONFIG")
            self._state = State.READ_JOB
            self._message_stack.append(response)

    def _process_job_config(self) -> bool:
        while self._state == State.READ_JOB:

            if self._message_stack:
                job_config = self._message_stack.pop()

            assert self.config is not None
            assert "JobConfig" in job_config

            accept_job: bool = self.config.compare(job_config["JobConfig"])

            if not accept_job:
                self._send_message({"ConfigResponse": {"accept": False}})
                self._state = State.HEARTBEAT
                logger.info("REJECTING JOB")
                return False

            self._send_message({"ConfigResponse": {"accept": True}})
            self._state = State.PROCESSING
            logger.info("ACCEPTING JOB")
            return True

    def _load_access_token(self, email, model_name) -> Tuple[str, str]:

        model_key: str = f"{email}.{model_name}"

        path = xdg_data_home() / "sybl.json"
        with path.open("r") as f:  # pylint: disable=invalid-name

            file_contents: str = f.read()
            models_dict: Dict = json.loads(file_contents)

            try:
                model_data = models_dict[model_key]

                return model_data["access_token"], model_data["model_id"]
            except ValueError as e:  # pylint: disable=invalid-name
                logger.error("Model not registered")
                raise ValueError(
                    f"Model {self.model_name} not registered to {self.email}"
                ) from e

    def _read_message(self) -> Dict:
        size_bytes = self._sock.recv(4)
        # print("size_bytes: {}".format(size_bytes))

        size = struct.unpack(">I", size_bytes)[0]
        logger.debug("Message size: %d", size)

        if size > 4096:
            remaining_size = size
            buf: List[int] = []

            while remaining_size > 0:
                chunk = self._sock.recv(4096)
                buf.extend(chunk)

                remaining_size -= 4096

            return json.loads(bytes(buf))
        message: Dict = json.loads(self._sock.recv(size))
        logger.info(message)
        return message

    def _send_message(self, message: Union[Dict, str]):
        data = json.dumps(message) if isinstance(message, dict) else message
        encoded = data.encode("utf-8")

        length = (len(data)).to_bytes(4, byteorder="big")
        # print("length: {}".format(length))

        self._sock.send(length + encoded)
