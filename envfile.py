"""Read and write the .env file, preserving comments and line order."""
import os
import re
import tempfile
from pathlib import Path

from dotenv import dotenv_values

_LINE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=")


def read(path):
    """Return {key: value} from the file (empty if it does not exist)."""
    path = Path(path)
    if not path.exists():
        return {}
    return {k: v or "" for k, v in dotenv_values(path).items()}


def _format(value):
    value = str(value)
    if value == "" or not re.search(r"[\s#'\"\\$]", value):
        return value
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _write(path, lines):
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".env.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines) + "\n")
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def save(path, values, template=None):
    """Update the keys in `values`, appending the ones not in the file yet.

    If the file does not exist, start from `template` (e.g. .env.example) to keep its comments.
    """
    path = Path(path)
    if path.exists():
        base = path.read_text(encoding="utf-8")
    elif template and Path(template).exists():
        base = Path(template).read_text(encoding="utf-8")
    else:
        base = ""

    pending = dict(values)
    out = []
    for line in base.splitlines():
        m = _LINE.match(line)
        if m and m.group(1) in pending:
            key = m.group(1)
            out.append(f"{key}={_format(pending.pop(key))}")
        else:
            out.append(line)
    if pending and out and out[-1].strip():
        out.append("")
    for key, value in pending.items():
        out.append(f"{key}={_format(value)}")
    _write(path, out)


def rename_keys(path, mapping):
    """Rename keys in place ({old: new}). If the new key already exists, the old line is dropped.

    Returns True if the file changed.
    """
    path = Path(path)
    if not path.exists():
        return False
    lines = path.read_text(encoding="utf-8").splitlines()
    present = {m.group(1) for line in lines if (m := _LINE.match(line))}
    out, changed = [], False
    for line in lines:
        m = _LINE.match(line)
        if m and m.group(1) in mapping:
            changed = True
            new = mapping[m.group(1)]
            if new not in present:
                out.append(_LINE.sub(f"{new}=", line, count=1))
                present.add(new)
            continue
        out.append(line)
    if changed:
        _write(path, out)
    return changed
