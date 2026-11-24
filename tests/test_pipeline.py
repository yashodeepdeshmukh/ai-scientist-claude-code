"""Exercise the stage planner against a saved bundled experiment."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from aggregate_reviews import LISTS, NUMERIC


def cli(script, *args):
    return subprocess.check_output(
        [sys.executable, str(SCRIPTS / f"{script}.py"), *map(str, args)], text=True
    )


class PipelineResumeTest(unittest.TestCase):
    def test_resumes_writeup_and_retries_only_incomplete_reviews(self):
        with tempfile.TemporaryDirectory() as workspace:
            baseline = json.loads(cli("init_workspace", "optim_toy", "--workspace", workspace))
            exp_dir = Path(baseline["exp_dir"])
            ideas = exp_dir / "ideas.json"
            name = json.loads(ideas.read_text())[0]["Name"]
            folder = Path(cli("init_idea", exp_dir, name, "--resume").strip())

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
