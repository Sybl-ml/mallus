import pandas as pd
from sklearn.svm import SVC
from sklearn.linear_model import LinearRegression

from sybl.client import Sybl

sybl = Sybl()


def ohe(dataset):
    categorical = dataset.select_dtypes("object")
    if not categorical.empty:
        encoded = pd.get_dummies(categorical[categorical.columns])
        return pd.concat([dataset, encoded], axis=1).drop(categorical, axis=1)
    return dataset


def callback(train, predict, job_config):
    prediction_col = job_config["prediction_column"]
    prediction_type = job_config["prediction_type"]

    print(train, predict, job_config)

    X_train = train.drop(prediction_col, axis=1)
    y_train = train[prediction_col]
    X_test = predict.drop(prediction_col, axis=1)
    X_train = ohe(X_train)
    X_test = ohe(X_test)
    for column in set(X_train.columns).difference(set(X_test.columns)):
        X_test[column] = 0
    for column in set(X_test.columns).difference(set(X_train.columns)):
        X_train[column] = 0
    print(X_train, X_test, y_train)

    if prediction_type == "classification":
        return_frame = SVC().fit(X_train, y_train).predict(X_test)
    else:
        return_frame = LinearRegression().fit(X_train, y_train).predict(X_test)

    return pd.DataFrame({prediction_col: return_frame})


sybl.register_callback(callback)
sybl.load_model("pm@sybl.com", "SVM")

sybl.connect()
