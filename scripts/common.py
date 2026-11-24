"""Shared helpers for the ai-scientist plugin scripts."""
import contextlib
import fcntl
import json
import math
import os
import shutil
import signal
import site
import subprocess
import sys
import tempfile

PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(PLUGIN_ROOT, "templates")


def resolve_template(name_or_path):
    if os.path.isdir(name_or_path):
        return os.path.abspath(name_or_path)
    cand = os.path.join(TEMPLATES_DIR, name_or_path)
    if os.path.isdir(cand):
        return cand
    available = sorted(os.listdir(TEMPLATES_DIR)) if os.path.isdir(TEMPLATES_DIR) else []
    raise SystemExit(f"Template '{name_or_path}' not found. Bundled templates: {available}")


def read_means(run_dir):
    path = os.path.join(run_dir, "final_info.json")
    with open(path) as f:
        info = json.load(f)
    if not isinstance(info, dict) or not info:
        raise ValueError("final_info.json must contain at least one dataset")
    means = {k: v.get("means", v) if isinstance(v, dict) else v for k, v in info.items()}
    for metrics in means.values():
        if not isinstance(metrics, dict) or not metrics or not all(
            (type(value) is int or (type(value) is float and math.isfinite(value)))
            for value in metrics.values()
        ):
            raise ValueError("final_info.json must contain finite numeric metric means")
    return means


@contextlib.contextmanager
def locked(path):
    """Serialize updates using a stable lock file beside the data."""
    with open(path + ".lock", "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def run_cmd(cmd, cwd, timeout, *, capture=True):
    """Run with a dedicated home and a small set of runtime environment variables."""
    allowed = (
        "PATH", "LANG", "LC_ALL", "LC_CTYPE", "TZ", "LD_LIBRARY_PATH",
        "CUDA_VISIBLE_DEVICES", "HIP_VISIBLE_DEVICES", "ROCR_VISIBLE_DEVICES",
        "OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS",
    )
    env = {key: os.environ[key] for key in allowed if key in os.environ}
    if cmd[0] == sys.executable and site.ENABLE_USER_SITE:
        env["PYTHONUSERBASE"] = site.getuserbase()
    output = subprocess.PIPE if capture else subprocess.DEVNULL
    with tempfile.TemporaryDirectory(prefix="ai-scientist-") as private_dir:
        env.update(HOME=private_dir, TMPDIR=private_dir, MPLBACKEND="Agg")
        try:
            with subprocess.Popen(cmd, cwd=cwd, stdout=output, stderr=output, text=True,
                                  encoding="utf-8", errors="replace", env=env,
                                  start_new_session=True) as process:
                try:
                    out, err = process.communicate(timeout=timeout)
                    return process.returncode, out or "", err or ""
                except BaseException:
                    with contextlib.suppress(ProcessLookupError):
                        os.killpg(process.pid, signal.SIGKILL)
                    raise
        except subprocess.TimeoutExpired:
            return 124, "", f"Timed out after {timeout} seconds"


_ignored = shutil.ignore_patterns(
    "__pycache__", "*.pyc", ".git", ".claude", ".env", ".env.*", "*.env", ".ssh", ".aws",
    ".kube", "*.p12", "*.pfx",
    ".gnupg", ".netrc", ".npmrc", ".pypirc", ".git-credentials", ".venv", "*.pem",
    "*.key", "id_rsa*", "id_ed25519*", "credentials.json", "secrets.json",
)


def copytree(src, dst):
    def ignore(directory, names):
        return _ignored(directory, names) | {
            name for name in names
            if os.path.islink(os.path.join(directory, name))
        }

    shutil.copytree(src, dst, ignore=ignore)


def process_failure(code, timeout):
    if code == 124:
        return f"Timed out after {timeout} seconds"
    return f"Process exited with code {code}"
