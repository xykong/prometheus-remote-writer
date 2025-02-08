import subprocess
import time

import pytest
import requests

from prometheus_remote_writer import RemoteWriter

VM_CONTAINER_NAME = "victoria_metrics"
VM_WRITE_URL = "http://localhost:8428/api/v1/write"


def is_victoria_metrics_running():
    """Check if the VictoriaMetrics container is already running."""
    result = subprocess.run(
        ['docker', 'ps', '-q', '-f', f'name={VM_CONTAINER_NAME}'],
        capture_output=True,
        text=True
    )
    return bool(result.stdout.strip())


@pytest.fixture(scope='module')
def victoria_metrics():
    """Fixture to ensure VictoriaMetrics is running."""
    started_by_test = False

    # Check if VictoriaMetrics is already running
    if not is_victoria_metrics_running():
        # Start VictoriaMetrics using Docker
        subprocess.run(
            [
                'docker', 'run', '--rm', '--name', VM_CONTAINER_NAME, '-d',
                '-p', '8428:8428',
                'victoriametrics/victoria-metrics'
            ],
            check=True
        )
        started_by_test = True

        # visit the healthy URL to ensure the server is up
        for _ in range(10):
            try:
                response = requests.get('http://localhost:8428/health')
                print('query_url:', response.url, 'response:', response.text)
                response.raise_for_status()
                break
            except requests.RequestException:
                time.sleep(1)
        else:
            raise Exception('VictoriaMetrics did not start')

    yield VM_WRITE_URL

    # Teardown: Stop VictoriaMetrics if we started it
    if started_by_test:
        subprocess.run(['docker', 'stop', VM_CONTAINER_NAME], check=True)


def test_remote_writer(victoria_metrics):
    # Instantiate the RemoteWriter with VictoriaMetrics write URL
    writer = RemoteWriter(url=victoria_metrics)

    # Define some sample metrics
    metrics = [
        {
            'metric': {'__name__': 'test_metric', 'label1': 'value1'},
            'values': [1.0, 2.0],
            'timestamps': [int(time.time()) * 1000, (int(time.time()) + 60) * 1000]
        }
    ]

    # Send metrics
    writer.send(metrics)

    # try 10 times to check if the metric was received
    for _ in range(15):
        # Verification: Check if the metric was received
        # Note: VictoriaMetrics has a /api/v1/export endpoint to query data
        query_url = f"http://localhost:8428/api/v1/export?match={metrics[0]['metric']['__name__']}"
        response = requests.get(query_url)
        if 'test_metric' in response.text:
            print('query_url:', response.url, 'response:', response.text)
            break
        time.sleep(1)
    else:
        assert False, 'test_metric not found in response'
