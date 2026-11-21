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
import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import run_cmd  # noqa: E402

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

    if shutil.which("chktex"):
        _, out, _ = run_cmd(["chktex", "-q", "-n2", "-n24", "-n13", "-n1", "template.tex"], latex_dir, 60)
        report["chktex"] = out.strip()[-3000:]
    else:
        report["chktex"] = "chktex not installed (optional)"

    if a.check_only:
        print(json.dumps(report, indent=2))
        return

    if not shutil.which("pdflatex"):
        report["compile"] = "pdflatex not installed"
        print(json.dumps(report, indent=2))
        sys.exit(1)
    log = []
    for cmd in (["pdflatex", "-interaction=nonstopmode", "template.tex"], ["bibtex", "template"],
                ["pdflatex", "-interaction=nonstopmode", "template.tex"],
                ["pdflatex", "-interaction=nonstopmode", "template.tex"]):
        code, out, err = run_cmd(cmd, latex_dir, a.timeout)
        log.append({"cmd": " ".join(cmd), "code": code})
    errors = re.findall(r"^! .*$", out, re.M)
    undefined = sorted(set(re.findall(r"(?:Citation|Reference) `([^']+)' .*undefined", out)))
    pdf = os.path.join(latex_dir, "template.pdf")
    name = a.name
    if not name:
        try:
            with open(os.path.join(idea_dir, "idea.json")) as f:
                name = json.load(f)["Name"]
        except Exception:
            name = "paper"
    report["compile_steps"] = log
    report["latex_errors"] = errors[:20]
    report["undefined_refs"] = undefined
    if os.path.exists(pdf):
        dest = os.path.join(idea_dir, f"{name}.pdf")
        shutil.copy(pdf, dest)
        report["pdf"] = dest
        print(json.dumps(report, indent=2))
    else:
        report["pdf"] = None
        report["log_tail"] = out[-2000:]
        print(json.dumps(report, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
