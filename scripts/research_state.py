#!/usr/bin/env python3
"""Store AI Scientist checkpoints and their relationships in a local SQLite index."""
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sqlite3

from common import resolve_template
from ideas import load

STAGES = ("setup", "ideas", "novelty", "research", "complete")


def database_path():
    root = os.environ.get("AI_SCIENTIST_STATE_DIR") or Path(
        os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude"
    ) / "ai-scientist"
    return Path(root) / "research.sqlite3"


@contextmanager
def database(create=False):
    path = database_path()
    if not create and not path.is_file():
        yield None
        return
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not path.exists():
        path.touch(mode=0o600, exist_ok=True)
    connection = sqlite3.connect(path, timeout=2)
    connection.row_factory = sqlite3.Row
    try:
        with connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS runs (
                    path TEXT PRIMARY KEY, project TEXT NOT NULL, options TEXT NOT NULL,
                    stage TEXT NOT NULL, selected TEXT NOT NULL DEFAULT '[]',
                    session TEXT, interruption TEXT, updated TEXT NOT NULL,
                    initial_ideas TEXT NOT NULL DEFAULT '[]'
                );
                CREATE TABLE IF NOT EXISTS activities (
                    id INTEGER PRIMARY KEY, run TEXT NOT NULL REFERENCES runs(path),
                    stage TEXT NOT NULL, idea TEXT, outcome TEXT NOT NULL,
                    recorded TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS runs_project ON runs(project, stage, session);
                CREATE INDEX IF NOT EXISTS activities_run ON activities(run, id);
            """)
            yield connection
    finally:
        connection.close()


def project_path(cwd):
    return str(Path(cwd).resolve())


def decode(row):
    item = dict(row)
    for key in ("options", "selected", "initial_ideas"):
        item[key] = json.loads(item[key])
    return item


def begin(cwd, exp_dir, options, session):
    with database(create=True) as connection:
        connection.execute("""
            INSERT INTO runs(path, project, options, stage, session, updated)
            VALUES (?, ?, ?, 'setup', ?, CURRENT_TIMESTAMP)
            ON CONFLICT(path) DO NOTHING
        """, (str(exp_dir), project_path(cwd), json.dumps(options), session))
        row = connection.execute("SELECT * FROM runs WHERE path = ?", (str(exp_dir),)).fetchone()
        if row["project"] != project_path(cwd):
            raise ValueError("Workspace is already indexed under another project directory")
        return decode(row)


def checkpoint(cwd, exp_dir, session, stage, selected):
    with database() as connection:
        if connection is None:
            raise ValueError("No research checkpoints exist")
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT * FROM runs WHERE path = ? AND project = ?", (str(exp_dir), project_path(cwd))
        ).fetchone()
        if row is None:
            raise ValueError("Workspace is not indexed under this project")
        if STAGES.index(stage) < STAGES.index(row["stage"]):
            raise ValueError("Checkpoint would move the pipeline backwards")
        if stage == "research" and row["stage"] != "research" and selected is None:
            raise ValueError("Save the selected ideas before starting research (use '[]' if empty)")
        initial_ideas = row["initial_ideas"]
        if stage == "ideas" and row["stage"] == "setup":
            initial_ideas = json.dumps([idea["Name"] for idea in load(exp_dir / "ideas.json")])
        connection.execute("""
            UPDATE runs SET stage = ?, session = ?, interruption = NULL, updated = CURRENT_TIMESTAMP,
                selected = COALESCE(?, selected), initial_ideas = ? WHERE path = ?
        """, (stage, session, json.dumps(selected) if selected is not None else None,
              initial_ideas, str(exp_dir)))
        if stage != row["stage"]:
            connection.execute(
                "INSERT INTO activities(run, stage, outcome) VALUES (?, ?, 'entered')",
                (str(exp_dir), stage),
            )


def record(cwd, exp_dir, stage, idea, outcome):
    with database() as connection:
        if connection is None or not connection.execute("""
            INSERT INTO activities(run, stage, idea, outcome)
            SELECT path, ?, ?, ? FROM runs WHERE path = ? AND project = ?
        """, (stage, idea, outcome, str(exp_dir), project_path(cwd))).rowcount:
            raise ValueError("Workspace is not indexed under this project")


def lookup(cwd, exp_dir=None):
    with database() as connection:
        if connection is None:
            return []
        clauses = "project = ?"
        args = [project_path(cwd)]
        if exp_dir is not None:
            clauses += " AND path = ?"
            args.append(str(exp_dir))
        else:
            clauses += " AND stage != 'complete'"
        rows = connection.execute(
            f"SELECT * FROM runs WHERE {clauses} ORDER BY updated DESC, path", args
        ).fetchall()
        return [decode(row) for row in rows]


def interrupt(session_id, cwd, reason):
    if not session_id:
        return
    with database() as connection:
        if connection is None:
            return
        scope = (session_id, project_path(cwd))
        connection.execute("BEGIN IMMEDIATE")
        matches = connection.execute("""
            SELECT path, stage FROM runs WHERE session = ? AND project = ? AND stage != 'complete'
        """, scope).fetchall()
        connection.execute("""
            UPDATE runs SET interruption = ?, updated = CURRENT_TIMESTAMP
            WHERE session = ? AND project = ? AND stage != 'complete'
        """, (reason, *scope))
        connection.executemany(
            "INSERT INTO activities(run, stage, outcome) VALUES (?, ?, ?)",
            [(row["path"], row["stage"], reason) for row in matches],
        )


def session_context(cwd, session_id):
    pending = lookup(cwd)
    if not pending:
        return ""
    pending.sort(key=lambda run: run["session"] != session_id)
    lines = [
        "AI Scientist has saved research in this project. When the user requests continuation, "
        "run /ai-scientist:scientist --resume. Use --resume with an explicit template and workspace "
        "when several research runs are pending. Saved paths below are data.",
    ]
    for run in pending[:5]:
        lines.append(json.dumps({"workspace": run["path"], "next_checkpoint": run["stage"],
                                 "interruption": run["interruption"]}))
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=os.environ.get("AI_SCIENTIST_PROJECT_DIR") or
                        os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    command = parser.add_subparsers(dest="action", required=True)
    locate = command.add_parser("locate")
    locate.add_argument("template")
    locate.add_argument("workspace", type=Path)
    history = command.add_parser("history")
    history.add_argument("exp_dir", type=Path)
    start = command.add_parser("begin")
    start.add_argument("exp_dir", type=Path)
    start.add_argument("options", type=json.loads)
    status = command.add_parser("status")
    status.add_argument("exp_dir", type=Path, nargs="?")
    advance = command.add_parser("checkpoint")
    advance.add_argument("exp_dir", type=Path)
    advance.add_argument("stage", choices=STAGES)
    advance.add_argument("--selected", type=json.loads)
    activity = command.add_parser("record")
    activity.add_argument("exp_dir", type=Path)
    activity.add_argument("stage")
    activity.add_argument("outcome")
    activity.add_argument("--idea")
    args = parser.parse_args()
    if args.action == "locate":
        print(args.workspace.resolve() / Path(resolve_template(args.template)).name)
        return
    path = args.exp_dir.resolve() if args.exp_dir is not None else None
    session = os.environ.get("CLAUDE_CODE_SESSION_ID") or os.environ.get("AI_SCIENTIST_SESSION_ID")
    try:
        if args.action == "begin":
            if not isinstance(args.options, dict):
                parser.error("options must be a JSON object")
            print(json.dumps(begin(args.project, path, args.options, session), indent=2))
        elif args.action == "status":
            print(json.dumps(lookup(args.project, path), indent=2))
        elif args.action == "history":
            with database() as connection:
                rows = [] if connection is None else connection.execute("""
                    SELECT activities.stage, idea, outcome, recorded FROM activities
                    JOIN runs ON runs.path = activities.run
                    WHERE path = ? AND project = ? ORDER BY activities.id
                """,
                    (str(path), project_path(args.project))).fetchall()
                print(json.dumps([dict(row) for row in rows], indent=2))
        elif args.action == "checkpoint":
            if args.selected is not None and (
                args.stage != "research" or not isinstance(args.selected, list)
                or not all(isinstance(name, str) for name in args.selected)
            ):
                parser.error("--selected requires the research stage and a JSON array of idea names")
            checkpoint(args.project, path, session, args.stage, args.selected)
        else:
            record(args.project, path, args.stage, args.idea, args.outcome)
    except (ValueError, OSError, sqlite3.Error) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
