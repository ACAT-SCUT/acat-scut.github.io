"""Read canonical content. No network, writes, or automatic date changes."""
import json
from pathlib import Path

from validate import validate_data

CONTENT = Path(__file__).resolve().parents[1] / "content"
FILES = {"meta": "team.json", "research": "research.json", "members": "members.json",
         "papers": "papers.json", "projects": "projects.json", "homepage": "homepage.json"}


def load_data(directory=None):
    directory = Path(directory) if directory is not None else CONTENT
    data = {}
    for key, filename in FILES.items():
        try:
            data[key] = json.loads((directory / filename).read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise ValueError(f"{filename}: {error}") from error
    errors = validate_data(data)
    if errors:
        raise ValueError("\n".join(errors))
    return data


def json_text(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"
