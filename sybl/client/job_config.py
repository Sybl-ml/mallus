""" JobConfig Module """

from typing import Callable, Dict, Optional, List

ComparisonFunction = Callable[[Dict], bool]


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
        self.comparison_function: Optional[ComparisonFunction] = None

    def set_comparison_function(self, comparison_function: ComparisonFunction):
        """
        Sets the comparison function to use with incoming job configurations.

        This allows more fine-grained control over the process. By default, we
        just check that the user's timeout is long enough and that they are
        willing to perform the job type. By providing a comparison function,
        they will be able to check other more complex aspects.

        Args:
            comparison_function: The function to use for comparing
        """
        self.comparison_function = comparison_function

    def compare(self, job_config: Dict) -> bool:
        """
        Compares a jobconfig dictionary from the DCL with the instance

            Parameters:
                job_config (Dict): Dictionary containing timeout and prediction_type
                    from the dcl for a specific job

            Returns:
                bool: True if job is accepted, False otherwise. False if the job_config is malformed
        """
        # Ensure the config is not malformed
        expected_fields = [
            "message_creation_timestamp",
            "prediction_cutoff_timestamp",
            "prediction_type",
        ]

        if not all(field in job_config for field in expected_fields):
            return False

        # If the user has defined a comparison function, use that
        if self.comparison_function is not None:
            return self.comparison_function(job_config)

        # Otherwise, do some basic checks for them
        message_creation_timestamp: int = job_config["message_creation_timestamp"]
        prediction_cutoff_timestamp: int = job_config["prediction_cutoff_timestamp"]
        prediction_type: str = job_config["prediction_type"].lower()

        # Calculate the time limit for the job
        time_difference: int = prediction_cutoff_timestamp - message_creation_timestamp

        # Multiply our timeout by 60 to convert from minutes to seconds
        return (
            time_difference <= self.max_timeout * 60
            and prediction_type in self.prediction_types
        )
