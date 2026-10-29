"""Running the tests: build a workspace, run pytest in isolation, read the results.

Two runners:

  DockerRunner  (recommended for untrusted models)
      a throw-away container with no network, a read-only file system (except the
      workspace), no Linux capabilities, a non-root user, and memory/CPU/process limits.

  LocalRunner   (fast, for your own trusted experiments)
      a subprocess in a temporary folder with a clean environment (your API keys and
      other environment variables are NOT passed in), its own process group (killed on
      timeout), and CPU-time / file-size limits on Linux and macOS. This is NOT strong
      isolation: code still runs as your user on your machine.

"auto" picks Docker when it is available and the sandbox image is built, else local.
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import tempfile
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

from .tasks import Task

SANDBOX_IMAGE = "safe-coding-agent-sandbox:latest"
REPORT = ".sca-report.xml"


@dataclass
class FailedTest:
    name: str
    message: str


@dataclass
class RunResult:
    passed: int = 0
    total: int = 0
    failures: list[FailedTest] = field(default_factory=list)
    output: str = ""
    timed_out: bool = False
    collection_error: bool = False
    runner: str = "local"

    @property
    def all_passed(self) -> bool:
        return self.total > 0 and self.passed == self.total and not self.timed_out


# ---------------------------------------------------------------- workspace

def build_workspace(task: Task, files: dict[str, str], root: Path) -> Path:
    """Starter files, then the model's files on top, then the task's tests (always last,
    so the model can never replace them)."""
    ws = root / "workspace"
    if task.starter_dir.is_dir():
        shutil.copytree(task.starter_dir, ws, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    ws.mkdir(parents=True, exist_ok=True)
    for rel, text in files.items():
        target = (ws / rel).resolve()
        if ws.resolve() not in target.parents:
            raise ValueError(f"refusing to write outside the workspace: {rel}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    tests = ws / "tests"
    if tests.exists():
        shutil.rmtree(tests)
    shutil.copytree(task.tests_dir, tests, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    # pytest's rootdir/conftest come from the task, never from the model
    for name in ("conftest.py", "pytest.ini", "tox.ini", "setup.cfg", "pyproject.toml"):
        task_file = task.path / name
        if task_file.is_file():
            shutil.copy(task_file, ws / name)
    return ws


def pytest_args(report_path: str) -> list[str]:
    # -vv: full assertion diffs (with -q pytest shortens lists to "['a', ...'c']", hiding the bug)
    return ["-m", "pytest", "tests", "-vv", "--tb=short", "--color=no", "-p", "no:cacheprovider",
            "--continue-on-collection-errors",
            "-o", "console_output_style=classic", "-o", "junit_family=xunit1",
            f"--junitxml={report_path}"]


def _clean_env(workspace: Path) -> dict[str, str]:
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "PYTHONPATH": str(workspace),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": "0",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "HOME": str(workspace),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
    }
    if os.environ.get("SYSTEMROOT"):  # Windows needs this to start Python
        env["SYSTEMROOT"] = os.environ["SYSTEMROOT"]
    return env


# ---------------------------------------------------------------- results

def parse_report(report: Path, output: str, returncode: int, task: Task) -> RunResult:
    res = RunResult(output=output)
    if report.is_file():
        try:
            root = ET.parse(report).getroot()
        except ET.ParseError:
            root = None
        if root is not None:
            for case in root.iter("testcase"):
                name = ".".join(x for x in (case.get("classname"), case.get("name")) if x)
                problem = case.find("failure")
                if problem is None:
                    problem = case.find("error")
                if case.find("skipped") is not None:
                    continue
                msg = "" if problem is None else \
                    ((problem.get("message") or "").strip() or (problem.text or "").strip())
                if problem is not None and msg.startswith("collection failure"):
                    # a whole test file failed to import: not a test, its tests count as failed
                    res.collection_error = True
                    res.failures.append(FailedTest(name, "could not import this test file"))
                    continue
                res.total += 1
                if problem is None:
                    res.passed += 1
                else:
                    res.failures.append(FailedTest(name, msg[:500]))
    if returncode in (2, 3, 4, 5) or "error during collection" in output.lower() \
            or "errors during collection" in output.lower():
        res.collection_error = True
    # tests that never ran (their file failed to import) still count in the total
    res.total = max(res.total, task.count_tests())
    # only call it an import failure when nothing at all could run
    res.collection_error = res.collection_error and res.passed == 0 and \
        not any(f for f in res.failures if f.message != "could not import this test file")
    return res


def summarize_output(output: str, limit: int = 6000) -> str:
    """The useful part of pytest's output: the failure/error sections and the summary."""
    lines = [line for line in output.splitlines() if "generated xml file" not in line]
    start = next((i for i, line in enumerate(lines)
                  if line.startswith("=") and ("FAILURES" in line or "ERRORS" in line)), 0)
    text = "\n".join(lines[start:])
    if len(text) > limit:
        text = text[: limit // 2] + "\n... (output shortened) ...\n" + text[-limit // 2:]
    return text.strip()


# ---------------------------------------------------------------- runners

def _set_limits(cpu_seconds: int):  # pragma: no cover - runs in the child process
    def apply():
        try:
            import resource
            resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds + 5))
            resource.setrlimit(resource.RLIMIT_FSIZE, (100 * 1024 * 1024, 100 * 1024 * 1024))
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        except (ImportError, ValueError, OSError):
            pass
    return apply


