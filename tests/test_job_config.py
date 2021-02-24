import pytest

from sybl.client import JobConfig


def test_compare_accept():
    instance = JobConfig(prediction_types=["regression", "classification"], timeout=10)
    test_config = {"prediction_type": "regression", "timeout": 5}

    assert instance.compare(test_config)


def test_compare_reject_type():
    instance = JobConfig(prediction_types=["classification"], timeout=10)
    test_config = {"prediction_type": "regression", "timeout": 5}

    assert not instance.compare(test_config)


def test_compare_reject_timeout():
    instance = JobConfig(prediction_types=["regression"], timeout=10)
    test_config = {"prediction_type": "regression", "timeout": 15}

    assert not instance.compare(test_config)


def test_reject_bad_config():
    instance = JobConfig(prediction_types=["regression"], timeout=10)
    test_config = {"this": "is", "not": "correct"}

    assert not instance.compare(test_config)
