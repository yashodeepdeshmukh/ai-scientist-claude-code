#!/usr/bin/env python3
"""Check and compile the paper in <idea_dir>/latex/template.tex.

Usage: latex_build.py <idea_dir> [--check-only] [--name PaperName]

Checks (as in AI-Scientist's generate_latex):
  * every \\cite key exists in the filecontents{references.bib} block
  * every \\includegraphics file exists (latex/ or idea folder)
  * no figure included twice, no duplicate \\section headers
  * chktex warnings (if chktex is installed)
Then compiles: pdflatex, bibtex, pdflatex, pdflatex -> <idea_dir>/<name>.pdf
Prints a JSON report. Exit 1 if compilation fails.
"""
import argparse
from pathlib import Path
import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import process_failure, run_cmd  # noqa: E402
from verify_benchmark import REPORT, TABLE_INPUT, current_report, digest, evaluator_for, record_pdf

BIB_RE = re.compile(r"\\begin\{filecontents\*?\}(?:\[[^\]]*\])?\{references\.bib\}(.*?)\\end\{filecontents\*?\}", re.S)
CITE_RE = re.compile(r"\\cite[pt]?\*?(?:\[[^\]]*\])*\{([^}]*)\}")
FIG_RE = re.compile(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]*)\}")
SEC_RE = re.compile(r"\\section\*?\{([^}]*)\}")


def strip_comments(tex):
    return "\n".join(re.sub(r"(?<!\\)%.*", "", line) for line in tex.splitlines())


def check(tex, latex_dir, idea_dir):
    issues = []
    m = BIB_RE.search(tex)
    if not m:
        issues.append("No \\begin{filecontents}{references.bib} block found.")
        bib_keys = set()
    else:
        bib_keys = set(re.findall(r"@\w+\s*\{\s*([^,\s]+)\s*,", m.group(1)))
        dupes = [k for k in bib_keys if len(re.findall(r"@\w+\s*\{\s*" + re.escape(k) + r"\s*,", m.group(1))) > 1]
        for k in dupes:
            issues.append(f"Duplicate bib key: {k}")
    body = strip_comments(tex)
    cited = set()
    for group in CITE_RE.findall(body):
        cited.update(k.strip() for k in group.split(",") if k.strip())
    for k in sorted(cited - bib_keys):
        issues.append(f"Citation key not in references.bib: {k}")

    figs = FIG_RE.findall(body)
    for f in figs:
        found = any(os.path.exists(os.path.join(base, f + ext))
                    for base in (latex_dir, idea_dir) for ext in ("", ".png", ".pdf", ".jpg"))
        if not found:
            issues.append(f"Figure file not found: {f}")
    for f in sorted({f for f in figs if figs.count(f) > 1}):
        issues.append(f"Figure included more than once: {f}")
    secs = SEC_RE.findall(body)
    for s in sorted({s for s in secs if secs.count(s) > 1}):
        issues.append(f"Duplicate section header: {s}")
    return issues, sorted(cited), figs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("idea_dir")
    ap.add_argument("--check-only", action="store_true")
    ap.add_argument("--name", default=None)
    ap.add_argument("--timeout", type=int, default=60)
    a = ap.parse_args()

    idea_dir = os.path.abspath(a.idea_dir)
    latex_dir = os.path.join(idea_dir, "latex")
    tex_path = os.path.join(latex_dir, "template.tex")
    with open(tex_path) as f:
        tex = f.read()
    issues, cited, figs = check(tex, latex_dir, idea_dir)
    report = {"issues": issues, "citations": cited, "figures": figs}

    folder = Path(idea_dir).resolve()
    evaluator = evaluator_for(folder)
    verification_hash = None
    if evaluator:
        if not current_report(folder, evaluator):
            issues.append("Run verify_benchmark.py for this idea before building the paper.")
        else:
            verification_hash = digest(folder / REPORT)
        if TABLE_INPUT not in strip_comments(tex):
            issues.append(f"Include the verified results table with {TABLE_INPUT}.")

    if shutil.which("chktex"):
        _, out, _ = run_cmd(["chktex", "-q", "-n2", "-n24", "-n13", "-n1", "template.tex"], latex_dir, 60)
        report["chktex"] = out.strip()[-3000:]
    else:
        report["chktex"] = "chktex not installed (optional)"

    if a.check_only:
        print(json.dumps(report, indent=2))
        return

    if evaluator and (not verification_hash or TABLE_INPUT not in strip_comments(tex)):
        report["pdf"] = None
        print(json.dumps(report, indent=2))
        sys.exit(1)

    name = a.name
    if not name:
        try:
            with open(os.path.join(idea_dir, "idea.json")) as f:
                name = json.load(f)["Name"]
        except (FileNotFoundError, KeyError):
            name = "paper"
    if not isinstance(name, str) or not re.fullmatch(r"[\w.-]+", name) or name in (".", ".."):
        ap.error("Paper name must be a filename stem")

    missing_tools = [tool for tool in ("pdflatex", "bibtex") if not shutil.which(tool)]
    if missing_tools:
        report["compile"] = "Missing tools: " + ", ".join(missing_tools)
        print(json.dumps(report, indent=2))
        sys.exit(1)

    latex = ["pdflatex", "-no-shell-escape", "-halt-on-error", "-interaction=nonstopmode", "template.tex"]
    report["compile_steps"] = []
    pdf = os.path.join(latex_dir, "template.pdf")
    if os.path.lexists(pdf):
        os.unlink(pdf)
    for cmd in (latex, ["bibtex", "template"], latex, latex):
        code, out, _ = run_cmd(cmd, latex_dir, a.timeout)
        report["compile_steps"].append({"cmd": " ".join(cmd), "code": code})
        if code != 0:
            report["pdf"] = None
            report["compile"] = process_failure(code, a.timeout)
            report["diagnostics"] = "See the local LaTeX or BibTeX build log."
            print(json.dumps(report, indent=2))
            sys.exit(1)
    report["undefined_refs"] = sorted(set(re.findall(r"(?:Citation|Reference) `([^']+)' .*undefined", out)))
    report["pdf"] = None
    if os.path.isfile(pdf) and not report["undefined_refs"]:
        if evaluator and (not current_report(folder, evaluator) or digest(folder / REPORT) != verification_hash):
            report["issues"].append("Benchmark evidence changed during the build. Retry the build.")
            print(json.dumps(report, indent=2))
            sys.exit(1)
        dest = os.path.join(idea_dir, f"{name}.pdf")
        shutil.copy(pdf, dest)
        if evaluator:
            record_pdf(Path(dest), verification_hash)
        report["pdf"] = dest
    print(json.dumps(report, indent=2))
    sys.exit(0 if report["pdf"] else 1)


if __name__ == "__main__":
    main()
