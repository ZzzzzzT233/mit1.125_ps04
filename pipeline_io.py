"""Shared I/O utilities; substantive work stays in its owning component."""
import contextlib
import datetime as dt
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlsplit
import uuid

ROOT = Path(__file__).resolve().parent


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def emit(value):
    print(json.dumps(value, ensure_ascii=False), flush=True)


def load(path):
    return json.loads(Path(path).read_text())


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


def records(stream):
    for number, line in enumerate(stream, 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"Invalid JSON on line {number}") from error
        if not isinstance(value, dict):
            raise ValueError(f"Line {number} must contain an object")
        yield value


def local_path(value):
    if not isinstance(value, str) or Path(value).is_absolute():
        raise ValueError("Evidence paths must be repository-relative strings")
    path = (ROOT / value).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError("Evidence path escapes the repository")
    return path


def run_dir(value):
    path = local_path(value)
    if not (path / "run.json").is_file():
        raise ValueError(f"Missing run metadata: {value}")
    return path


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def published_date(value):
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Publication date must be a string or null")
    if len(value) == 10:
        return dt.date.fromisoformat(value)
    timestamp = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if timestamp.tzinfo is None:
        raise ValueError("Publication timestamps require a timezone")
    return timestamp.astimezone(dt.timezone.utc).date()


def date_reason(value, as_of):
    try:
        date = published_date(value)
    except ValueError:
        return "invalid_date"
    if date is None:
        return "unknown_date"
    if date > as_of:
        return "future_date"
    if date < as_of - dt.timedelta(days=29):
        return "outside_window"
    return None


def fetch(url, destination=None):
    parts = urlsplit(url)
    if parts.scheme not in ("https", "http") or not parts.hostname or parts.username or parts.password:
        raise ValueError("Expected a public HTTP(S) URL without credentials")
    command = ["curl", "--fail", "--location", "--silent", "--show-error", "--max-redirs", "5", "--connect-timeout", "15", "--max-time", "180" if destination else "45"]
    if destination:
        command += ["--max-filesize", "536870912", "--output", str(destination)]
    else:
        command += ["--max-filesize", "16777216"]
    result = subprocess.run(command + [url], capture_output=True, timeout=190 if destination else 55)
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors="replace").strip())
    return result.stdout


@contextlib.contextmanager
def stage(name, directory):
    receipt = {"stage": name, "status": "completed", "input_count": 0, "output_count": 0,
               "started_at": now(), "tools": ["Python stdlib"], "models": [],
               "cost_usd": None, "cost_note": "No model API used; local compute and transfer costs are not measured.", "errors": []}
    code = 0
    try:
        yield receipt
        if receipt["errors"]:
            code = 1
            receipt["status"] = "incomplete"
    except (ValueError, KeyError, TypeError) as error:
        code = 2
        receipt["status"] = "invalid_input"
        receipt["errors"].append(str(error))
    except Exception as error:
        code = 1
        receipt["status"] = "failed"
        receipt["errors"].append(str(error))
    finally:
        receipt["finished_at"] = now()
        receipt["exit_code"] = code
        save(directory / "logs" / f"{name}-{uuid.uuid4().hex}.json", receipt)
    for error in receipt["errors"]:
        print(f"{name}: {error}", file=sys.stderr)
    if code:
        raise SystemExit(code)


def component(name, function):
    try:
        if len(sys.argv) != 2:
            raise ValueError("Expected RUN_DIR as the only argument")
        directory = run_dir(sys.argv[1])
    except (ValueError, OSError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(2)
    with stage(name, directory) as receipt:
        function(directory, receipt)


def workflow_receipt(directory, name, started_at, code, input_name, output_name):
    def count(filename):
        path = directory / filename
        return sum(bool(line.strip()) for line in path.read_text().splitlines()) if path.is_file() else 0
    save(directory / 'logs' / f'{name}-{uuid.uuid4().hex}.json', {
        'stage': name, 'status': 'completed' if code == 0 else 'incomplete',
        'exit_code': code, 'started_at': started_at, 'finished_at': now(),
        'input_count': count(input_name), 'output_count': count(output_name),
        'tools': ['Bash'], 'models': [], 'cost_usd': None,
        'cost_note': 'Coordination only; component costs are counted in their own receipts.',
        'errors': [] if code == 0 else ['Workflow did not complete; inspect component receipts and review issues.']})


if __name__ == '__main__':
    if len(sys.argv) != 8 or sys.argv[1] != 'workflow_receipt':
        raise SystemExit('Usage: pipeline_io.py workflow_receipt RUN_DIR STAGE STARTED_AT CODE INPUT_FILE OUTPUT_FILE')
    workflow_receipt(run_dir(sys.argv[2]), sys.argv[3], sys.argv[4], int(sys.argv[5]), sys.argv[6], sys.argv[7])
