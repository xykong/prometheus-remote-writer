from typing import Dict, List

import requests
import snappy  # noqa

from .remote_pb2 import WriteRequest  # noqa
from .types_pb2 import TimeSeries, Label, Sample  # noqa


class RemoteWriter:
    def __init__(self, url: str, headers: Dict[str, str] = None, timeout: int = 10):
        self.url = url
        self.headers = headers or {"Content-Type": "application/x-protobuf", "Content-Encoding": "snappy"}
        self.timeout = timeout

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
                timeout=self.timeout
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Failed to send data to {self.url}: {e}")
