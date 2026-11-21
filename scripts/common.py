"""Shared helpers for the ai-scientist plugin scripts."""
import json
import os
import shutil
import subprocess

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
    return {k: (v["means"] if isinstance(v, dict) and "means" in v else v) for k, v in info.items()}


def run_cmd(cmd, cwd, timeout):
    """Run a command, return (returncode, stdout, stderr). Timeout returns code 124."""
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired as e:
        out = e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
        err = e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or "")
        return 124, out, err + f"\nTIMEOUT after {timeout} s"


def copytree(src, dst):
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
