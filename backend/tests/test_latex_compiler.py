"""Tests for sandboxed LaTeX compiler and diagnostics tool."""

from unittest.mock import AsyncMock, patch

import pytest

from openmlr.tools.latex_compiler import (
    compile_latex,
    create_latex_tool,
    diagnose_latex_errors,
    markdown_to_latex,
    validate_latex_syntax,
)

pytestmark = pytest.mark.asyncio


class TestValidateLatexSyntax:
    def test_valid_latex_document(self):
        tex = r"""
        \documentclass{article}
        \usepackage{amsmath}
        \begin{document}
        \section{Introduction}
        This is a test document with $x + y = z$ and balanced {braces}.
        \begin{equation}
        E = mc^2
        \end{equation}
        \end{document}
        """
        valid, errors, warnings = validate_latex_syntax(tex)
        assert valid is True
        assert len(errors) == 0

    def test_missing_documentclass(self):
        tex = r"""
        \begin{document}
        Hello
        \end{document}
        """
        valid, errors, warnings = validate_latex_syntax(tex)
        assert valid is False
        assert any("documentclass" in e for e in errors)

    def test_unclosed_environment(self):
        tex = r"""
        \documentclass{article}
        \begin{document}
        \begin{itemize}
        \item First item
        \end{document}
        """
        valid, errors, warnings = validate_latex_syntax(tex)
        assert valid is False
        assert any("Unclosed environment" in e or "itemize" in e for e in errors)

    def test_mismatched_environment(self):
        tex = r"""
        \documentclass{article}
        \begin{document}
        \begin{itemize}
        \item Item
        \end{enumerate}
        \end{document}
        """
        valid, errors, warnings = validate_latex_syntax(tex)
        assert valid is False
        assert any("Mismatched environment" in e for e in errors)

    def test_unmatched_curly_braces(self):
        tex = r"""
        \documentclass{article}
        \begin{document}
        \textbf{Unclosed brace
        \end{document}
        """
        valid, errors, warnings = validate_latex_syntax(tex)
        assert valid is False
        assert any("curly braces" in e for e in errors)


class TestDiagnoseLatexErrors:
    def test_diagnose_missing_package(self):
        log = """
        This is pdfTeX, Version 3.141592653-2.6-1.40.24
        ! LaTeX Error: File `tcolorbox.sty' not found.
        Type X to quit or <RETURN> to proceed.
        """
        diag = diagnose_latex_errors(log)
        assert "tcolorbox" in diag["missing_packages"]
        assert any("tcolorbox" in fix for fix in diag["suggested_fixes"])

    def test_diagnose_undefined_control_sequence(self):
        log = """
        ! Undefined control sequence.
        l.12 \\customCommand
                           {arg}
        """
        diag = diagnose_latex_errors(log)
        assert len(diag["errors"]) > 0
        assert any("customCommand" in fix for fix in diag["suggested_fixes"])

    def test_diagnose_missing_citations(self):
        log = """
        LaTeX Warning: Citation 'vaswani2017' on page 1 undefined on input line 42.
        """
        diag = diagnose_latex_errors(log)
        assert "vaswani2017" in diag["missing_citations"]
        assert any("vaswani2017" in fix for fix in diag["suggested_fixes"])


class TestMarkdownToLatex:
    def test_converts_headers_and_citations(self):
        md = """
        # My Paper Title
        ## Introduction
        Deep learning works well [@lecun2015].
        ### Background
        **Bold text** and *italic text*.
        """
        author_info = {
            "name": "Dr. Research",
            "affiliation": "AI Lab",
            "email": "dr@example.com",
        }
        tex = markdown_to_latex(md, title="My Paper Title", author_info=author_info, bib_content="dummy")
        assert r"\documentclass" in tex
        assert r"\title{My Paper Title}" in tex
        assert "Dr. Research" in tex
        assert r"\section{Introduction}" in tex
        assert r"\subsubsection{Background}" in tex
        assert r"\cite{lecun2015}" in tex
        assert r"\textbf{Bold text}" in tex
        assert r"\textit{italic text}" in tex
        assert r"\bibliography{references}" in tex


class TestCompileLatex:
    async def test_compile_syntax_failure(self):
        invalid_tex = "Not a latex doc"
        res = await compile_latex(invalid_tex)
        assert res.success is False
        assert res.engine_used == "static-validator"
        assert len(res.errors) > 0

    async def test_compile_static_pass_when_no_engine(self):
        valid_tex = r"""
        \documentclass{article}
        \begin{document}
        Hello World
        \end{document}
        """
        with patch("openmlr.tools.latex_compiler.get_available_latex_engine", return_value=None):
            res = await compile_latex(valid_tex)
            assert res.success is True
            assert res.engine_used == "static-validator"
            assert "Static syntax analysis passed" in res.log

    async def test_compile_with_tectonic_engine_mock(self, tmp_path):
        valid_tex = r"""
        \documentclass{article}
        \begin{document}
        Hello World
        \end{document}
        """
        fake_pdf = tmp_path / "document.pdf"
        fake_pdf.write_bytes(b"%PDF-1.5 test")

        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"Tectonic finished", b"")
        mock_proc.returncode = 0

        with patch("openmlr.tools.latex_compiler.get_available_latex_engine", return_value="tectonic"):
            with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
                res = await compile_latex(valid_tex, work_dir=tmp_path)
                assert res.success is True
                assert res.pdf_bytes is not None


class TestLatexCompilerTool:
    def test_creates_tool(self):
        tool = create_latex_tool()
        assert tool.name == "latex_compiler"
        assert "operation" in tool.parameters["required"]
        ops = tool.parameters["properties"]["operation"]["enum"]
        assert "compile" in ops
        assert "validate" in ops
        assert "convert_markdown" in ops
        assert "check_engine" in ops

    async def test_tool_handler_check_engine(self):
        tool = create_latex_tool()
        assert tool.handler is not None
        result, ok = await tool.handler("check_engine")
        assert ok is True
        assert "LaTeX compiler" in result or "No headless" in result

    async def test_tool_handler_validate(self):
        tool = create_latex_tool()
        assert tool.handler is not None
        valid_tex = r"""
        \documentclass{article}
        \begin{document}
        Testing
        \end{document}
        """
        result, ok = await tool.handler("validate", tex_content=valid_tex)
        assert ok is True
        assert "LaTeX Syntax Valid: True" in result

    async def test_tool_handler_convert_markdown(self):
        tool = create_latex_tool()
        assert tool.handler is not None
        md = "## Intro\nText here."
        result, ok = await tool.handler("convert_markdown", markdown_content=md, title="Test")
        assert ok is True
        assert r"\documentclass" in result
        assert r"\section{Intro}" in result
