import socket
import json
import os
import base64
import struct

from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

from OpenSSL import crypto
from dotenv import load_dotenv
from xdg import xdg_data_home

load_dotenv()

DCL_SOCKET: int = 7000
DCL_IP: str = "127.0.0.1"


class Authentication:
    def __init__(self, email, model_name):
        self.stream = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.stream.connect(("127.0.0.1", DCL_SOCKET))

        self.email = email
        self.model_name = model_name

        self.access_token = None
        self.model_id = None

    def sign_challenge(self, challenge: List[bytes], private_key: str) -> List[bytes]:
        """
        Signs the challenge provided by the API server with the user's private
        key.

        Args:
            challenge: The bytes of the challenge provided
            private_key: The user's private key

        Returns: Bytes that have been signed with their key

        """

        private_key = crypto.load_privatekey(crypto.FILETYPE_PEM, private_key)
        return crypto.sign(private_key, challenge, "sha256")

    def parse_message(self, message: Dict) -> Tuple[str, Any]:
        """
        Parses a message and ensures it has a single variant.

        Args:
            message: The message to parse

        Returns: The message variant and data content

        Raises:
            IndexError: If the message doesn't have exactly 1 key

        """

        keys: List[str] = list(message)

        if len(keys) > 1:
            raise IndexError

        variant: str = keys[0]
        data: Any = message[variant]

        return (variant, data)

    def authenticate_challenge(self, challenge: Dict):
        """
        Authenticates a challenge message and responds to the requestor.

        Args:
            challenge: The challenge message itself

        Raises:
            KeyError: If the user does not have their private key in their
            environment

        """

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

    def display_access(self, message: Dict):
        """
        Parses an access token from a message and displays them to the user.

        Args:
            message: The message to parse

        Raises:
            KeyError: If the message doesn't contain the "token" and "id" keys

        """

        try:
            self.access_token: str = message["token"]
            self.model_id: str = message["id"]

            print(
                "ACCESS TOKEN: {} \n MODEL ID: {}".format(
                    self.access_token, self.model_id
                )
            )
        except KeyError:
            print("Malformed data")
        finally:
            self.stream.close()

    def verify(self):
        """
        Creates a new model for the user and authenticates it with the
        challenge response method.

        Raises:
            IndexError: If an invalid message is encountered

        """

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
        """
        Saves a user's access token to their `sybl.json` file, specified by the
        `XDG_DATA_HOME` directory. If the directory or file do not exist, they
        will be created prior to writing.
        """

        directory = xdg_data_home()
        path = directory / "sybl.json"

        # Ensure the path exists
        if not Path(directory).is_dir():
            print(f"Creating the following as it does not exist: {directory}")
            Path(directory).mkdir(parents=True)

        # Ensure the file itself exists, even if it's empty
        if not Path(path).is_file():
            print(f"Creating the following file: '{path}'")
            Path(path).touch()

        key_name = f"{self.email}.{self.model_name}"
        new_model = {"model_id": self.model_id, "access_token": self.access_token}

        with path.open("r") as sybl_json:

            contents = sybl_json.read()
            json_contents = json.loads(contents if contents else "{}")

            json_contents[key_name] = new_model

        with path.open("w") as sybl_json:

            sybl_json.write(json.dumps(json_contents))

    def _read_message(self) -> Dict:
        """
        Reads a single message from the stream and loads it as JSON. Messages
        are expected to be length encoded and will be buffered if they are
        larger than 4096 bytes.

        Returns: Serialised JSON read from the stream

        """

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
        """
        Serialises a dictionary into JSON and sends it across the stream.
        Messages will be length prefixed before sending.

        Args:
            message: The message to send
            dump: Whether to use `json.dumps` before handling the message

        """
        data = json.dumps(message) if dump else message
        data = data.encode("utf-8")

        length = (len(data)).to_bytes(4, byteorder="big")
        # print("length: {}".format(length))

        self.stream.send(length + data)


def main():

    email: str = input("Enter email: ")
    name: str = input("Enter name of model: ")
    print("Authenticating...")

    verifier = Authentication(email, name)

    verifier.verify()


if __name__ == "__main__":
    main()
