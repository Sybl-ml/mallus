from json.decoder import JSONDecodeError
import socket
import json
from socket import socket as Socket
from enum import Enum, auto
from typing import Callable, Optional, Dict

from xdg import xdg_data_home

class State(Enum):
    AUTHENTICATING: int = auto()
    HEARTBEAT: int = auto()
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

    def connect(self) -> None:
        # connect to sybl
        return

    def start(self, callback: Callable) -> None:
        # start heartbeating and then process data
        return
    
    def load_config(self) -> None:
        return
    
    def load_model(self, email: str, model_name: str) -> None:

        return
    
    def _heartbeat(self) -> None:
        return

    def _load_access_token(self) -> None:

        model_key: str = f"{self.email}.{self.model_name}"

        if self.config:
            raise ValueError("Config options not yet implemented")

        path = xdg_data_home() / 'sybl.json'

        with path.open('r') as f:

            file_contents: str = f.read()

            models_dict: Dict = json.loads(file_contents)

            try:
                model_data = models_dict[model_key]

                self._access_token = model_data["access_token"]
                self._model_id = model_data["model_id"]
            except ValueError:
                raise ValueError(f"Model {self.model_name} not registered to {self.email}")