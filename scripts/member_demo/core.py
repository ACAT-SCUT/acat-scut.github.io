"""Request/review logic, independent of HTTP and of the real site's data."""
import copy
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import threading
from urllib.parse import urlparse
import uuid

from .fixtures import DIRECTIONS, seed_state

ROLES = {"phd": "博士", "master": "硕士", "postdoc": "博士后"}
KINDS = {"add": "新增经历", "update": "修改资料", "graduate": "申请毕业"}
REVIEWS = {"pending": "待核对", "approved": "通过", "rejected": "退回"}
DIRECTION_MAP = {item["id"]: item["title"] for item in DIRECTIONS}
ROOT = Path(__file__).resolve().parents[2]


class DemoError(ValueError):
    pass


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def registry(state):
    return {key: state[key] for key in ("members", "experiences")}


def clean_text(value, label, required=False):
    if not isinstance(value, str) or len(value) > 500:
        raise DemoError(label + "格式不正确")
    value = value.strip()
    if required and not value:
        raise DemoError("请填写" + label)
    return value


def valid_year(value, required=True):
    if value in (None, "") and not required:
        return None
    try:
        if isinstance(value, bool):
            raise ValueError()
        year = int(value)
        if str(year) != str(value).strip() or not 1900 <= year <= 2100:
            raise ValueError()
        return year
    except (TypeError, ValueError):
        raise DemoError("年份须为1900至2100之间的四位整数") from None


def valid_url(value):
    value = clean_text(value, "个人主页")
    if value:
        parsed = urlparse(value)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise DemoError("个人主页请填写完整的 HTTPS 地址")
    return value


def valid_directions(value):
    if not isinstance(value, list) or any(not isinstance(x, str) or x not in DIRECTION_MAP for x in value):
        raise DemoError("请选择已有的研究方向")
    if len(value) != len(set(value)):
        raise DemoError("研究方向不能重复")
    return value


def validate_registry(state):
    members = state["members"]
    experiences = state["experiences"]
    mids = [m["id"] for m in members]
    eids = [e["id"] for e in experiences]
    if len(mids) != len(set(mids)) or len(eids) != len(set(eids)):
        raise DemoError("人员或经历编号重复")
    for member in members:
        clean_text(member["name"], "姓名", True)
        valid_url(member.get("url", ""))
        if not any(e["id"] == member["displayExperienceId"] and e["memberId"] == member["id"] for e in experiences):
            raise DemoError("主经历与人员不匹配")
    for experience in experiences:
        if experience["memberId"] not in mids or experience["role"] not in ROLES:
            raise DemoError("经历中的人员或身份不正确")
        valid_year(experience.get("entryYear"), experience["role"] != "postdoc")
        valid_directions(experience["researchIds"])
        if experience["status"] not in ("current", "former") or type(experience["graduationConfirmed"]) is not bool:
            raise DemoError("经历状态不正确")
        if experience["graduationConfirmed"] and (experience["role"] == "postdoc" or experience["status"] != "former"):
            raise DemoError("毕业确认仅适用于已结束的硕博经历")


