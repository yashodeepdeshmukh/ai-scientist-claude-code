import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


class ResearchCheckpointTest(unittest.TestCase):
    def test_rate_limit_then_resume_from_a_new_session(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "project"
            project.mkdir()
            workspace = project / "workspace"
            workspace.mkdir()
            env = dict(os.environ, AI_SCIENTIST_STATE_DIR=str(root / "state"),
                       AI_SCIENTIST_PROJECT_DIR=str(project), CLAUDE_CODE_SESSION_ID="first",
                       CLAUDE_ENV_FILE=str(root / "session.env"))

            def run(script, *args, payload=None, cwd=project):
                return subprocess.check_output(
                    [sys.executable, str(SCRIPTS / script), *map(str, args)], cwd=cwd, env=env,
                    input=payload, text=True,
                )

            def state(*args):
                return run("research_state.py", *args)

            def hook(event, session, cwd=project, **fields):
                return run("resume_hook.py", payload=json.dumps({
                    "hook_event_name": event, "session_id": session, "cwd": str(cwd), **fields,
                }), cwd=cwd)

            options = {"num_reviews": 3, "parallel": True}
            state("begin", workspace, json.dumps(options))
            (workspace / "ideas.json").write_text('[{"Name":"seed"}]')
            state("checkpoint", workspace, "ideas")
            (workspace / "ideas.json").write_text('[{"Name":"seed"},{"Name":"generated"}]')

            hook("StopFailure", "other", error="rate_limit")
            hook("StopFailure", "first", error="overloaded")
            self.assertIsNone(json.loads(state("status"))[0]["interruption"])
            hook("StopFailure", "first", error="rate_limit")
            saved, = json.loads(state("status"))
            self.assertEqual(saved["interruption"], "rate_limit")
            self.assertEqual(saved["initial_ideas"], ["seed"])
            self.assertEqual(saved["options"], options)

            context = json.loads(hook("SessionStart", "second"))["hookSpecificOutput"]
            self.assertIn(str(workspace), context["additionalContext"])

            env["CLAUDE_CODE_SESSION_ID"] = "second"
            state("checkpoint", workspace, "ideas")
            state("checkpoint", workspace, "novelty")
            state("checkpoint", workspace, "research", "--selected", '["generated"]')
            state("record", workspace, "experiments", "completed", "--idea", "generated")
            saved, = json.loads(state("status"))
            self.assertEqual(saved["selected"], ["generated"])
            self.assertIsNone(saved["interruption"])
            self.assertEqual(json.loads(state("history", workspace))[-1]["idea"], "generated")
            state("checkpoint", workspace, "complete")
            self.assertEqual(json.loads(state("status")), [])
            self.assertEqual(hook("SessionStart", "second"), "")


if __name__ == "__main__":
    unittest.main()
