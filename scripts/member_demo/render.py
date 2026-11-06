"""Server-rendered member preview; native details remain usable without JS."""
from html import escape

from .core import ROLES
from .fixtures import DIRECTIONS


def render_members(state):
    people = {person["id"]: person for person in state["members"]}
    parts = ['<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>成员展示预览</title><link rel="stylesheet" href="/style.css"></head><body class="preview-body"><a class="skip" href="#members-main">跳到成员列表</a><main id="members-main"><p class="eyebrow">MEMBERS / 测试展示</p><h1>成员展示预览</h1><p class="muted">以下均为虚构成员。应用申请后，此处会显示更新结果。</p>']

    def names(experiences, graduated=False):
        rows = []
        for experience in experiences:
            person = people[experience["memberId"]]
            name = escape(person["name"])
            if person.get("url"):
                name = f'<a href="{escape(person["url"], quote=True)}" target="_blank" rel="noopener noreferrer">{name}</a>'
            if graduated:
                suffix = {"phd": "博", "master": "硕", "postdoc": "博后"}[experience["role"]]
                year = str(experience["entryYear"])[-2:] if experience.get("entryYear") else ""
                name += f'<span class="member-label">（{year}{suffix}）</span>'
            rows.append('<span class="person-name">' + name + '</span>')
        return '<div class="names">' + ''.join(rows) + '</div>'

    groups = DIRECTIONS + [{"id": "unassigned", "title": "其他成员"}]
    for group in groups:
        items = [e for e in state["experiences"] if group["id"] in e["researchIds"] or (group["id"] == "unassigned" and not e["researchIds"])]
        if not items:
            continue
        parts.append(f'<section class="direction" id="direction-{group["id"]}"><h2>{escape(group["title"])}</h2>')
        for role in ("phd", "master", "postdoc"):
            role_items = [e for e in items if e["role"] == role]
            if not role_items:
                continue
            parts.append(f'<section class="role"><h3>{ROLES[role]}</h3>')
            current = [e for e in role_items if e["status"] == "current" and not e["graduationConfirmed"]]
            for year in sorted({e.get("entryYear") for e in current}, key=lambda x: x or 0, reverse=True):
                caption = f'{year}级' if year else '年份未补充'
                if role == "postdoc" and year:
                    caption = f'{year}年入站'
                rows = [e for e in current if e.get("entryYear") == year]
                parts.append(f'<details class="year-group" open><summary>{caption}<span class="small-count">{len(rows)}</span></summary>{names(rows)}</details>')
            graduated = sorted([e for e in role_items if e["graduationConfirmed"]], key=lambda e: e.get("entryYear", 0), reverse=True)
            if graduated:
                parts.append(f'<details class="year-group graduates"><summary>已毕业<span class="small-count">{len(graduated)}</span></summary>{names(graduated, True)}</details>')
            other = sorted([e for e in role_items if e["status"] == "former" and not e["graduationConfirmed"]], key=lambda e: e.get("entryYear", 0), reverse=True)
            if other:
                # A known former member is retained, without inventing graduation.
                parts.append(f'<details class="year-group former"><summary>往届成员<span class="small-count">{len(other)}</span></summary>{names(other, True)}</details>')
            parts.append('</section>')
        parts.append('</section>')
    parts.append('</main></body></html>')
    return ''.join(parts)
