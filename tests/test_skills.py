from __future__ import annotations

from tests.helpers import SKILLS
from unifi_mcp.skills import load_skills


def test_load_skills_defaults_to_read_only_without_connector_proxy() -> None:
    all_skills = load_skills(SKILLS, read_only=False, allow_connector_proxy=True)
    expected = {
        skill.name
        for skill in all_skills
        if skill.method == "GET" and not skill.is_connector_proxy
    }

    skills = load_skills(SKILLS, read_only=True, allow_connector_proxy=False)

    assert {skill.name for skill in skills} == expected
    assert all(skill.method == "GET" for skill in skills)
    assert all(not skill.is_connector_proxy for skill in skills)


def test_load_skills_can_include_connector_get_in_read_only_mode() -> None:
    all_skills = load_skills(SKILLS, read_only=False, allow_connector_proxy=True)
    expected = {skill.name for skill in all_skills if skill.method == "GET"}

    skills = load_skills(SKILLS, read_only=True, allow_connector_proxy=True)

    assert {skill.name for skill in skills} == expected
    assert all(skill.method == "GET" for skill in skills)
    assert any(skill.is_connector_proxy for skill in skills)


def test_load_skills_can_include_write_tools_when_enabled() -> None:
    all_skills = load_skills(SKILLS, read_only=False, allow_connector_proxy=True)

    skills = load_skills(SKILLS, read_only=False, allow_connector_proxy=True)

    assert {skill.name for skill in skills} == {skill.name for skill in all_skills}
    assert any(skill.method != "GET" for skill in skills)
