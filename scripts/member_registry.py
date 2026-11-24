"""Canonical people/experiences and read-only compatibility views."""
import copy
import json
from pathlib import Path
import re

from member_demo.core import DemoError, validate_registry as check_registry

REGISTRY_FILES = {"members": "members.json", "experiences": "member-experiences.json"}


def validate_registry(state):
    for key, allowed, required in (
        ("members", {"id", "name", "url", "displayExperienceId", "sortName"}, {"id", "name", "displayExperienceId"}),
        ("experiences", {"id", "memberId", "role", "entryYear", "status", "graduationConfirmed", "researchIds"}, {"id", "memberId", "role", "status", "graduationConfirmed", "researchIds"}),
    ):
        rows = state.get(key)
        if not isinstance(rows, list):
            raise DemoError(key + " must be an array")
        for row in rows:
            if not isinstance(row, dict) or set(row) - allowed or required - set(row):
                raise DemoError(key + ": unsupported or missing fields; keep private review details local")
            if not isinstance(row["id"], str) or not re.fullmatch(r"[a-z][a-z0-9-]*", row["id"]):
                raise DemoError(key + ": invalid stable id")
            if key == "members" and "sortName" in row and (
                not isinstance(row["sortName"], str) or not re.fullmatch(r"[a-z]+(?: [a-z]+)*", row["sortName"])
            ):
                raise DemoError("sortName must contain lowercase pinyin syllables separated by spaces")
            if key == "experiences" and "entryYear" in row and type(row["entryYear"]) is not int:
                raise DemoError("entryYear must be an integer")
    check_registry(state)


def load_registry(directory):
    directory = Path(directory)
    state = {key: json.loads((directory / name).read_text(encoding="utf-8")) for key, name in REGISTRY_FILES.items()}
    state["directions"] = json.loads((directory / "research.json").read_text(encoding="utf-8"))
    state["idPrefixes"] = {"members": "member", "experiences": "experience"}
    validate_registry(state)
    mids = {m["id"] for m in state["members"]}
    for group in state["directions"]:
        if "memberIds" in group:
            raise DemoError("research.memberIds is derived; maintain experience.researchIds")
        order = group.get("memberOrder", [])
        if not isinstance(order, list) or any(not isinstance(mid, str) or mid not in mids for mid in order) or len(order) != len(set(order)):
            raise DemoError("invalid memberOrder")
    return state


def legacy_members(state):
    experiences = {e["id"]: e for e in state["experiences"]}
    result = []
    for member in state["members"]:
        e = experiences[member["displayExperienceId"]]
        result.append({**{key: member[key] for key in ("id", "name", "url") if key in member},
                       **{key: e[key] for key in ("role", "status", "entryYear") if key in e}})
    return result


def derived_groups(state):
    groups = copy.deepcopy(state["directions"])
    member_order = [m["id"] for m in state["members"]]
    for group in groups:
        related = {e["memberId"] for e in state["experiences"] if group["id"] in e["researchIds"]}
        order = group.get("memberOrder", []) + member_order
        group["memberIds"] = list(dict.fromkeys(mid for mid in order if mid in related))
    return groups
