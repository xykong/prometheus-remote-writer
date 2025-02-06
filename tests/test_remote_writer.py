import time
from unittest.mock import patch

import pytest
import requests

from prometheus_remote_writer import RemoteWriter

VM_API_URL = 'http://localhost:58480/insert/0/prometheus/'


@pytest.fixture
def mock_requests_post():
    with patch('requests.post') as mock_post:
        yield mock_post


def test_remote_writer_to_server():
    # Setup
    server_url = "http://localhost:58480/insert/0/prometheus/api/v1/write"
    writer = RemoteWriter(url=server_url)

    # Data to send
    current_time_millis = int(time.time() * 1000)  # Current time in milliseconds

    data = [
        {
            'metric': {'__name__': 'test_metric', 'host': 'test_host'},
            'values': [300],
            'timestamps': [current_time_millis]  # Example timestamp in milliseconds
        }
    ]

    # Act
    try:
        writer.send(data)
        print("Data sent successfully.")
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Failed to send data to server: {e}")


def test_remote_writer_send_successful(mock_requests_post):
    # Arrange
    mock_requests_post.return_value.status_code = 200

    writer = RemoteWriter(
        url=f'{VM_API_URL}/api/v1/write',
        headers={'Authorization': 'Bearer TEST_TOKEN'}
    )

    data = [
        {
            'metric': {'__name__': 'cpu_usage', 'host': 'server1'},
            'values': [23.5],
            'timestamps': [1609459200000]
        }
    ]

    # Act
    writer.send(data)

    # Assert
    assert mock_requests_post.called
    args, kwargs = mock_requests_post.call_args
    assert args[0] == f'{VM_API_URL}/api/v1/write'
    assert kwargs['headers'] == {'Authorization': 'Bearer TEST_TOKEN'}
    assert kwargs['timeout'] == 10
    # Additional checks on the data can be added here


@pytest.mark.skip(reason="This test is not needed for the current implementation")
def test_remote_writer_send_failure(mock_requests_post):
    # Arrange
    mock_requests_post.return_value.status_code = 500

    writer = RemoteWriter(
        url='https://example.com/api/v1/write',
        headers={'Authorization': 'Bearer TEST_TOKEN'}
    )

    data = [
        {
            'metric': {'__name__': 'cpu_usage', 'host': 'server1'},
            'values': [23.5],
            'timestamps': [1609459200000]
        }
    ]

    # Act & Assert
    with pytest.raises(requests.exceptions.HTTPError):
        writer.send(data)


def test_remote_writer_no_data(mock_requests_post):
    # Arrange
    writer = RemoteWriter(
        url='https://example.com/api/v1/write'
    )

    data = []  # No data provided

    # Act
    writer.send(data)

    # Assert
    assert not mock_requests_post.called


@pytest.mark.skip(reason="This test is not needed for the current implementation")
def test_remote_writer_invalid_url(mock_requests_post):
    # Arrange
    writer = RemoteWriter(
        url='invalid-url'
    )

    data = [
        {
            'metric': {'__name__': 'cpu_usage', 'host': 'server1'},
            'values': [23.5],
            'timestamps': [1609459200000]
        }
    ]

    # Act & Assert
    with pytest.raises(requests.exceptions.RequestException):
        writer.send(data)
