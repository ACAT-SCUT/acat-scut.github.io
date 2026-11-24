"""Review CSV -> preview receipt -> explicit application, with local recovery."""
import argparse
from contextlib import contextmanager
import copy
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import tempfile
import uuid

from member_demo.core import DemoError, KINDS, ROLES, fingerprint, normalize_request, now, propose
from member_registry import REGISTRY_FILES, load_registry, validate_registry

ROOT = Path(__file__).resolve().parents[1]
COLUMNS = {"申请编号", "申请类型", "姓名", "身份", "定位身份", "入学年份", "定位年份", "研究方向", "个人主页", "修改字段", "新值", "明确清空", "确认毕业", "审核结果", "匹配人员编号", "匹配经历编号", "审核备注", "申请内容", "提交时间", "应用时间", "数据用途"}
FIELD_NAMES = {"姓名": "name", "个人主页": "url", "身份": "role", "入学年份": "entryYear", "研究方向": "researchIds"}


def text_json(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def checked_directory(value):
    directory = Path(value).resolve()
    if directory != ROOT / "content" and not directory.is_relative_to(ROOT / ".local"):
        raise DemoError("数据目录须为本项目 content/ 或 .local/ 中的测试副本")
    return directory


def runtime(directory):
    directory = checked_directory(directory)
    result = ROOT / ".local/member-maintenance" / hashlib.sha256(str(directory).encode()).hexdigest()[:16]
    result.mkdir(parents=True, exist_ok=True)
    return result


def source_hash(state):
    return fingerprint({key: state[key] for key in ("members", "experiences", "directions")})


def role_value(value):
    reverse = {label: key for key, label in ROLES.items()}
    reverse.update({"博士生": "phd", "硕士生": "master"})
    return reverse.get(value, value)


def direction_values(value, state):
    names = {g["title"]: g["id"] for g in state["directions"]}
    return [names.get(x.strip(), x.strip()) for x in re.split(r"[;；、]", value) if x.strip()]


def parse_payload(row, state):
    if row.get("申请内容"):
        try:
            payload = json.loads(row["申请内容"])
        except ValueError as error:
            raise DemoError("申请内容JSON不正确") from error
    else:
        kind = {label: key for key, label in KINDS.items()}.get(row.get("申请类型"), row.get("申请类型"))
        payload = {"kind": kind, "name": row.get("姓名", ""), "role": role_value(row.get("身份") or row.get("定位身份", "")), "entryYear": row.get("入学年份") or row.get("定位年份", "")}
        if kind == "graduate":
            payload["graduationAcknowledged"] = row.get("确认毕业", "").lower() in ("是", "确认", "yes", "true", "1")
        elif kind == "add":
            payload.update(researchIds=direction_values(row.get("研究方向", ""), state), url=row.get("个人主页", ""))
        elif kind == "update":
            field = FIELD_NAMES.get(row.get("修改字段"), row.get("修改字段"))
            if field not in ("name", "url", "role", "entryYear", "researchIds"):
                raise DemoError("请选择一个支持的修改字段")
            clear = row.get("明确清空", "").lower() in ("是", "yes", "true", "1", "__clear__")
            value = row.get("新值", "")
            if field == "researchIds":
                value = direction_values(value, state)
            if field == "role":
                value = role_value(value)
            payload.update(changes={} if clear else {field: value}, clearFields=[field] if clear else [])
    return normalize_request(payload, state["directions"])


def prepare_import(state, csv_path, ledger=None):
    original = copy.deepcopy(state)
    updated = copy.deepcopy(state)
    ledger = copy.deepcopy(ledger or {"requests": {}})
    result = {"beforeHash": source_hash(state), "csvHash": hashlib.sha256(Path(csv_path).read_bytes()).hexdigest(), "changes": [], "skipped": [], "requests": []}
    seen = set()
    with Path(csv_path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames or []
        if "id" in fields and "申请类型" not in fields:
            raise DemoError("旧成员CSV不能直接应用到多经历数据；请使用新的成员变更申请模板，并明确审核结果")
        if len(fields) != len(set(fields)) or set(fields) - COLUMNS or not {"审核结果"}.issubset(fields):
            raise DemoError("CSV须包含审核结果，且仅包含模板规定的列")
        for line, raw in enumerate(reader, 2):
            if None in raw or any(value is None for value in raw.values()):
                raise DemoError(f"第{line}行列数不匹配")
            row = {key: value.strip() for key, value in raw.items()}
            if not any(row.values()):
                continue
            label = row.get("申请编号") or f"第{line}行"
            if row.get("审核结果") not in ("通过", "approved"):
                result["skipped"].append({"requestId": label, "reason": "待核对、退回或未明确通过"})
                continue
            if row.get("数据用途") == "演示":
                raise DemoError("演示申请不能导入正式资料，请使用正式变更申请模板")
            try:
                payload = parse_payload(row, updated)
            except DemoError as error:
                if "请填写至少一项修改" in str(error):
                    result["skipped"].append({"requestId": label, "reason": "空白修改保留原值"})
                    continue
                raise DemoError(f"{label}：{error}") from error
            target = None
            if row.get("匹配人员编号") or row.get("匹配经历编号"):
                target = {"memberId": row.get("匹配人员编号", ""), "experienceId": row.get("匹配经历编号", "")}
                if any(str(value).startswith("demo-") for value in target.values()):
                    raise DemoError("演示数据的人员／经历编号不能应用到正式资料")
            digest = fingerprint({"payload": payload, "target": target})
            request_id = row.get("申请编号") or "request-" + digest[:20]
            if request_id in seen:
                raise DemoError("同批申请编号重复：" + request_id)
            seen.add(request_id)
            applied = ledger["requests"].get(request_id)
            if applied:
                if applied["digest"] != digest:
                    raise DemoError("申请编号已用于其他内容：" + request_id)
                result["skipped"].append({"requestId": request_id, "reason": "已应用，不重复写入"})
                continue
            request = {"id": request_id, "payload": payload, "review": "approved", "target": target}
            try:
                updated, changes = propose(updated, request)
            except DemoError as error:
                if "与现有资料一致" in str(error) or "已确认毕业" in str(error):
                    result["skipped"].append({"requestId": request_id, "reason": "资料已符合申请，无需修改"})
                    continue
                raise DemoError(f"{request_id}：{error}") from error
            validate_registry(updated)
            result["changes"].append({"requestId": request_id, "name": payload["name"], "changes": changes})
            result["requests"].append({"id": request_id, "digest": digest, "reviewNote": row.get("审核备注", "")})
    assert original == state, "Preview must not mutate input"
    result["updated"] = updated
    return result


def expected_targets(directory):
    return {**{name: directory / name for name in REGISTRY_FILES.values()}, "ledger.json": runtime(directory) / "ledger.json"}


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def restore_entries(directory, batch, manifest):
    targets = expected_targets(directory)
    if manifest["directory"] != str(directory):
        raise DemoError("备份与当前数据目录不匹配")
    contents = {}
    for name, entry in manifest["files"].items():
        if name not in targets:
            raise DemoError("备份文件范围不正确")
        if entry["before"] is None:
            contents[name] = None
        else:
            raw = (batch / (name + ".before")).read_bytes()
            if hashlib.sha256(raw).hexdigest() != entry["before"]:
                raise DemoError("备份哈希不匹配")
            contents[name] = raw
    for name, raw in contents.items():
        if raw is None:
            targets[name].unlink(missing_ok=True)
        else:
            targets[name].write_bytes(raw)


def recover_pending(directory):
    directory = checked_directory(directory)
    batches = runtime(directory) / "batches"
    if not batches.exists():
        return
    targets = expected_targets(directory)
    for manifest_path in sorted(batches.glob("*/manifest.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest["status"] != "prepared":
            continue
        for name, entry in manifest["files"].items():
            if name not in targets or file_hash(targets[name]) not in (entry["before"], entry["after"]):
                raise DemoError("待恢复事务与当前文件有冲突，请先保留当前文件并人工核对")
        restore_entries(directory, manifest_path.parent, manifest)
        manifest.update(status="recovered", recoveredAt=now())
        manifest_path.write_text(text_json(manifest), encoding="utf-8", newline="\n")


def apply_import(directory, plan):
    directory = checked_directory(directory)
    current = load_registry(directory)
    if source_hash(current) != plan["beforeHash"]:
        raise DemoError("正式资料已变化，请重新预览")
    if not plan["requests"]:
        return None
    validate_registry(plan["updated"])
    work = runtime(directory)
    ledger_path = work / "ledger.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8")) if ledger_path.exists() else {"requests": {}}
    for request in plan["requests"]:
        if request["id"] in ledger["requests"]:
            raise DemoError("申请记录已变化，请重新预览")
        ledger["requests"][request["id"]] = {**request, "appliedAt": now()}
    outputs = {"members.json": plan["updated"]["members"], "member-experiences.json": plan["updated"]["experiences"], "ledger.json": ledger}
    targets = expected_targets(directory)
    batch_id = uuid.uuid4().hex
    batch = work / "batches" / batch_id
    batch.mkdir(parents=True)
    manifest = {"directory": str(directory), "status": "prepared", "createdAt": now(), "files": {}, "changes": plan["changes"]}
    staged = {}
    for name, value in outputs.items():
        target = targets[name]
        before = target.read_bytes() if target.exists() else None
        after = text_json(value).encode("utf-8")
        if before == after:
            continue
        if before is not None:
            (batch / (name + ".before")).write_bytes(before)
        (batch / (name + ".after")).write_bytes(after)
        manifest["files"][name] = {"before": hashlib.sha256(before).hexdigest() if before is not None else None, "after": hashlib.sha256(after).hexdigest()}
    manifest_path = batch / "manifest.json"
    manifest_path.write_text(text_json(manifest), encoding="utf-8", newline="\n")
    try:
        for name in manifest["files"]:
            target = targets[name]
            with tempfile.NamedTemporaryFile(dir=target.parent, prefix=".member-update-", delete=False) as stream:
                staged[name] = Path(stream.name)
                stream.write((batch / (name + ".after")).read_bytes())
                stream.flush(); os.fsync(stream.fileno())
        # Check once more immediately before replacing any file.
        if source_hash(load_registry(directory)) != plan["beforeHash"]:
            raise DemoError("资料已变化，请重新预览")
        for name, entry in manifest["files"].items():
            if file_hash(targets[name]) != entry["before"]:
                raise DemoError("文件在应用前发生变化，请重新预览")
        for name in manifest["files"]:
            os.replace(staged[name], targets[name])
        manifest.update(status="committed", completedAt=now())
        manifest_path.write_text(text_json(manifest), encoding="utf-8", newline="\n")
    except Exception:
        # Only restore when replacements began; preflight conflicts must never
        # overwrite work made by another maintainer.
        replaced = [name for name, path in staged.items() if not path.exists()]
        if replaced:
            restore_entries(directory, batch, manifest)
        manifest.update(status="failed", failedAt=now())
        manifest_path.write_text(text_json(manifest), encoding="utf-8", newline="\n")
        raise
    finally:
        for path in staged.values():
            path.unlink(missing_ok=True)
    return batch_id


def restore_batch(directory, batch_id):
    directory = checked_directory(directory)
    if not re.fullmatch(r"[a-f0-9]{32}", batch_id):
        raise DemoError("恢复批次编号不正确")
    batch = runtime(directory) / "batches" / batch_id
    manifest_path = batch / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["status"] != "committed":
        raise DemoError("只能恢复已成功应用且尚未恢复的批次")
    targets = expected_targets(directory)
    for name, entry in manifest["files"].items():
        if name not in targets or file_hash(targets[name]) != entry["after"]:
            raise DemoError("批次之后已有其他修改，不能整批恢复覆盖，请人工核对")
    restore_entries(directory, batch, manifest)
    manifest.update(status="restored", restoredAt=now())
    manifest_path.write_text(text_json(manifest), encoding="utf-8", newline="\n")


@contextmanager
def exclusive(directory):
    """One command at a time per content directory; OS releases locks on exit."""
    with (runtime(directory) / "command.lock").open("a+b") as lock:
        lock.seek(0, 2)
        if lock.tell() == 0:
            lock.write(b"0"); lock.flush()
        lock.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            raise DemoError("另一个维护命令正在操作此数据目录，请稍后重试") from error
        try:
            yield
        finally:
            lock.seek(0)
            if os.name == "nt":
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, nargs="?", help="审核后的变更申请CSV")
    parser.add_argument("--content-dir", type=Path, default=ROOT / "content")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--restore", metavar="BATCH_ID")
    args = parser.parse_args()
    try:
        directory = checked_directory(args.content_dir)
        with exclusive(directory):
            recover_pending(directory)
            if args.restore:
                restore_batch(directory, args.restore)
                print(text_json({"mode": "restored", "batchId": args.restore}))
                return
            if not args.input:
                raise DemoError("请指定变更申请CSV")
            state = load_registry(directory)
            work = runtime(directory)
            ledger_path = work / "ledger.json"
            ledger = json.loads(ledger_path.read_text(encoding="utf-8")) if ledger_path.exists() else {"requests": {}}
            plan = prepare_import(state, args.input, ledger)
            receipt_path = work / ("preview-" + hashlib.sha256(str(args.input.resolve()).encode()).hexdigest()[:16] + ".json")
            receipt = {key: plan[key] for key in ("beforeHash", "csvHash")}
            batch = None
            if args.apply:
                if not receipt_path.exists() or json.loads(receipt_path.read_text(encoding="utf-8")) != receipt:
                    raise DemoError("请先预览当前CSV；资料或CSV已变化时须重新预览")
                batch = apply_import(directory, plan)
            else:
                receipt_path.write_text(text_json(receipt), encoding="utf-8", newline="\n")
            print(text_json({"mode": "applied" if args.apply else "preview", "batchId": batch, "changes": plan["changes"], "skipped": plan["skipped"]}))
    except (OSError, ValueError, TypeError, KeyError) as error:
        parser.exit(1, str(error) + "\n")


if __name__ == "__main__":
    main()