class LocalRunner:
    name = "local"

    def run(self, task: Task, files: dict[str, str], timeout: int | None = None) -> RunResult:
        timeout = timeout or task.timeout
        with tempfile.TemporaryDirectory(prefix="sca-") as tmp:
            ws = build_workspace(task, files, Path(tmp))
            report = ws / REPORT
            cmd = [sys.executable, *pytest_args(str(report))]
            kwargs = dict(cwd=ws, env=_clean_env(ws), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, stdin=subprocess.DEVNULL)
            if os.name == "posix":
                kwargs.update(start_new_session=True, preexec_fn=_set_limits(timeout + 5))
            proc = subprocess.Popen(cmd, **kwargs)
            try:
                out, _ = proc.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                _kill_group(proc)
                out, _ = proc.communicate()
                res = RunResult(total=task.count_tests(), output=out or "", timed_out=True,
                                runner=self.name)
                res.output += f"\n\nTIMEOUT: tests did not finish within {timeout}s (infinite loop?)"
                return res
            res = parse_report(report, out or "", proc.returncode, task)
            res.runner = self.name
            return res


def _kill_group(proc: subprocess.Popen) -> None:
    try:
        if os.name == "posix":
            os.killpg(proc.pid, signal.SIGKILL)
        else:
            proc.kill()
    except (ProcessLookupError, PermissionError):
        pass


class DockerRunner:
    name = "docker"

    def __init__(self, image: str = SANDBOX_IMAGE, memory: str = "1g", cpus: str = "1",
                 docker: str = "docker", startup_seconds: int = 5):
        self.image, self.memory, self.cpus, self.docker = image, memory, cpus, docker
        self.startup_seconds = startup_seconds   # extra time allowed for the container to start

    @staticmethod
    def container_user() -> str:
        """Your own user id (so test reports in the workspace stay readable), but never root."""
        if hasattr(os, "getuid") and os.getuid() != 0:
            return f"{os.getuid()}:{os.getgid()}"
        return "65534:65534"   # nobody

    def command(self, ws: Path, container: str) -> list[str]:
        uid = self.container_user()
        return [
            self.docker, "run", "--rm", "--name", container,
            "--network", "none",
            "--read-only", "--tmpfs", "/tmp:rw,nosuid,size=64m",
            "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
            "--pids-limit", "256", "--memory", self.memory, "--memory-swap", self.memory,
            "--cpus", self.cpus,
            "--user", uid,
            "-e", "PYTHONDONTWRITEBYTECODE=1", "-e", "PYTHONPATH=/work", "-e", "HOME=/tmp",
            "-e", "PYTEST_DISABLE_PLUGIN_AUTOLOAD=1", "-e", "PYTHONHASHSEED=0",
            "-v", f"{ws}:/work:rw", "-w", "/work",
            self.image, "python", *pytest_args(f"/work/{REPORT}"),
        ]

    def run(self, task: Task, files: dict[str, str], timeout: int | None = None) -> RunResult:
        timeout = timeout or task.timeout
        with tempfile.TemporaryDirectory(prefix="sca-") as tmp:
            ws = build_workspace(task, files, Path(tmp))
            os.chmod(ws, 0o777)
            container = f"sca-{uuid.uuid4().hex[:12]}"
            try:
                proc = subprocess.run(self.command(ws, container), stdout=subprocess.PIPE,
                                      stderr=subprocess.STDOUT, text=True,
                                      timeout=timeout + self.startup_seconds,
                                      stdin=subprocess.DEVNULL)
            except subprocess.TimeoutExpired as e:
                subprocess.run([self.docker, "kill", container], capture_output=True)
                out = e.stdout if isinstance(e.stdout, str) else (e.stdout or b"").decode(errors="replace")
                res = RunResult(total=task.count_tests(), output=out, timed_out=True, runner=self.name)
                res.output += f"\n\nTIMEOUT: tests did not finish within {timeout}s (infinite loop?)"
                return res
            if proc.returncode == 125 or "Unable to find image" in proc.stdout:
                raise SandboxError(f"Docker could not start the sandbox:\n{proc.stdout.strip()[-800:]}\n"
                                   "Build the sandbox image with:  sca sandbox build")
            res = parse_report(ws / REPORT, proc.stdout, proc.returncode, task)
            res.runner = self.name
            return res


class SandboxError(RuntimeError):
    pass


def docker_status(image: str = SANDBOX_IMAGE, docker: str = "docker") -> tuple[bool, str]:
    """(usable, explanation)"""
    if not shutil.which(docker):
        return False, "Docker is not installed"
    info = subprocess.run([docker, "info"], capture_output=True, text=True)
    if info.returncode != 0:
        return False, "Docker is installed but not running (or you lack permission)"
    img = subprocess.run([docker, "image", "inspect", image], capture_output=True, text=True)
    if img.returncode != 0:
        return False, f"sandbox image '{image}' is not built yet (run: sca sandbox build)"
    return True, f"Docker is ready (image {image})"


def get_runner(kind: str = "auto", image: str = SANDBOX_IMAGE):
    """Returns (runner, note). note explains a fallback to the local runner, else ''."""
    if kind == "local":
        return LocalRunner(), ""
    ok, why = docker_status(image)
    if kind == "docker":
        if not ok:
            raise SandboxError(f"Docker runner not available: {why}")
        return DockerRunner(image), ""
    if ok:
        return DockerRunner(image), ""
    return LocalRunner(), (f"Using the LOCAL runner ({why}). Model code runs on this machine "
                           "without strong isolation. For untrusted models use Docker: sca sandbox build")


def build_image(image: str = SANDBOX_IMAGE, base: str = "python:3.12-slim",
                extra_packages: list[str] | None = None, docker: str = "docker") -> int:
    dockerfile = Path(__file__).parent / "Dockerfile.sandbox"
    args = [docker, "build", "-t", image, "-f", str(dockerfile), "--build-arg", f"BASE={base}"]
    if extra_packages:
        args += ["--build-arg", "EXTRA=" + " ".join(extra_packages)]
    args.append(str(dockerfile.parent))
    return subprocess.call(args)
