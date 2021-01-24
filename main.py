from sybl.client import Sybl
import pandas as pd

sybl = Sybl()


def callback(train, predict):
    return pd.DataFrame(predict[predict.columns[-1]])


sybl.register_callback(callback)
sybl.load_model("test1@test.com", "Test")

sybl.connect()
