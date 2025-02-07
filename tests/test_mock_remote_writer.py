from unittest.mock import patch

import pytest
import requests

from prometheus_remote_writer import RemoteWriter

# Sample data for testing
metrics = [
    {
        'metric': {'__name__': 'metric_name', 'label1': 'value1'},
        'values': [100, 200],
        'timestamps': [1617181723, 1617181733]
    }
]


# noinspection HttpUrlsUsage,PyUnresolvedReferences
class TestRemoteWriter:

    def test_initialization_defaults(self):
        writer = RemoteWriter(url="http://example.com")
        assert writer.url == "http://example.com"
        assert writer.headers["Content-Type"] == "application/x-protobuf"
        assert writer.headers["Content-Encoding"] == "snappy"
        assert writer.timeout == 10
        assert writer.auth is None
        assert writer.proxies is None

    def test_initialization_with_params(self):
        headers = {"Custom-Header": "HeaderValue"}
        auth = {'username': 'user', 'password': 'pass'}
        proxies = {'http': 'http://proxy.com'}
        writer = RemoteWriter(url="http://example.com", headers=headers, timeout=20, auth=auth, proxies=proxies)
        assert writer.url == "http://example.com"
        assert writer.headers["Custom-Header"] == "HeaderValue"
        assert writer.timeout == 20
        assert isinstance(writer.auth, requests.auth.HTTPBasicAuth)
        assert writer.proxies == {'http': 'http://proxy.com'}

    def test_setup_auth_basic(self):
        auth = {'username': 'user', 'password': 'pass'}
        writer = RemoteWriter(url="http://example.com", auth=auth)
        assert isinstance(writer.auth, requests.auth.HTTPBasicAuth)

    def test_setup_auth_bearer_token(self):
        auth = {'bearer_token': 'token'}
        writer = RemoteWriter(url="http://example.com", auth=auth)
        assert writer.auth is None
        assert writer.headers["Authorization"] == "Bearer token"

    def test_convert_to_timeseries(self):
        timeseries = RemoteWriter._convert_to_timeseries(metrics)
        assert len(timeseries) == 1
        ts = timeseries[0]
        assert len(ts.labels) == 2
        assert ts.labels[0].name == '__name__'
        assert ts.labels[0].value == 'metric_name'
        assert len(ts.samples) == 2
        assert ts.samples[0].value == 100
        assert ts.samples[0].timestamp == 1617181723

    def test_build_message(self):
        timeseries = RemoteWriter._convert_to_timeseries(metrics)
        message = RemoteWriter._build_message(timeseries)
        assert isinstance(message, bytes)

    @patch('requests.post')
    def test_send_message_success(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status.return_value = None

        writer = RemoteWriter(url="http://example.com")
        timeseries = RemoteWriter._convert_to_timeseries(metrics)
        message = RemoteWriter._build_message(timeseries)

        writer._send_message(message)

        mock_post.assert_called_once_with(
            "http://example.com",
            headers=writer.headers,
            data=message,
            timeout=writer.timeout,
            auth=writer.auth,
            proxies=writer.proxies
        )

    @patch('requests.post')
    def test_send_message_failure(self, mock_post):
        mock_post.side_effect = requests.exceptions.RequestException("Error")

        writer = RemoteWriter(url="http://example.com")
        timeseries = RemoteWriter._convert_to_timeseries(metrics)
        message = RemoteWriter._build_message(timeseries)

        with pytest.raises(RuntimeError, match=r"Failed to send data to http://example.com: Error"):
            writer._send_message(message)
