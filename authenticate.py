from os import access
import socket
from typing import Any, Dict, List, Tuple
import json
import os
import base64

from OpenSSL import crypto


DCL_SOCKET: int = 7000

stream = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
stream.connect(("127.0.0.1", DCL_SOCKET))


def sign_challenge(challenge: List[bytes], private_key):

    private_key = crypto.load_privatekey(private_key)
    return crypto.sign(private_key, challenge)


def parse_message(message: Dict) -> Tuple[str, Any]:

    keys: List[str] = list(message)

    if len(keys) > 1:
        raise Exception

    variant: str = keys[0]
    data: Any = message[type]

    return (variant, data)


def authenticate_challenge(challenge: str):

    try:
        private_key = os.environ["PRIVATE_KEY"]
        signed_challenge = sign_challenge(base64.b64decode(challenge), private_key)

        message: str = "{{ signed_challenge: {} }}".format(signed_challenge)

        stream.send(message)
    except KeyError:
        print("Private Key not set in environemt variable")


def display_access(data: Dict):

    try:
        access_token: str = data["access_token"]
        model_id: str = data["model_id"]

        print("ACCESS TOKEN: {} \n MODEL ID: {}".format(access_token, model_id))
    except KeyError:
        print("Malformed data")


def verify(email: str, name: str) -> bool:
    message = {"email": email, "model_name": name}
    stream.send(message)

    while True:
        # Read some data
        data = json.loads(stream.recv(1024)[:-1])

        print("data: {}".format(data))

        try:
            variant, data = parse_message(data)

            if variant == "Alive":
                stream.send(b"Alive\0")
            elif variant == "Challenge":
                authenticate_challenge(data)
            elif variant == "Identifier":
                display_access(data)
            else:
                print("Unknown message Variant")

        except Exception:
            print("Message cannot be parsed")


def main():

    email: str = input("Enter email: ")
    name: str = input("Enter name of model: ")
    print("Authenticating...")

    verify(email, name)