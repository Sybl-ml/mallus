from authenticate import DCL_SOCKET
from json.decoder import JSONDecodeError
import socket
import json
from socket import socket as Socket
from enum import Enum, auto
from typing import Callable, Optional, Dict, Tuple, List

from xdg import xdg_data_home


SYBL_IP: str = "127.0.0.1"
DCL_SOCKET: int = 7000

class State(Enum):
    AUTHENTICATING: int = auto()
    HEARTBEAT: int = auto()
    ACCEPT_JOB: int = auto()
    PROCESSING: int = auto()
    COMPLETED: int = auto()


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

    def connect(self) -> None:
        # connect to sybl
        self._sock.connect((SYBL_IP, DCL_SOCKET))

        response = {
            "AccessToken": {
                "id": self._model_id,
                "token": self._access_token,
            }
        }

        self._send(response)
        self._recv_message()
        self._state = State.HEARTBEAT
        self._heartbeat()

        if self._process_job_config():
            self._process_job()

    def load_config(self) -> None:
        return
    
    def load_model(self, email: str, model_name: str) -> None:

        self._access_token, self._model_id = self._load_access_token(email, model_name)

        self.email = email
        self.model_name = model_name
    
    def _process_job(self) -> None:

        while self._state == State.PROCESSING:

            response: Dict = json.loads(self._recv_message())

            # do your machine learning
            self._send("Fuck your machine learning")
            self._state = State.COMPLETED

    
    def _heartbeat(self) -> None:
        
        while self._state == State.HEARTBEAT:

            response: Dict = json.loads(self._recv_message())

            print("response: {}".format(response))

            if "Alive" in response.keys():
                # Write it back
                self._send(response)
            elif "JobConfig" in response.keys():
                self._state = State.ACCEPT_JOB
                self._message_stack.append(response)
    
    def _process_job_config(self) -> bool:

        while self._state == State.ACCEPT_JOB:
            
            if self._message_stack:
                job_config = self._message_stack.pop()
            
            self._send("YES")
            
            self._state = State.PROCESSING
            return True
            
    def _recv_message(self) -> List[bytes]:
        
        buffer: List[bytes] = []

        while True:
            data = self._sock.recv(1024)
            print(data)
            if data:
                buffer.extend(data)
            else:
                break
        
        return buffer

    def _load_access_token(self, email, model_name) -> Tuple[str, str]:

        model_key: str = f"{email}.{model_name}"

        if self.config:
            raise ValueError("Config options not yet implemented")

        path = xdg_data_home() / 'sybl.json'
        with path.open('r') as f:

            file_contents: str = f.read()
            models_dict: Dict = json.loads(file_contents)

            try:
                model_data = models_dict[model_key]

                return model_data["access_token"], model_data["model_id"]
            except ValueError:
                raise ValueError(f"Model {self.model_name} not registered to {self.email}")
    
    def _send(self, message: Dict):

        message_str: str = json.dumps(message)
        encoded_message: List[bytes] = message_str.encode('utf-8')
        print(f"SENDING: {message_str}")
        self._sock.send(encoded_message)