def normalize_request(payload):
    if not isinstance(payload, dict):
        raise DemoError("申请内容格式不正确")
    allowed = {"kind", "name", "role", "entryYear", "researchIds", "url", "changes", "clearFields", "graduationAcknowledged"}
    if set(payload) - allowed:
        raise DemoError("申请包含不支持的字段")
    kind, role = payload.get("kind"), payload.get("role")
    if not isinstance(kind, str) or not isinstance(role, str) or kind not in KINDS or role not in ROLES:
        raise DemoError("请选择申请类型和身份")
    result = {"kind": kind, "name": clean_text(payload.get("name", ""), "姓名", True), "role": role,
              "entryYear": valid_year(payload.get("entryYear"), role != "postdoc")}
    if kind == "graduate":
        if role == "postdoc":
            raise DemoError("博士后离站不作为毕业，请使用修改资料并联系维护者确认")
        if payload.get("graduationAcknowledged") is not True:
            raise DemoError("请确认申请的是这段经历的毕业状态")
        result["graduationAcknowledged"] = True
    elif kind == "add":
        result["researchIds"] = valid_directions(payload.get("researchIds", []))
        result["url"] = valid_url(payload.get("url", ""))
    else:
        changes = payload.get("changes", {})
        clears = payload.get("clearFields", [])
        allowed_changes = {"name", "url", "role", "entryYear", "researchIds"}
        if not isinstance(changes, dict) or set(changes) - allowed_changes:
            raise DemoError("修改项不正确")
        if not isinstance(clears, list) or any(x not in ("url", "researchIds", "entryYear") for x in clears) or len(clears) != len(set(clears)):
            raise DemoError("清空项不正确")
        normalized = {}
        for key, value in changes.items():
            if value in (None, "", []):
                continue  # Blank submissions never erase existing data.
            if key in clears:
                raise DemoError("同一字段不能同时修改和清空")
            if key == "url":
                normalized[key] = valid_url(value)
            elif key == "name":
                normalized[key] = clean_text(value, "新姓名", True)
            elif key == "role":
                if not isinstance(value, str) or value not in ROLES:
                    raise DemoError("新身份不正确")
                normalized[key] = value
            elif key == "entryYear":
                normalized[key] = valid_year(value)
            else:
                normalized[key] = valid_directions(value)
        if not normalized and not clears:
            raise DemoError("请填写至少一项修改内容；空白会保留原值")
        result.update(changes=normalized, clearFields=clears)
    return result


def candidates(state, request):
    payload = request["payload"]
    matching_members = [m for m in state["members"] if m["name"] == payload["name"]]
    if payload["kind"] == "add":
        return [{"memberId": m["id"], "experienceId": "", "label": m["name"] + "（已有成员，新增一段经历）"} for m in matching_members] + [
            {"memberId": "new", "experienceId": "", "label": "新建一位成员（同名时请核实）"}]
    result = []
    for m in matching_members:
        for e in state["experiences"]:
            if e["memberId"] == m["id"] and e["role"] == payload["role"] and e.get("entryYear") == payload["entryYear"]:
                result.append({"memberId": m["id"], "experienceId": e["id"], "label": f'{m["name"]} · {e.get("entryYear") or "年份未填"} · {ROLES[e["role"]]} · ' + ("当前" if e["status"] == "current" else "往届"), "member": copy.deepcopy(m), "experience": copy.deepcopy(e)})
    return result


def new_id(rows, prefix):
    number = 1
    known = {r["id"] for r in rows}
    while f"{prefix}-{number:03d}" in known:
        number += 1
    return f"{prefix}-{number:03d}"


def choose_target(state, request, target):
    if target is not None and not isinstance(target, dict):
        raise DemoError("请选择匹配的人员与经历")
    options = candidates(state, request)
    if target:
        for option in options:
            if option["memberId"] == target.get("memberId") and option["experienceId"] == target.get("experienceId", ""):
                return {key: option[key] for key in ("memberId", "experienceId")}
        raise DemoError("选中的人员或经历与申请不匹配，请重新核对")
    existing = [option for option in options if option["memberId"] != "new"]
    if len(existing) == 1:
        return {key: existing[0][key] for key in ("memberId", "experienceId")}
    if not existing and request["payload"]["kind"] == "add":
        return {"memberId": "new", "experienceId": ""}
    raise DemoError("无法唯一匹配，请由维护者明确选择人员与经历")


def display_value(field, value):
    if value is None or value == "":
        return "未填写"
    if field == "role":
        return ROLES[value]
    if field == "status":
        return {"current": "当前", "former": "往届"}[value]
    if field == "graduationConfirmed":
        return "已确认毕业" if value else "未确认毕业"
    if field == "researchIds":
        return "、".join(DIRECTION_MAP[x] for x in value) or "未归属方向"
    return str(value)


