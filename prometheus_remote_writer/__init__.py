import logging
from dataclasses import dataclass
from typing import (
    Dict,
    List,
    Optional,
    Mapping,
    Sequence,
    Tuple,
    Union,
    Iterable,
    Iterator,
    cast,
)

import requests
import snappy
from requests import Response, Session
from requests.adapters import HTTPAdapter
from requests.auth import AuthBase, HTTPBasicAuth
from urllib3.util.retry import Retry

from prometheus_remote_writer.proto.remote_pb2 import WriteRequest  # noqa
from prometheus_remote_writer.proto.types_pb2 import TimeSeries, Label, Sample  # noqa

try:
    # Py3.8+ preferred
    from typing import TypedDict
except ImportError:
    # For older environments
    from typing_extensions import TypedDict  # type: ignore

# ---------------------------
# Types and constants
# ---------------------------

MS_THRESHOLD = 10_000_000_000  # 1e10: below this likely seconds, above equals milliseconds


class MetricItem(TypedDict):
    metric: Dict[str, str]
    values: List[Union[int, float]]
    timestamps: List[Union[int, float]]


@dataclass
class SendResult:
    requests_sent: int
    series_sent: int
    samples_sent: int
    last_response: Optional[Response]


# ---------------------------
# Remote Writer
# ---------------------------

