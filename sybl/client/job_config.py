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
        if "timeout" not in job_config and "prediction_type" not in job_config:
            return False

        timeout: int = job_config["timeout"]
        prediction_type: str = job_config["prediction_type"].lower()

        return timeout < self.max_timeout and prediction_type in self.prediction_types
