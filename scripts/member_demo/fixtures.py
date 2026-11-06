"""Fictional people only; no reads from the website's real content."""

DIRECTIONS = [
    {"id": "power", "title": "数据中心节能与绿色计算"},
    {"id": "scheduling", "title": "算力优化和算电协同"},
    {"id": "llm", "title": "大模型优化与应用"},
    {"id": "ts", "title": "时序预测模型与应用"},
    {"id": "fl", "title": "边缘智能与联邦学习"},
]


def seed_state():
    return {
        "schemaVersion": 1,
        "members": [
            {"id": "demo-person-001", "name": "示例同学甲", "url": "https://example.org/", "displayExperienceId": "demo-exp-002"},
            {"id": "demo-person-002", "name": "示例同学乙", "displayExperienceId": "demo-exp-003"},
            {"id": "demo-person-003", "name": "示例同学丙", "displayExperienceId": "demo-exp-004"},
            {"id": "demo-person-004", "name": "示例博士后丁", "displayExperienceId": "demo-exp-005"},
        ],
        "experiences": [
            {"id": "demo-exp-001", "memberId": "demo-person-001", "role": "master", "entryYear": 2021, "status": "former", "graduationConfirmed": False, "researchIds": ["power"]},
            {"id": "demo-exp-002", "memberId": "demo-person-001", "role": "phd", "entryYear": 2024, "status": "current", "graduationConfirmed": False, "researchIds": ["power"]},
            {"id": "demo-exp-003", "memberId": "demo-person-002", "role": "master", "entryYear": 2025, "status": "current", "graduationConfirmed": False, "researchIds": ["ts"]},
            {"id": "demo-exp-004", "memberId": "demo-person-003", "role": "master", "entryYear": 2024, "status": "current", "graduationConfirmed": False, "researchIds": ["power", "ts"]},
            {"id": "demo-exp-005", "memberId": "demo-person-004", "role": "postdoc", "status": "former", "graduationConfirmed": False, "researchIds": ["fl"]},
        ],
        "requests": [], "audit": [],
    }
