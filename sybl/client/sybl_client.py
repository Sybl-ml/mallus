import socket
from socket import socket as Socket
import json
import struct
from enum import Enum, auto
from typing import Callable, Optional, Dict, Tuple, List, Union
import logging

from xdg import xdg_data_home
import pandas as pd


SYBL_IP: str = "127.0.0.1"
DCL_SOCKET: int = 7000

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
formatter = logging.Formatter('%(levelname)s:%(module)s %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

# logging.basicConfig(level=logging.DEBUG, format=format)

class State(Enum):
    AUTHENTICATING: int = auto()
    HEARTBEAT: int = auto()
    READ_JOB: int = auto()
    PROCESSING: int = auto()


class Sybl:

    def __init__(self) -> None:
        
        self.model_name: Optional[str] = None
        self.email: Optional[str] = None

        self._access_token: Optional[str] = None
        self._model_id: Optional[str] = None

        self._sock: Socket = Socket(socket.AF_INET, socket.SOCK_STREAM)
        self._state: State = State.AUTHENTICATING

        self.callback: Optional[Callable] = None
        self.config: bool = False

        self._message_stack: List[Dict] = []
    
    def register_callback(self, callback: Callable):
        # needs more checks

        if not isinstance(callback, Callable):
            raise TypeError("Callback provided is not callable")

        self.callback = callback

    def connect(self):
        # connect to sybl
        self._sock.connect((SYBL_IP, DCL_SOCKET))
        logger.info("Connected")

        if not self._access_token or not self._model_id:
            logger.error("Model has not been loaded")
            return

        if self._is_authenticated():
            return

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
        if message['message'] != 'Authentication successful':
            logger.error("Authentication not successful")
            return False
        
        return True

    def load_config(self) -> None:
        return
    
    def load_model(self, email: str, model_name: str) -> None:

        self._access_token, self._model_id = self._load_access_token(email, model_name)

        self.email = email
        self.model_name = model_name
    
    def _process_job(self) -> None:
        logger.info("PROCCESSING JOB")
        while self._state == State.PROCESSING:

            data: Dict = self._read_message()

            train = data["Dataset"]["train"]
            predict = data["Dataset"]["predict"]

            predictions = self.callback()
            # do your machine learning
            self._send_message("Fuck your machine learning")
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
            
            self._send_message("YES")
            
            self._state = State.PROCESSING
            logger.info("ACCEPTING JOB")
            return True
            
    def _load_access_token(self, email, model_name) -> Tuple[str, str]:

        model_key: str = f"{email}.{model_name}"

        if self.config:
            logger.error("Config options not implemented")
            raise ValueError("Config options not yet implemented")

        path = xdg_data_home() / 'sybl.json'
        with path.open('r') as f:

            file_contents: str = f.read()
            models_dict: Dict = json.loads(file_contents)

            try:
                model_data = models_dict[model_key]

                return model_data["access_token"], model_data["model_id"]
            except ValueError:
                logger.error("Model not registered")
                raise ValueError(f"Model {self.model_name} not registered to {self.email}")
    
    def _read_message(self) -> Dict:
        size_bytes = self._sock.recv(4) 
        # print("size_bytes: {}".format(size_bytes))

        size = struct.unpack(">I", size_bytes)[0]
        # print("size: {}".format(size))

        return json.loads(self._sock.recv(size))

    def _send_message(self, message: Union[Dict, str], dump=True):
        data = json.dumps(message) if dump else message
        data = data.encode("utf-8")

        length = (len(data)).to_bytes(4, byteorder='big')
        # print("length: {}".format(length))

        self._sock.send(length + data)