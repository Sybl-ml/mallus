""" JobConfig Module """

from typing import Dict, List


class JobConfig:
    """
    JobConfig Object which is created by the client
    Which can be compared to a dictionary to return if the specification
    fits the provided config.
    """

    def __init__(
        self,
        prediction_types: List = ["regression", "classification"],
        timeout: int = 10,
    ):
        self.prediction_types = prediction_types
        self.max_timeout = timeout

    def compare(self, job_config: Dict) -> bool:
        """
        Compares a jobconfig dictionary from the DCL with the instance

            Parameters:
                job_config (Dict): Dictionary containing timeout and prediction_type
                    from the dcl for a specific job

            Returns:
                bool: True if job is accepted, False otherwise. False if the job_config is malformed
        """
        if "timeout" not in job_config and "prediction_type" not in job_config:
            return False

        timeout: int = job_config["timeout"]
        prediction_type: str = job_config["prediction_type"].lower()

        return timeout < self.max_timeout and prediction_type in self.prediction_types
