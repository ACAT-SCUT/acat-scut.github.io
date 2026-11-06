"""Preview or apply a reviewed CSV; unspecified members and fields are preserved."""
import argparse
import copy
import csv
import json
from pathlib import Path
import tempfile

from content import CONTENT, json_text, load_data
from validate import validate_data

COLUMNS = {"action", "id", "name", "role", "status", "entryYear", "url", "researchIds"}
CLEAR = "__CLEAR__"


def prepare_import(data, csv_path):
    result = copy.deepcopy(data)
    members = {m["id"]: m for m in result["members"]}
    groups = {g["id"]: g for g in result["research"]}
    seen, changes = set(), []
    with Path(csv_path).open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        fields = reader.fieldnames or []
        if len(fields) != len(set(fields)) or set(fields) - COLUMNS or "id" not in fields:
            raise ValueError("CSV requires id and only documented, unique columns")
        for line, raw in enumerate(reader, 2):
            if None in raw or any(value is None for value in raw.values()):
                raise ValueError(f"line {line}: column count does not match header")
            row = {key: value.strip() for key, value in raw.items()}
            if not any(row.values()):
                continue
            mid = row.get("id", "")
            if not mid or mid in seen:
                raise ValueError(f"line {line}: missing or duplicate id {mid}")
            seen.add(mid)
            action = row.get("action") or "update"
            if action not in ("add", "update"):
                raise ValueError(f"line {line}: action must be add or update")
            if (action == "add") == (mid in members):
                raise ValueError(f"line {line}: add requires a new id; update requires an existing id ({mid})")
            before = copy.deepcopy(members.get(mid))
            member = members.get(mid, {"id": mid})
            for key in ("name", "role", "status", "entryYear", "url"):
                value = row.get(key, "")
                if not value:
                    continue
                if value == CLEAR:
                    if key not in ("url", "entryYear"):
                        raise ValueError(f"line {line}: cannot clear {key}")
                    member.pop(key, None)
                elif key == "entryYear":
                    try:
                        member[key] = int(value)
                    except ValueError as error:
                        raise ValueError(f"line {line}: entryYear must be an integer") from error
                else:
                    member[key] = value
            if action == "add":
                result["members"].append(member)
                members[mid] = member
            old_groups = [gid for gid, group in groups.items() if mid in group["memberIds"]]
            if row.get("researchIds"):
                target = [] if row["researchIds"] == CLEAR else [gid.strip() for gid in row["researchIds"].split(";")]
                if len(target) != len(set(target)) or any(gid not in groups for gid in target):
                    raise ValueError(f"line {line}: duplicate or unknown researchIds")
                for gid, group in groups.items():
                    if gid not in target and mid in group["memberIds"]:
                        group["memberIds"].remove(mid)
                    elif gid in target and mid not in group["memberIds"]:
                        group["memberIds"].append(mid)
            new_groups = [gid for gid, group in groups.items() if mid in group["memberIds"]]
            if before != member or old_groups != new_groups:
                changes.append({"id": mid, "before": before, "after": copy.deepcopy(member),
                                "researchBefore": old_groups, "researchAfter": new_groups})
    errors = validate_data(result)
    if errors:
        raise ValueError("\n".join(errors))
    return result, changes


def apply_import(directory, original, updated):
    """Stage both files before replacement; roll back on ordinary write errors."""
    directory = Path(directory)
    filenames = {"members": "members.json", "research": "research.json"}
    changed = [key for key in filenames if original[key] != updated[key]]
    originals = {key: (directory / filenames[key]).read_bytes() for key in changed}
    for key, filename in filenames.items():
        if json.loads((directory / filename).read_text(encoding="utf-8")) != original[key]:
            raise ValueError("Content changed during import; preview again")
    staged = {}
    try:
        for key in changed:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=directory, prefix=".import-", delete=False) as stream:
                stream.write(json_text(updated[key]))
                staged[key] = Path(stream.name)
        try:
            for key in changed:
                staged[key].replace(directory / filenames[key])
        except OSError:
            for key, raw in originals.items():
                (directory / filenames[key]).write_bytes(raw)
            raise
    finally:
        for path in staged.values():
            path.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="reviewed UTF-8 CSV, kept under .local/")
    parser.add_argument("--content-dir", type=Path, default=CONTENT, help="alternate data directory for testing")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="apply reviewed changes; never builds or publishes")
    mode.add_argument("--dry-run", action="store_true", help="preview only (default)")
    args = parser.parse_args()
    try:
        original = load_data(args.content_dir)
        updated, changes = prepare_import(original, args.input)
        if args.apply:
            apply_import(args.content_dir, original, updated)
    except (OSError, ValueError) as error:
        parser.exit(1, str(error) + "\n")
    print(json.dumps({"mode": "applied" if args.apply else "preview", "changes": changes}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
