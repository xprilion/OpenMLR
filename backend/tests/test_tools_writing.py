"""Tests for writing tool — project management and paper operations."""

import pytest

from openmlr.tools.writing import (
    _add_citation,
    _count_sections,
    _create_project,
    _get_draft,
    _get_draft_from_proj,
    _list_sections,
    _refine_section,
    _set_outline,
    _write_section,
    create_writing_tool,
)

pytestmark = pytest.mark.asyncio


class TestCreateWritingTool:
    async def test_creates_tool(self):
        tool = create_writing_tool()
        assert tool.name == "writing"
        assert tool.handler is not None
        assert "operation" in tool.parameters["required"]
        ops = tool.parameters["properties"]["operation"]["enum"]
        assert "create_project" in ops
        assert "write_section" in ops
        assert "get_draft" in ops


class TestCreateProject:
    async def test_creates_project(self):
        from openmlr.tools.writing import _projects
        _projects.clear()
        result, ok = _create_project(conv_id=1, title="My Paper")
        assert ok is True
        assert "My Paper" in result
        proj = _projects.get(1)
        assert proj is not None
        assert proj["title"] == "My Paper"
        _projects.clear()

    async def test_requires_title(self):
        result, ok = _create_project(conv_id=1, title="")
        assert ok is False
        assert "title" in result.lower()


class TestSetOutline:
    async def test_no_project(self):
        from openmlr.tools.writing import _projects
        _projects.clear()
        result, ok = _set_outline(conv_id=999, outline=[])
        assert ok is False
        assert "No paper project" in result

    async def test_requires_outline(self):
        from openmlr.tools.writing import _projects
        _projects.clear()
        _create_project(conv_id=1, title="Test")
        result, ok = _set_outline(conv_id=1, outline=None)
        assert ok is False
        _projects.clear()

    async def test_sets_outline(self):
        from openmlr.tools.writing import _projects
        _projects.clear()
        _create_project(conv_id=1, title="Test")
        outline = [
            {"id": "sec1", "title": "Introduction"},
            {"id": "sec2", "title": "Methods", "subsections": [
                {"id": "sec2.1", "title": "Setup"},
            ]},
        ]
        result, ok = _set_outline(conv_id=1, outline=outline)
        assert ok is True
        assert "Introduction" in result
        assert "Methods" in result
        assert "Setup" in result
        _projects.clear()


class TestWriteSection:
    async def test_no_project(self):
        from openmlr.tools.writing import _projects
        _projects.clear()
        result, ok = _write_section(conv_id=999, section_id="s1", content="text")
        assert ok is False

    async def test_writes_section(self):
        from openmlr.tools.writing import _projects
        _projects.clear()
        _create_project(conv_id=1, title="Test")
        _set_outline(conv_id=1, outline=[{"id": "intro", "title": "Introduction"}])
        result, ok = _write_section(conv_id=1, section_id="intro", content="Hello world.")
        assert ok is True
        assert "intro" in result
        assert "auto-saved" in result
        _projects.clear()


class TestGetDraft:
    async def test_no_project(self):
        from openmlr.tools.writing import _projects
        _projects.clear()
        result, ok = await _get_draft(conv_id=999)
        assert ok is False

    async def test_generates_draft(self):
        from openmlr.tools.writing import _projects
        _projects.clear()
        _create_project(conv_id=1, title="The Paper")
        _set_outline(conv_id=1, outline=[{"id": "intro", "title": "Introduction"}])
        _write_section(conv_id=1, section_id="intro", content="This is the intro.")
        result, ok = await _get_draft(conv_id=1)
        assert ok is True
        assert "# The Paper" in result
        assert "Introduction" in result
        assert "This is the intro." in result
        _projects.clear()


class TestGetDraftFromProj:
    async def test_generates_full_draft(self):
        proj = {
            "title": "ML Research",
            "outline": [
                {"id": "abstract", "title": "Abstract"},
                {"id": "method", "title": "Method", "subsections": [
                    {"id": "method.experimental", "title": "Experimental Setup"},
                ]},
            ],
            "sections": {
                "abstract": "This is the abstract.",
                "method": "The method section.",
                "method.experimental": "Experimental details.",
            },
            "bibliography": [
                {"key": "doe2024", "author": "J. Doe", "title": "Great Paper", "year": "2024"},
            ],
        }
        result, ok = _get_draft_from_proj(proj)
        assert ok is True
        assert "ML Research" in result
        assert "Abstract" in result
        assert "Method" in result
        assert "Experimental Setup" in result
        assert "References" in result
        assert "J. Doe" in result


class TestListSections:
    async def test_no_project(self):
        from openmlr.tools.writing import _projects
        _projects.clear()
        result, ok = _list_sections(conv_id=999)
        assert ok is False
        assert "No paper project" in result

    async def test_lists_sections_with_status(self):
        from openmlr.tools.writing import _projects
        _projects.clear()
        _create_project(conv_id=1, title="Test")
        _set_outline(conv_id=1, outline=[
            {"id": "s1", "title": "Section 1"},
            {"id": "s2", "title": "Section 2"},
        ])
        _write_section(conv_id=1, section_id="s1", content="written")
        result, ok = _list_sections(conv_id=1)
        assert ok is True
        assert "[done]" in result
        assert "[pending]" in result
        _projects.clear()


class TestAddCitation:
    async def test_adds_citation(self):
        from openmlr.tools.writing import _projects
        _projects.clear()
        _create_project(conv_id=1, title="Test")
        citation = {
            "key": "smith2023",
            "title": "Important Paper",
            "author": "A. Smith",
            "year": "2023",
        }
        result, ok = _add_citation(conv_id=1, citation=citation)
        assert ok is True
        assert "Added citation" in result
        _projects.clear()


class TestRefineSection:
    async def test_returns_feedback_mode(self):
        from openmlr.tools.writing import _projects
        _projects.clear()
        _create_project(conv_id=1, title="Test")
        _set_outline(conv_id=1, outline=[{"id": "s1", "title": "Section"}])
        _write_section(conv_id=1, section_id="s1", content="original content")
        result, ok = _refine_section(
            conv_id=1, section_id="s1",
            content=None, feedback="make it better",
        )
        assert ok is True
        assert "feedback" in result.lower()
        _projects.clear()


class TestCountSections:
    async def test_counts_with_subsections(self):
        outline = [
            {"id": "a", "title": "A"},
            {"id": "b", "title": "B", "subsections": [
                {"id": "b1", "title": "B1"},
                {"id": "b2", "title": "B2"},
            ]},
        ]
        assert _count_sections(outline) == 4

    async def test_empty_outline(self):
        assert _count_sections([]) == 0
