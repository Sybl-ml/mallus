"""
Tests for the job config module
"""

from typing import Dict

from sybl.client import JobConfig

# pylint: disable=missing-function-docstring


def test_compare_accept():
    instance = JobConfig(prediction_types=["regression", "classification"], timeout=10)
    test_config = {
        "prediction_type": "regression",
        "message_creation_timestamp": 0,
        "prediction_cutoff_timestamp": 600,
    }

    assert instance.compare(test_config)


def test_compare_reject_type():
    instance = JobConfig(prediction_types=["classification"], timeout=10)
    test_config = {
        "prediction_type": "regression",
        "message_creation_timestamp": 0,
        "prediction_cutoff_timestamp": 300,
    }

    assert not instance.compare(test_config)


def test_compare_reject_timeout():
    instance = JobConfig(prediction_types=["regression"], timeout=10)
    test_config = {
        "prediction_type": "regression",
        "message_creation_timestamp": 0,
        "prediction_cutoff_timestamp": 900,
    }

    assert not instance.compare(test_config)


def test_reject_bad_config():
    instance = JobConfig(prediction_types=["regression"], timeout=10)
    test_config = {"this": "is", "not": "correct"}

    assert not instance.compare(test_config)


def test_user_defined_custom_comparison_function():
    instance = JobConfig(prediction_types=["classification"], timeout=5)
    test_config = {
        "message_creation_timestamp": 0,
        "prediction_cutoff_timestamp": 1,
        "prediction_type": "regression",
    }

    # Just ignore what we said before and accept anyway
    def comparison_function(job_config: Dict):
        return True

    instance.set_comparison_function(comparison_function)
    assert instance.compare(test_config)


def test_user_defined_custom_comparison_function_with_config_usage():
    instance = JobConfig(prediction_types=["classification"], timeout=5)
    test_config = {
        "message_creation_timestamp": 0,
        "prediction_cutoff_timestamp": 600,
        "prediction_type": "regression",
    }

    # Use a different timeout for classification compared to regression
    def comparison_function(job_config: Dict):
        prediction_type = job_config["prediction_type"]
        message_creation_timestamp = job_config["message_creation_timestamp"]
        prediction_cutoff_timestamp = job_config["prediction_cutoff_timestamp"]

        time_difference = prediction_cutoff_timestamp - message_creation_timestamp

        # Use 15 minutes for classification, 5 minutes for regression
        if prediction_type == "classification":
            return 15 * 60 <= time_difference
        else:
            return 5 * 60 <= time_difference

    # Set the comparison function itself
    instance.set_comparison_function(comparison_function)

    # This should pass, as we are doing regression with a 10 minute value
    assert instance.compare(test_config)

    # This should fail, as we are now doing classification with the same
    test_config["prediction_type"] = "classification"
    assert not instance.compare(test_config)

    # This should pass, as we now have 15 minutes for classification
    test_config["prediction_cutoff_timestamp"] *= 1.5
    assert instance.compare(test_config)
