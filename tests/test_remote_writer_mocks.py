from typing import (
    Sequence,
)
from unittest.mock import patch, MagicMock

import pytest
import requests
from requests import Response

from prometheus_remote_writer import RemoteWriter, MetricItem

# Sample data for testing
metrics: Sequence[MetricItem] = [
    {
        'metric': {'__name__': 'metric_name', 'label1': 'value1'},
        'values': [100, 200],
        'timestamps': [1617181723000, 1617181733000]
    }
]


# noinspection HttpUrlsUsage
class TestRemoteWriter:

    def test_initialization_defaults(self):
        writer = RemoteWriter(url="http://example.com")
        assert writer.url == "http://example.com"
        assert writer.headers["Content-Type"] == "application/x-protobuf"
        assert writer.headers["Content-Encoding"] == "snappy"
        assert writer.timeout == 10
        # assert writer.auth is None
        assert writer.proxies is None

    def test_initialization_with_params(self):
        headers = {"Custom-Header": "HeaderValue"}
        auth = {'username': 'user', 'password': 'pass'}
        proxies = {'http': 'http://proxy.com'}
        writer = RemoteWriter(url="http://example.com", headers=headers, timeout=20, auth=auth, proxies=proxies)
        assert writer.url == "http://example.com"
        assert writer.headers["Custom-Header"] == "HeaderValue"
        assert writer.timeout == 20
        # assert isinstance(writer.auth, requests.auth.HTTPBasicAuth)
        assert writer.proxies == {'http': 'http://proxy.com'}

    def test_setup_auth_basic(self):
        auth = {'username': 'user', 'password': 'pass'}
        writer = RemoteWriter(url="http://example.com", auth=auth)
        # noinspection PyUnresolvedReferences
        assert isinstance(writer._auth_object, requests.auth.HTTPBasicAuth)

    def test_setup_auth_bearer_token(self):
        auth = {'bearer_token': 'token'}
        writer = RemoteWriter(url="http://example.com", auth=auth)
        # assert writer.auth is None
        assert writer.headers["Authorization"] == "Bearer token"

    def test_convert_to_timeseries(self):
        writer = RemoteWriter(url="http://example.com")
        timeseries, total_samples = writer._convert_to_timeseries(metrics)
        assert len(timeseries) == 1
        ts = timeseries[0]
        assert len(ts.labels) == 2
        assert ts.labels[0].name == '__name__'
        assert ts.labels[0].value == 'metric_name'
        assert len(ts.samples) == 2
        assert ts.samples[0].value == 100
        assert ts.samples[0].timestamp == 1617181723000

    def test_build_message(self):
        writer = RemoteWriter(url="http://example.com")
        timeseries, total_samples = writer._convert_to_timeseries(metrics)
        message = writer._build_message(timeseries)
        assert isinstance(message, bytes)

    @patch.object(requests.Session, "post")
    def test_send_message_success(self, mock_post):
        # 准备返回的响应
        mock_resp = MagicMock(spec=Response)
        mock_resp.status_code = 200
        mock_resp.raise_for_status.return_value = None
        mock_post.return_value = mock_resp

        writer = RemoteWriter(url="http://example.com")

        # 构造一个最小可用的 timeseries/message（假设已有 metrics 变量）
        timeseries, _ = writer._convert_to_timeseries(metrics)
        message = writer._build_message(timeseries)

        resp = writer._send_message(message)

        mock_post.assert_called_once_with(
            "http://example.com",
            headers=writer.headers,
            data=message,
            timeout=writer.timeout,
            auth=writer._auth_object,  # 新实现通过 self._auth_object 传递
            proxies=writer.proxies,
            verify=writer.verify,  # 新增的参数需要断言
        )
        assert resp is mock_resp

    @patch.object(requests.Session, "post")
    def test_send_message_failure(self, mock_post):
        # 让 Session.post 抛出网络层异常
        mock_post.side_effect = requests.exceptions.RequestException("Error")

        writer = RemoteWriter(url="http://example.com")

        timeseries, _ = writer._convert_to_timeseries(metrics)
        message = writer._build_message(timeseries)

        # 匹配新的错误信息格式
        with pytest.raises(
                RuntimeError,
                match=r"Network error posting to http://example\.com: RequestException: Error",
        ):
            writer._send_message(message)

        # 验证入参（包含 auth 和 verify）
        mock_post.assert_called_once_with(
            "http://example.com",
            headers=writer.headers,
            data=message,
            timeout=writer.timeout,
            auth=writer._auth_object,  # 新实现使用 _auth_object
            proxies=writer.proxies,
            verify=writer.verify,
        )
