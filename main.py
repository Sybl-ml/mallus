import socket
import json
from typing import List

DCL_SOCKET: int = 7000
API_KEY: List[bytes] = b"hello world"

def heartbeat():

    while True:
        # Read some data
        data = json.loads(stream.recv(1024)[:-1])

        print("data: {}".format(data))

        if data == "Alive":
            stream.send(b"Alive\0")
            
stream = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
stream.connect(("127.0.0.1", DCL_SOCKET))
stream.send(API_KEY)

heartbeat()
