"""Checks that the Docker sandbox really isolates code (runs only where Docker is ready).

These tests run hostile code through the DockerRunner with the safety check bypassed,
so the container itself has to stop it.
"""

import os
import time

import pytest

from safe_coding_agent.sandbox import SANDBOX_IMAGE, DockerRunner, docker_status
from safe_coding_agent.tasks import load_task

IMAGE = os.environ.get("SCA_TEST_IMAGE", SANDBOX_IMAGE)
ready, why = docker_status(IMAGE)
if os.environ.get("SCA_TEST_DOCKER") and not ready:
    raise RuntimeError(f"SCA_TEST_DOCKER is set but Docker is not ready: {why}")
pytestmark = pytest.mark.skipif(not ready, reason=why)

ESCAPE_TESTS = '''
import os, socket, subprocess, pytest
import solution

def test_normal_code_works():
    assert solution.add(2, 3) == 5

def test_no_network():
    with pytest.raises(OSError):
        socket.create_connection(("1.1.1.1", 80), timeout=2)

def test_root_filesystem_is_read_only():
    with pytest.raises(OSError):
        open("/etc/evil", "w")

def test_not_root():
    assert os.getuid() != 0

def test_no_secrets_in_env():
    assert "MY_SECRET_API_KEY" not in os.environ

def test_process_limit():
    procs, failed = [], False
    try:
        for _ in range(400):
            procs.append(subprocess.Popen(["python", "-c", "import time; time.sleep(5)"]))
    except OSError:
        failed = True
    finally:
        for p in procs:
            p.kill()
    assert failed, f"started {len(procs)} processes"

def test_workspace_writable():
    open("/work/scratch.txt", "w").write("ok")
'''


@pytest.fixture
def escape_task(make_task):
    return load_task(make_task(ESCAPE_TESTS, timeout=20))


def test_container_isolation(escape_task, monkeypatch):
    monkeypatch.setenv("MY_SECRET_API_KEY", "sk-should-not-leak")
    res = DockerRunner(image=IMAGE).run(escape_task, {"solution.py": "def add(a, b):\n    return a + b\n"})
    assert res.runner == "docker"
    assert res.all_passed, [f"{f.name}: {f.message}" for f in res.failures]


def test_container_timeout_and_cleanup(escape_task):
    start = time.time()
    res = DockerRunner(image=IMAGE).run(escape_task, {"solution.py": "while True:\n    pass\n"}, timeout=3)
    assert res.timed_out and time.time() - start < 20
    leftover = os.popen("docker ps -q --filter name=sca-").read().strip()
    assert leftover == ""
