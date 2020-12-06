from sybl.client import Sybl

sybl = Sybl()

def callback(train, predict):
    return train

sybl.register_callback(callback)
sybl.load_model("test1@test.com", "Test")

sybl.connect()
