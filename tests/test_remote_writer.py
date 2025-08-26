import pytest

from prometheus_remote_writer import RemoteWriter


@pytest.mark.skip(reason="This test is not yet implemented")
def test_timestamp_warning():
    # Prepare test data with a timestamp that seems to be in seconds
    metrics = [
        {
            'metric': {'name': 'cpu_usage'},
            'values': [0.5],
            'timestamps': [1609459200]  # This is in seconds (2021-01-01T00:00:00Z)
        }
    ]

    # Instantiate the RemoteWriter
    writer = RemoteWriter(url="https://example.com")

    # Use pytest.warns to check if a warning is raised
    with pytest.warns(UserWarning, match=r"Timestamp 1609459200 appears to be in seconds"):
        writer._convert_to_timeseries(metrics)