class RemoteWriter:
    """
    A Prometheus Remote Write client with robust batching, retries, validation, and logging.
    """

    DEFAULT_HEADERS = {
        "Content-Type": "application/x-protobuf",
        "Content-Encoding": "snappy",
        "X-Prometheus-Remote-Write-Version": "0.1.0",
    }

    def __init__(
            self,
            url: str,
            headers: Optional[Mapping[str, str]] = None,
            timeout: Union[float, Tuple[float, float]] = 10.0,
            auth: Optional[Dict[str, str]] = None,
            proxies: Optional[Mapping[str, str]] = None,
            session: Optional[Session] = None,
            retries: int = 3,
            backoff_factor: float = 0.5,
            status_forcelist: Sequence[int] = (429, 500, 502, 503, 504),
            pool_connections: int = 10,
            pool_maxsize: int = 50,
            max_series_per_request: Optional[int] = 2000,
            max_bytes_per_request: Optional[int] = None,
            sort_labels: bool = False,
            auto_convert_seconds_to_ms: bool = True,
            strict_timestamps: bool = False,
            logger: Optional[logging.Logger] = None,
            verify: Optional[Union[bool, str]] = None,
            user_agent: str = "animal-remote-writer/1.0",
    ):
        self.url = url
        self.timeout = timeout
        self.proxies = dict(proxies) if proxies else None
        self.verify = verify
        self.sort_labels = sort_labels
        self.auto_convert_seconds_to_ms = auto_convert_seconds_to_ms
        self.strict_timestamps = strict_timestamps
        self.max_series_per_request = max_series_per_request
        self.max_bytes_per_request = max_bytes_per_request
        self.logger = logger or logging.getLogger(__name__)

        # Build headers safely (copy + merge)
        merged_headers = dict(self.DEFAULT_HEADERS)
        if headers:
            merged_headers.update(headers)
        # Ensure User-Agent present/override
        merged_headers.setdefault("User-Agent", user_agent)
        self.headers = merged_headers

        # Auth setup
        self._auth_object: Optional[AuthBase] = None
        if auth:
            if "username" in auth and "password" in auth:
                self._auth_object = HTTPBasicAuth(auth["username"], auth["password"])
            elif "bearer_token" in auth:
                self.headers["Authorization"] = f"Bearer {auth['bearer_token']}"
            else:
                raise ValueError("auth must include either ('username','password') or 'bearer_token'")

        # Session & retries
        self._external_session = session is not None
        self._session: Session = session or self._build_session(
            retries=retries,
            backoff_factor=backoff_factor,
            status_forcelist=tuple(status_forcelist),
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize,
        )

    # ---------------------------
    # Public API
    # ---------------------------

    def send(self, metrics: Sequence[MetricItem]) -> SendResult:
        """
        Convert and send metrics via Prometheus Remote Write.

        Returns SendResult with counts and last response.
        Raises RuntimeError on network/HTTP errors; ValueError on invalid input.
        """
        if not metrics:
            return SendResult(requests_sent=0, series_sent=0, samples_sent=0, last_response=None)

        timeseries, total_samples = self._convert_to_timeseries(metrics)

        requests_sent = 0
        series_sent = 0
        last_response: Optional[Response] = None

        for batch in self._iter_batches(timeseries):
            message = self._build_message(batch)
            last_response = self._send_message(message)
            requests_sent += 1
            series_sent += len(batch)

        return SendResult(
            requests_sent=requests_sent,
            series_sent=series_sent,
            samples_sent=total_samples,
            last_response=last_response,
        )

    def close(self):
        """Close the underlying session if it was created internally."""
        if not self._external_session and self._session:
            self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def __repr__(self) -> str:
        # Avoid leaking secrets
        cls = self.__class__.__name__
        masked_headers = {k: ("<redacted>" if k.lower() == "authorization" else v) for k, v in self.headers.items()}
        return f"{cls}(url={self.url!r}, headers={masked_headers!r}, timeout={self.timeout!r})"

    # ---------------------------
    # Internal helpers
    # ---------------------------

    @staticmethod
    def _build_session(
            retries: int,
            backoff_factor: float,
            status_forcelist: Tuple[int, ...],
            pool_connections: int,
            pool_maxsize: int,
    ) -> Session:
        s = requests.Session()

        # Retry config: include POST as allowed method
        retry = Retry(
            total=retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
            allowed_methods=frozenset(["POST", "GET", "PUT", "DELETE", "HEAD", "OPTIONS", "PATCH"]),
            raise_on_status=False,
        )

        adapter = HTTPAdapter(max_retries=retry, pool_connections=pool_connections, pool_maxsize=pool_maxsize)
        # noinspection HttpUrlsUsage
        s.mount("http://", adapter)
        s.mount("https://", adapter)

        return s

    def _convert_to_timeseries(self, metrics: Sequence[MetricItem]) -> Tuple[List[TimeSeries], int]:
        timeseries: List[TimeSeries] = []
        total_samples = 0

        for idx, item in enumerate(metrics):
            if not isinstance(item, dict) or "metric" not in item or "values" not in item or "timestamps" not in item:
                raise ValueError(f"Metric item at index {idx} missing required keys: 'metric', 'values', 'timestamps'")

            labels_map = cast(Dict[str, object], item["metric"])
            values = cast(Sequence[Union[int, float]], item["values"])
            timestamps = cast(Sequence[Union[int, float]], item["timestamps"])

            if len(values) != len(timestamps):
                raise ValueError(
                    f"Metric item at index {idx} has length mismatch: "
                    f"values={len(values)} vs timestamps={len(timestamps)}"
                )

            ts = TimeSeries()

            # Labels: ensure str types, optionally sort
            labels_items: Iterable[Tuple[str, str]] = ((str(k), str(v)) for k, v in labels_map.items())
            if self.sort_labels:
                labels_items = sorted(labels_items, key=lambda kv: kv[0])

            for name, val in labels_items:
                ts.labels.append(Label(name=name, value=val))

            # Normalize timestamps to ms
            norm_timestamps = self._normalize_timestamps(timestamps, idx)

            # Samples
            for v, t in zip(values, norm_timestamps):
                ts.samples.append(Sample(value=float(v), timestamp=int(t)))

            total_samples += len(values)
            timeseries.append(ts)

        return timeseries, total_samples

    def _normalize_timestamps(
            self,
            timestamps: Sequence[Union[int, float]],
            metric_index: int,
    ) -> List[int]:
        if not timestamps:
            return []

        first = timestamps[0]
        first_int = int(first)
        is_seconds = first_int < MS_THRESHOLD
        result: List[int] = []

        if is_seconds:
            if self.auto_convert_seconds_to_ms:
                # Convert all to ms with rounding for float seconds
                for t in timestamps:
                    if isinstance(t, float):
                        result.append(int(round(t * 1000)))
                    else:
                        result.append(int(t) * 1000)
                if self.logger:
                    self.logger.warning(
                        "Metric[%d]: timestamps appear to be in seconds; auto-converted to milliseconds.",
                        metric_index,
                    )
                return result
            elif self.strict_timestamps:
                raise ValueError(
                    f"Metric[{metric_index}]: timestamps appear to be in seconds (< {MS_THRESHOLD}); "
                    f"strict_timestamps=True, refusing to send."
                )
            else:
                if self.logger:
                    self.logger.warning(
                        "Metric[%d]: timestamps appear to be in seconds; sending as-is (may be incorrect).",
                        metric_index,
                    )

        # Already in ms (or intentionally sending seconds)
        for t in timestamps:
            if isinstance(t, float):
                result.append(int(round(t)))
            else:
                result.append(int(t))
        return result

    @staticmethod
    def _build_message(timeseries: List[TimeSeries]) -> bytes:
        write_request = WriteRequest()
        write_request.timeseries.extend(timeseries)
        serialized = write_request.SerializeToString()
        compressed = snappy.compress(serialized)
        return compressed

    def _iter_batches(self, timeseries: List[TimeSeries]) -> Iterator[List[TimeSeries]]:
        """
        Yield batches of TimeSeries based on max_series_per_request and/or max_bytes_per_request.
        If only the series limit is set: simple slicing.
        If the size limit is set: assemble by testing compressed size progressively.
        """
        n = len(timeseries)

        # Fast path: only series cap
        if self.max_bytes_per_request is None and self.max_series_per_request:
            step = max(1, int(self.max_series_per_request))
            for i in range(0, n, step):
                yield timeseries[i: i + step]
        else:
            # Size-aware batching (may serialize multiple times per batch for accuracy)
            max_bytes = self.max_bytes_per_request
            series_cap = self.max_series_per_request or n

            start = 0
            while start < n:
                batch: List[TimeSeries] = []
                # Grow the batch while staying under limits
                for i in range(start, min(n, start + series_cap)):
                    candidate = timeseries[i]
                    if not batch:
                        # First element: always accept; we'll check if it alone exceeds size
                        batch.append(candidate)
                        if max_bytes is not None:
                            size = len(self._build_message(batch))
                            if size > max_bytes:
                                if self.logger:
                                    self.logger.warning(
                                        "Single-series batch exceeds max_bytes_per_request (%d > %d). Sending anyway.",
                                        size,
                                        max_bytes,
                                    )
                                # Keep as is; won't add more
                                break
                    else:
                        if max_bytes is None:
                            batch.append(candidate)
                        else:
                            # Try adding and test size
                            batch.append(candidate)
                            size = len(self._build_message(batch))
                            if size > max_bytes:
                                # Revert last and stop growing this batch
                                batch.pop()
                                break
                if not batch:
                    # Fallback to avoid infinite loop (shouldn't happen)
                    batch = [timeseries[start]]
                    start += 1
                else:
                    start += len(batch)
                yield batch

    def _send_message(self, message: bytes) -> Response:
        try:
            resp = self._session.post(
                self.url,
                headers=self.headers,
                data=message,
                timeout=self.timeout,
                auth=self._auth_object,
                proxies=self.proxies,
                verify=self.verify,
            )
            resp.raise_for_status()
            return resp
        except requests.HTTPError as e:
            resp = e.response
            status = resp.status_code if resp is not None else None
            body_snippet = ""
            if resp is not None:
                content = resp.content or b""
                if content:
                    # Best-effort decode without raising
                    encoding = resp.encoding or "utf-8"
                    body_snippet = content.decode(encoding, errors="replace")[:1024]
            raise RuntimeError(
                f"HTTP error posting to {self.url}: status={status}, body={body_snippet}"
            ) from e
        except requests.RequestException as e:
            raise RuntimeError(f"Network error posting to {self.url}: {e.__class__.__name__}: {e}") from e

# ---------------------------
# Usage example (commented)
# ---------------------------
# logger = logging.getLogger("remote_writer")
# logging.basicConfig(level=logging.INFO)
#
# writer = RemoteWriter(
#     url="https://prom-remote-write.example/api/v1/write",
#     auth={"bearer_token": "your-token"},
#     max_series_per_request=2000,
#     max_bytes_per_request=None,  # or set to e.g. 4_000_000 to cap compressed size ~4MB
#     sort_labels=True,
#     auto_convert_seconds_to_ms=True,
#     strict_timestamps=False,
#     logger=logger,
# )
#
# metrics: List[MetricItem] = [
#     {
#         "metric": {"__name__": "http_requests_total", "method": "GET", "status": "200"},
#         "values": [1.0, 2.0, 3.0],
#         "timestamps": [1724300000, 1724300001, 1724300002],  # seconds -> will auto convert to ms
#     }
# ]
#
# res = writer.send(metrics)
# print(res)
# writer.close()
