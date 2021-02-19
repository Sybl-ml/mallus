from typing import Dict, List


class JobConfig:
    def __init__(
        self,
        prediction_types: List = ["regression", "classification"],
        timeout: int = 10,
    ):
        self.prediction_types = prediction_types
        self.max_timeout = timeout

    def compare(self, job_config: Dict) -> bool:
        timeout: int = job_config["timeout"]
        prediction_type: str = job_config["prediction_type"].lower()

        return timeout < self.timeout and prediction_type in self.prediction_types