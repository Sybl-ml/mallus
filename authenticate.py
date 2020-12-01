import socket
from typing import Any, Dict, List, Tuple
import json
import os
import base64

from OpenSSL import crypto
from dotenv import load_dotenv
load_dotenv()

DCL_SOCKET: int = 7000

stream = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
stream.connect(("127.0.0.1", DCL_SOCKET))


def sign_challenge(challenge: List[bytes], private_key):

    private_key = crypto.load_privatekey(crypto.FILETYPE_PEM, private_key)
    return crypto.sign(private_key, challenge, "sha256")


def parse_message(message: Dict) -> Tuple[str, Any]:

    # print(message)
    keys: List[str] = list(message)

    if len(keys) > 1:
        raise IndexError

    variant: str = keys[0]
    data: Any = message[variant]

    return (variant, data)


def authenticate_challenge(challenge: Dict, email: str, model_name: str):

    challenge = challenge["challenge"]
    print("Authenticating challenge")
    try:
        private_key = os.environ["PRIVATE_KEY"]
        # print(private_key)
        signed_challenge = sign_challenge(base64.b64decode(challenge), private_key)

        message = {"ChallengeResponse": {"email": email, "model_name": model_name, "response": base64.b64encode(signed_challenge).decode('utf-8') }}
        
        # print(message)
        stream.send(json.dumps(message).encode('utf-8'))
        print("Authenticated")
    except KeyError:
        print("Private Key not set in environemt variable")


def display_access(data: Dict):

    try:
        access_token: str = data["token"]
        model_id: str = data["id"]

        print("ACCESS TOKEN: {} \n MODEL ID: {}".format(access_token, model_id))
    except KeyError:
        print("Malformed data")


def verify(email: str, name: str) -> bool:
    message = {"NewModel": {"email": email, "model_name": name}}
    stream.send(json.dumps(message).encode('utf-8'))

    while True:
        # Read some data
        data = json.loads(stream.recv(1024))

        # print("data: {}".format(data))

        try:
            variant, data = parse_message(data)

            if variant == "Challenge":
                authenticate_challenge(data, email, name)
            elif variant == "AccessToken":
                display_access(data)
                break
            else:
                print("Unknown message Variant")

        except IndexError:
            print("Message cannot be parsed")


def main():

    email: str = input("Enter email: ")
    name: str = input("Enter name of model: ")
    print("Authenticating...")

    verify(email, name)
    return

if __name__ == "__main__":
    main()