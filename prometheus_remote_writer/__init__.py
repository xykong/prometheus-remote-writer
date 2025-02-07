from typing import Dict, List, Optional

import requests
import snappy  # noqa

from prometheus_remote_writer.proto.remote_pb2 import WriteRequest  # noqa
from prometheus_remote_writer.proto.types_pb2 import TimeSeries, Label, Sample  # noqa


# noinspection PyUnresolvedReferences, HttpUrlsUsage
class RemoteWriter:
    def __init__(
            self,
            url: str,
            headers: Optional[Dict[str, str]] = None,
            timeout: int = 10,
            auth: Optional[Dict[str, str]] = None,
            proxies: Optional[Dict[str, str]] = None
    ):
        """
        :param url: The URL to send data to.
        :param headers: HTTP headers to include in the request.
        :param timeout: Request timeout in seconds.
        :param auth: Authentication information (e.g., {'username': 'user', 'password':
        'pass'} or {'bearer_token': 'token'}).
        :param proxies: Proxy settings
        (e.g., {'http': 'http://proxy.example.com:8080',
        'https': 'https://proxy.example.com:8080'}).
        """

        self.url = url
        self.headers = headers or {"Content-Type": "application/x-protobuf", "Content-Encoding": "snappy"}
        self.timeout = timeout
        self.auth = self._setup_auth(auth)
        self.proxies = proxies

    def _setup_auth(self, auth: Optional[Dict[str, str]]) -> Optional[requests.auth.AuthBase]:

        if not auth:
            return None

        if 'username' in auth and 'password' in auth:
            return requests.auth.HTTPBasicAuth(auth['username'], auth['password'])

        if 'bearer_token' in auth:
            self.headers["Authorization"] = f"Bearer {auth['bearer_token']}"

        return None

    def send(self, metrics: List[Dict]):
        """
        Send data to the Prometheus remote write endpoint.

        :param metrics: A list of dictionaries containing metrics data.
        """

        if not metrics:
            return

        timeseries = self._convert_to_timeseries(metrics)
        message = self._build_message(timeseries)

        self._send_message(message)

    @staticmethod
    def _convert_to_timeseries(metrics: List[Dict]) -> List[TimeSeries]:
        timeseries = []

        for item in metrics:
            ts = TimeSeries()
            for key, value in item['metric'].items():
                ts.labels.append(Label(name=key, value=value))
            for value, timestamp in zip(item['values'], item['timestamps']):
                ts.samples.append(Sample(value=value, timestamp=timestamp))
            timeseries.append(ts)

        return timeseries

    @staticmethod
    def _build_message(timeseries: List[TimeSeries]) -> bytes:

        write_request = WriteRequest()
        write_request.timeseries.extend(timeseries)
        serialized_message = write_request.SerializeToString()
        compressed_message = snappy.compress(serialized_message)

        return compressed_message

    def _send_message(self, message: bytes):
        try:
            response = requests.post(
                self.url,
                headers=self.headers,
                data=message,
                timeout=self.timeout,
                auth=self.auth,
                proxies=self.proxies
            )

            response.raise_for_status()

        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Failed to send data to {self.url}: {e}")