def propose(state, request):
    if request.get("appliedAt"):
        raise DemoError("这份申请已经应用，不能重复应用")
    if request["review"] != "approved":
        raise DemoError("只有审核通过的申请才能预览或应用")
    updated = copy.deepcopy(state)
    target = choose_target(state, request, request.get("target"))
    payload = request["payload"]
    kind = payload["kind"]
    member = next((m for m in updated["members"] if m["id"] == target["memberId"]), None)
    before_member = copy.deepcopy(member)
    before_experience = None
    if kind == "add":
        if member is None:
            member = {"id": new_id(updated["members"], "demo-person"), "name": payload["name"]}
            updated["members"].append(member)
        if any(e["memberId"] == member["id"] and e["role"] == payload["role"] and e.get("entryYear") == payload["entryYear"] for e in updated["experiences"]):
            raise DemoError("该成员已有同身份、同年份的经历，请使用修改资料")
        experience = {"id": new_id(updated["experiences"], "demo-exp"), "memberId": member["id"], "role": payload["role"], "status": "current", "graduationConfirmed": False, "researchIds": payload["researchIds"]}
        if payload["entryYear"] is not None:
            experience["entryYear"] = payload["entryYear"]
        if payload.get("url"):
            member["url"] = payload["url"]
        if "displayExperienceId" not in member:
            member["displayExperienceId"] = experience["id"]
        updated["experiences"].append(experience)
    else:
        experience = next(e for e in updated["experiences"] if e["id"] == target["experienceId"])
        before_experience = copy.deepcopy(experience)
        if kind == "graduate":
            if experience["graduationConfirmed"]:
                raise DemoError("这段经历已确认毕业，无需重复申请")
            experience.update(status="former", graduationConfirmed=True)
        else:
            for key, value in payload["changes"].items():
                (member if key in ("name", "url") else experience)[key] = value
            for key in payload["clearFields"]:
                if key == "researchIds":
                    experience[key] = []
                else:
                    (member if key == "url" else experience).pop(key, None)
    validate_registry(updated)
    changes = []
    labels = {"name": "姓名（所有经历共用）", "url": "个人主页（所有经历共用）", "role": "身份", "entryYear": "入学／入站年份", "status": "所属状态", "graduationConfirmed": "毕业确认", "researchIds": "研究方向"}
    for scope, before, after, fields in (
        ("个人资料", before_member or {}, member, ("name", "url")),
        ("本段经历", before_experience or {}, experience, ("role", "entryYear", "status", "graduationConfirmed", "researchIds")),
    ):
        for field in fields:
            if before.get(field) != after.get(field):
                changes.append({"scope": scope, "field": field, "label": labels[field], "before": display_value(field, before.get(field)), "after": display_value(field, after.get(field))})
    if not changes:
        raise DemoError("申请内容与现有资料一致，无需应用")
    return updated, changes


