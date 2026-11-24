"""Exercise the stage planner against a saved bundled experiment."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from aggregate_reviews import LISTS, NUMERIC


def cli(script, *args):
    return subprocess.check_output(
        [sys.executable, str(SCRIPTS / f"{script}.py"), *map(str, args)],
        text=True, env=dict(os.environ, OPENBLAS_NUM_THREADS="1"),
    )


class PipelineResumeTest(unittest.TestCase):
    def test_resumes_writeup_and_retries_only_incomplete_reviews(self):
        with tempfile.TemporaryDirectory() as workspace:
            baseline = json.loads(cli("init_workspace", "optim_toy", "--workspace", workspace))
            # Exercise the legacy pipeline for workspaces without an evaluator.
            (Path(baseline["template_dir"]) / "benchmark_evaluator.py").rename(Path(workspace) / "benchmark_evaluator.py")
            exp_dir = Path(baseline["exp_dir"])
            ideas = exp_dir / "ideas.json"
            name = json.loads(ideas.read_text())[0]["Name"]
            folder = Path(cli("init_idea", exp_dir, name, "--resume").strip())

            shutil.copyfile(Path(workspace) / "benchmark_evaluator.py", folder / "benchmark_evaluator.py")

            def plan():
                return json.loads(cli("pipeline", exp_dir, "--idea", name, "--num-reviews", 3))[0]

            self.assertEqual(plan()["stage"], "experiments")
            cli("run_experiment", folder, 1)
            cli("ideas", "set", ideas, name, "status", "experiments_done")
            self.assertEqual(plan()["stage"], "writeup")

            paper = folder / f"{name}.pdf"
            paper.write_bytes(b"%PDF-1.0\nDraft")
            cli("ideas", "set", ideas, name, "status", "writeup_failed")
            self.assertEqual(plan()["stage"], "writeup")

            cli("ideas", "set", ideas, name, "status", "writeup_done")
            review_plan = plan()
            self.assertEqual(review_plan["stage"], "review")
            slots = review_plan["reviewers"]
            review = {
                **{key: lo for key, (lo, _) in NUMERIC.items()},
                **{key: [] for key in LISTS},
                "Decision": "Reject",
                "Summary": "Review",
                "Ethical Concerns": False,
            }
            Path(slots[0]["out"]).write_text(json.dumps(review))
            Path(slots[1]["out"]).write_text("{")
            resumed = plan()["reviewers"]
            self.assertEqual([slot["id"] for slot in resumed if not slot["complete"]], [2, 3])

            paper.write_bytes(b"%PDF-1.0\nRevised draft")
            self.assertTrue(all(not slot["complete"] for slot in plan()["reviewers"]))


    def test_benchmark_uses_checkpoints_and_resumes_when_inputs_change(self):
        with tempfile.TemporaryDirectory() as workspace:
            baseline = json.loads(cli("init_workspace", "optim_toy", "--workspace", workspace))
            exp_dir = Path(baseline["exp_dir"])
            ideas = exp_dir / "ideas.json"
            name = json.loads(ideas.read_text())[0]["Name"]
            folder = Path(cli("init_idea", exp_dir, name, "--resume").strip())

            def stage():
                return json.loads(cli("pipeline", exp_dir, "--idea", name))[0]["stage"]

            experiment = folder / "experiment.py"
            experiment.write_text(experiment.read_text().replace("lr=0.1", "lr=0.001"))
            cli("run_experiment", folder, 1)
            experiment.write_text(experiment.read_text().replace("lr=0.001", "lr=0.00001"))
            cli("run_experiment", folder, 2)
            cli("ideas", "set", ideas, name, "status", "experiments_done")
            self.assertEqual(stage(), "verify")
            metrics_file = folder / "run_1/final_info.json"
            metrics = json.loads(metrics_file.read_text())
            for dataset in metrics.values():
                dataset["means"]["final_validation_acc"] = 1.0
            metrics_file.write_text(json.dumps(metrics))

            def verify():
                return json.loads(cli("verify_benchmark", folder))

            report = verify()
            self.assertEqual(report["selected_run"], "run_1")
            self.assertEqual(set(report["validation"]), {"run_0", "run_1", "run_2"})
            self.assertEqual(set(report["test"]), {"run_0", "run_1"})
            self.assertTrue(all(value < 1.0 for seeds in report["validation"]["run_1"].values()
                                for value in seeds.values()))
            self.assertEqual(stage(), "writeup")
            tex = folder / "benchmark_results.tex"
            self.assertIn("Delta (pp)", tex.read_text())
            checkpoint = folder / "run_1/checkpoint.npz"
            checkpoint_mtime = checkpoint.stat().st_mtime_ns
            manifest = folder / "benchmark_results.json"
            recorded_mtime = manifest.stat().st_mtime_ns
            self.assertEqual(verify(), report)
            self.assertEqual(manifest.stat().st_mtime_ns, recorded_mtime)
            self.assertEqual(checkpoint.stat().st_mtime_ns, checkpoint_mtime)

            if shutil.which("pdflatex") and shutil.which("bibtex"):
                manuscript = folder / "latex/template.tex"
                manuscript.write_text(manuscript.read_text().replace(
                    "INTRO HERE", r"Compare against \cite{kingma2014adam}."
                ))
                result = json.loads(cli("latex_build", folder))
                self.assertTrue(Path(result["pdf"]).is_file())
                cli("ideas", "set", ideas, name, "status", "writeup_done")
                self.assertEqual(stage(), "review")

            # ZIP permits trailing bytes; changing them must invalidate the old record.
            checkpoint.write_bytes(checkpoint.read_bytes() + b"\x00")
            self.assertEqual(stage(), "verify")
            renewed = verify()
            self.assertNotEqual(renewed["inputs"], report["inputs"])
            self.assertEqual(renewed["test"], report["test"])
            self.assertEqual(stage(), "writeup")
