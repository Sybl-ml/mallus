from enum import Enum
import socket
from typing import Any, Dict, List, Tuple, Union
import json
import os
import base64
import struct

from OpenSSL import crypto
from dotenv import load_dotenv
from xdg import xdg_data_home

load_dotenv()

DCL_SOCKET: int = 7000
DCL_IP: str = "127.0.0.1"


class Authenication:
    def __init__(self, email, model_name):
        self.stream = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.stream.connect(("127.0.0.1", DCL_SOCKET))

        self.email = email
        self.model_name = model_name

        self.access_token = None
        self.model_id = None

    def sign_challenge(self, challenge: List[bytes], private_key):

        private_key = crypto.load_privatekey(crypto.FILETYPE_PEM, private_key)
        return crypto.sign(private_key, challenge, "sha256")

    def parse_message(self, message: Dict) -> Tuple[str, Any]:

        # print(message)
        keys: List[str] = list(message)

        if len(keys) > 1:
            raise IndexError

        variant: str = keys[0]
        data: Any = message[variant]

        return (variant, data)

    def authenticate_challenge(self, challenge: Dict):

        challenge = challenge["challenge"]
        print("Authenticating challenge")
        try:
            private_key = os.environ["PRIVATE_KEY"]
            signed_challenge = self.sign_challenge(
                base64.b64decode(challenge), private_key
            )

            message = {
                "ChallengeResponse": {
                    "email": self.email,
                    "model_name": self.model_name,
                    "response": base64.b64encode(signed_challenge).decode("utf-8"),
                }
            }

            # print(message)
            self._send_message(message)
            print("Authenticated")
        except KeyError:
            print("Private Key not set in environemt variable")

    def display_access(self, data: Dict):

        try:
            self.access_token: str = data["token"]
            self.model_id: str = data["id"]

            print(
                "ACCESS TOKEN: {} \n MODEL ID: {}".format(
                    self.access_token, self.model_id
                )
            )
        except KeyError:
            print("Malformed data")
        finally:
            self.stream.close()

    def verify(self) -> bool:
        message = {"NewModel": {"email": self.email, "model_name": self.model_name}}
        self._send_message(message)

        while True:
            # Read some data
            data = self._read_message() 
            print("data: {}".format(data))

            try:
                variant, data = self.parse_message(data)

                if variant == "Challenge":
                    self.authenticate_challenge(data)
                elif variant == "AccessToken":
                    self.display_access(data)
                    self.save_access_tokens()
                    break
                else:
                    print("Unknown message Variant")

            except IndexError:
                print("Message cannot be parsed")
    

    def save_access_tokens(self):

        path = xdg_data_home() / 'sybl.json'

        key_name = f"{self.email}.{self.model_name}"
        new_model = {"model_id": self.model_id, "access_token": self.access_token}
        
        with path.open('r') as f:

            contents = f.read()
            json_contents = json.loads(contents if contents else "{}")

            json_contents[key_name] = new_model
        
        with path.open('w') as f:

            f.write(json.dumps(json_contents))

    def _read_message(self) -> Dict:
        size_bytes = self.stream.recv(4)
        # print("size_bytes: {}".format(size_bytes))

        size = struct.unpack(">I", size_bytes)[0]

        if size > 4096:
            remaining_size = size
            buffer = []

            while remaining_size > 0:
                chunk = self.stream.recv(4096)
                buffer.extend(chunk)

                remaining_size -= 4096

            return json.loads(buffer)

        return json.loads(self.stream.recv(size))

    def _send_message(self, message: Union[Dict, str], dump=True):
        data = json.dumps(message) if dump else message
        data = data.encode("utf-8")

        length = (len(data)).to_bytes(4, byteorder="big")
        # print("length: {}".format(length))

        self.stream.send(length + data)
                
def main():

    email: str = input("Enter email: ")
    name: str = input("Enter name of model: ")
    print("Authenticating...")

    verifier = Authenication(email, name)

    verifier.verify()


if __name__ == "__main__":
    main()