class Store:
    """One atomic state file contains the registry, requests and audit events."""
    def __init__(self, directory):
        self.directory = Path(directory).resolve()
        local = (ROOT / ".local").resolve()
        if not self.directory.is_relative_to(local) or self.directory == local:
            raise DemoError("演示数据目录必须位于本项目 .local/ 的子目录中")
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / "state.json"
        self.lock = threading.RLock()
        if not self.path.exists():
            self._save(seed_state())
        validate_registry(self.read())

    def read(self):
        with self.lock:
            return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, state):
        validate_registry(state)
        raw = json.dumps(state, ensure_ascii=False, indent=2) + "\n"
        old = self.path.read_bytes() if self.path.exists() else None
        temp = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=self.directory, prefix=".state-", delete=False) as stream:
                temp = Path(stream.name)
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            if old is not None:
                backup_dir = self.directory / "backups"
                backup_dir.mkdir(exist_ok=True)
                (backup_dir / (uuid.uuid4().hex + ".json")).write_bytes(old)
            os.replace(temp, self.path)
        finally:
            if temp is not None:
                temp.unlink(missing_ok=True)

    def public_state(self):
        state = self.read()
        for request in state["requests"]:
            request["candidates"] = candidates(state, request)
            request.pop("preview", None)
        return {**state, "directions": DIRECTIONS, "roles": ROLES, "kinds": KINDS, "reviews": REVIEWS}

    def submit(self, payload):
        payload = normalize_request(payload)
        with self.lock:
            state = self.read()
            request = {"id": "申请-" + str(len(state["requests"]) + 1).zfill(3), "payload": payload, "review": "pending", "submittedAt": now(), "reviewNote": "", "target": None}
            state["requests"].append(request)
            self._save(state)
            return copy.deepcopy(request)

    @staticmethod
    def _request(state, request_id):
        for request in state["requests"]:
            if request["id"] == request_id:
                return request
        raise DemoError("未找到这份申请，请刷新列表")

    def review(self, request_id, decision, note="", target=None):
        if not isinstance(decision, str) or decision not in REVIEWS:
            raise DemoError("审核状态不正确")
        note = clean_text(note, "审核备注")
        with self.lock:
            state = self.read()
            request = self._request(state, request_id)
            if request.get("appliedAt"):
                raise DemoError("已应用的申请不能再次审核")
            request.update(review=decision, reviewNote=note, reviewedAt=now())
            request.pop("preview", None)
            if decision == "approved":
                request["target"] = choose_target(state, request, target)
                propose(state, request)
            else:
                request["target"] = None
            state["audit"].append({"action": "review", "requestId": request_id, "decision": decision, "at": now()})
            self._save(state)
            return copy.deepcopy(request)

    def preview(self, request_id):
        with self.lock:
            state = self.read()
            request = self._request(state, request_id)
            _, changes = propose(state, request)
            token = uuid.uuid4().hex
            request["preview"] = {"token": token, "registryHash": fingerprint(registry(state)), "changes": changes}
            self._save(state)
            return {"token": token, "changes": changes, "requestId": request_id}

    def apply(self, request_id, token):
        with self.lock:
            state = self.read()
            request = self._request(state, request_id)
            if request.get("appliedAt"):
                raise DemoError("这份申请已经应用，不能重复应用")
            preview = request.get("preview")
            if not preview or not token or token != preview["token"]:
                raise DemoError("请先查看修改预览，再应用")
            if fingerprint(registry(state)) != preview["registryHash"]:
                raise DemoError("测试资料已变化，请重新预览后再应用")
            updated, changes = propose(state, request)
            updated_request = self._request(updated, request_id)
            updated_request["appliedAt"] = now()
            updated_request.pop("preview", None)
            updated["audit"].append({"action": "apply", "requestId": request_id, "changes": changes, "at": now()})
            self._save(updated)
            return {"requestId": request_id, "changes": changes}

    def reset(self, confirmed=False):
        if confirmed is not True:
            raise DemoError("请先确认重置演示数据")
        with self.lock:
            self._save(seed_state())

    def export_csv(self, reviewed=False):
        state = self.read()
        out = io.StringIO(newline="")
        headers = ["申请编号", "申请类型", "姓名", "定位身份", "定位年份", "申请内容", "提交时间"]
        if reviewed:
            headers += ["审核结果", "匹配人员编号", "匹配经历编号", "审核备注", "应用时间"]
        writer = csv.writer(out, lineterminator="\n")
        writer.writerow(headers)
        for request in state["requests"]:
            p = request["payload"]
            row = [request["id"], KINDS[p["kind"]], p["name"], ROLES[p["role"]], p.get("entryYear") or "", json.dumps(p, ensure_ascii=False), request["submittedAt"]]
            if reviewed:
                target = request.get("target") or {}
                row += [REVIEWS[request["review"]], target.get("memberId", ""), target.get("experienceId", ""), request["reviewNote"], request.get("appliedAt", "")]
            # Spreadsheet programs must not interpret user-supplied text as formulas.
            row = ["'" + str(x) if str(x).lstrip().startswith(("=", "+", "-", "@")) else x for x in row]
            writer.writerow(row)
        return "\ufeff" + out.getvalue()
