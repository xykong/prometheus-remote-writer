# Prometheus Remote Writer

[![Python package](https://github.com/xykong/prometheus-remote-writer/actions/workflows/python-package.yml/badge.svg)](https://github.com/xykong/prometheus-remote-writer/actions/workflows/python-package.yml)
![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)

## Introduction

`prometheus-remote-writer` is a Python library designed to simplify the process of writing data to a database using
the [Prometheus Remote Write](https://prometheus.io/docs/prometheus/latest/storage/#remote-storage-integrations)
protocol. This library is platform-independent and aims to provide developers with an intuitive way to send time-series
data to Prometheus-compatible storage.

## Key Features

- Easily write data to Prometheus-compatible storage backends.
- Supports custom HTTP headers and authentication methods.
- Provides a simple and easy-to-use API.
- Supports batch data sending to improve transmission efficiency.

## Installation

Before using `prometheus-remote-writer`, ensure that Python 3.8 or higher is installed on your system.

```bash
pip install prometheus-remote-writer
```

## Quick Start

Here's a simple example of how to use `prometheus-remote-writer` in your project:

```python
from prometheus_remote_writer import RemoteWriter

# Create a RemoteWriter instance
writer = RemoteWriter(
    url='https://your-prometheus-server/api/v1/write',
    headers={'Authorization': 'Bearer YOUR_ACCESS_TOKEN'}
)

# Prepare the data to send
data = [
    {
        'metric': {'__name__': 'cpu_usage', 'host': 'server1'},
        'values': [23.5, 24.1, 22.8],
        'timestamps': [1609459200000, 1609459260000, 1609459320000]
    }
]

# Send the data
writer.send(data)
```

## Configuration

`RemoteWriter` supports the following configuration parameters:

- `url` (required): The URL of the Prometheus remote write endpoint.
- `headers` (optional): Custom HTTP headers for authentication or other purposes.
- `timeout` (optional): Request timeout in seconds, default is 10 seconds.
- `auth` (optional): Authentication credentials. Supports:
  - Basic auth: `{'username': 'user', 'password': 'pass'}`
  - Bearer token: `{'bearer_token': 'your-token'}`
- `verify` (optional): SSL certificate verification. Options:
  - `True` (default): Verify SSL certificates
  - `False`: Disable SSL certificate verification (useful for self-signed certificates)
  - `'/path/to/ca-bundle.crt'`: Path to a custom CA certificate bundle
- `proxies` (optional): Proxy configuration as a dictionary, e.g., `{'http': 'http://proxy.com', 'https': 'https://proxy.com'}`
- `retries` (optional): Number of retry attempts for failed requests, default is 3.
- `max_series_per_request` (optional): Maximum number of time series per request, default is 2000.
- `auto_convert_seconds_to_ms` (optional): Automatically convert timestamps from seconds to milliseconds, default is True.

### Advanced Examples

#### Using Self-Signed Certificates

If your Prometheus server uses a self-signed certificate, you can disable SSL verification:

```python
from prometheus_remote_writer import RemoteWriter

writer = RemoteWriter(
    url='https://mimir.example.com/api/v1/push',
    headers={'X-Scope-OrgID': 'test-id'},
    verify=False  # Disable SSL verification
)
```

#### Using Custom CA Certificate

Alternatively, you can provide a path to your custom CA certificate:

```python
writer = RemoteWriter(
    url='https://mimir.example.com/api/v1/push',
    headers={'X-Scope-OrgID': 'test-id'},
    verify='/path/to/ca-bundle.crt'  # Custom CA certificate
)
```

#### Using Authentication

```python
# Bearer token authentication
writer = RemoteWriter(
    url='https://your-prometheus-server/api/v1/write',
    auth={'bearer_token': 'YOUR_ACCESS_TOKEN'}
)

# Basic authentication
writer = RemoteWriter(
    url='https://your-prometheus-server/api/v1/write',
    auth={'username': 'user', 'password': 'pass'}
)
```

#### Using Proxy

```python
writer = RemoteWriter(
    url='https://your-prometheus-server/api/v1/write',
    proxies={'http': 'http://proxy.example.com:8080', 'https': 'https://proxy.example.com:8080'}
)
```

## Unit Testing

This project uses `pytest` for unit testing. To run the tests, execute the following command:

```bash
pytest
```

## Contribution Guide

We welcome contributions from the community! To contribute to `prometheus-remote-writer`, please follow these steps:
Fork the repository.
Create your feature branch (`git checkout -b feature/YourFeature`).
Commit your changes (`git commit -m 'Add some feature'`).
Push to the branch (`git push origin feature/YourFeature`).
Open a pull request.

## FAQ

Why can't I connect to the Prometheus server?

Ensure your network connection is active and the `url` is correct. You may also need to configure firewall rules to
allow traffic.

How do I report a bug?

Please file a bug report on the GitHub issues page with detailed information and steps to reproduce the issue.

## License

This project is licensed under the Apache License 2.0. See the LICENSE file for details.

## Contact

If you have any questions or suggestions, feel free to contact us at xy.kong@gmail.com.

