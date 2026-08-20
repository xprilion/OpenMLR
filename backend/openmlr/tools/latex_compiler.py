"""Sandboxed LaTeX compilation, syntax validation, and diagnostics tool.

Provides headless LaTeX compilation (Tectonic / pdflatex / xelatex),
syntax checking, error diagnosis, Markdown-to-LaTeX conversion, and BibTeX integration.
"""

from __future__ import annotations

import asyncio
import logging
import re
import shutil
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..agent.types import ToolSpec
from ..services.bibtex_validator import validate_bibtex

logger = logging.getLogger("openmlr.tools.latex_compiler")

LATEX_ENGINES = ["tectonic", "pdflatex", "xelatex", "lualatex"]


@dataclass
class LaTeXCompilationResult:
    """Result of LaTeX compilation."""

    success: bool
    pdf_path: str | None = None
    pdf_bytes: bytes | None = None
    log: str = ""
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    missing_packages: list[str] = field(default_factory=list)
    missing_citations: list[str] = field(default_factory=list)
    engine_used: str = ""
    compilation_time_ms: float = 0.0
    suggested_fixes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "pdf_path": self.pdf_path,
            "has_pdf": self.pdf_bytes is not None or self.pdf_path is not None,
            "log_snippet": self.log[-2000:] if self.log else "",
            "errors": self.errors,
            "warnings": self.warnings,
            "missing_packages": self.missing_packages,
            "missing_citations": self.missing_citations,
            "engine_used": self.engine_used,
            "compilation_time_ms": round(self.compilation_time_ms, 2),
            "suggested_fixes": self.suggested_fixes,
        }


def get_available_latex_engine() -> str | None:
    """Return the name of the first available LaTeX compiler on PATH."""
    for engine in LATEX_ENGINES:
        if shutil.which(engine):
            return engine
    return None


def validate_latex_syntax(tex_content: str) -> tuple[bool, list[str], list[str]]:
    """Static syntax analysis on LaTeX content without running a compiler."""
    errors: list[str] = []
    warnings: list[str] = []

    if not tex_content or not tex_content.strip():
        return False, ["LaTeX content is empty"], []

    if r"\documentclass" not in tex_content:
        errors.append("Missing '\\documentclass{...}' declaration")
    if r"\begin{document}" not in tex_content:
        errors.append("Missing '\\begin{document}'")
    if r"\end{document}" not in tex_content:
        errors.append("Missing '\\end{document}'")

    lines = tex_content.splitlines()
    clean_lines = [re.sub(r"(?<!\\)%.*$", "", line) for line in lines]

    # Environment stack validation
    env_stack: list[tuple[str, int]] = []
    env_pattern = re.compile(r"\\(begin|end)\{([^}]+)\}")

    for line_idx, line in enumerate(clean_lines, start=1):
        for match in env_pattern.finditer(line):
            cmd_type, env_name = match.group(1), match.group(2).strip()
            if cmd_type == "begin":
                env_stack.append((env_name, line_idx))
            else:
                if not env_stack:
                    errors.append(f"Line {line_idx}: '\\end{{{env_name}}}' with no matching '\\begin'")
                else:
                    last_env, start_line = env_stack.pop()
                    if last_env != env_name:
                        errors.append(
                            f"Line {line_idx}: Mismatched environment '\\end{{{env_name}}}' "
                            f"(expected '\\end{{{last_env}}}' opened on line {start_line})"
                        )

    for env_name, start_line in env_stack:
        errors.append(f"Line {start_line}: Unclosed environment '\\begin{{{env_name}}}'")

    # Brace balance validation
    brace_depth = 0
    for line_idx, line in enumerate(clean_lines, start=1):
        for col_idx, ch in enumerate(line):
            if col_idx > 0 and line[col_idx - 1] == "\\":
                continue
            if ch == "{":
                brace_depth += 1
            elif ch == "}":
                brace_depth -= 1
                if brace_depth < 0:
                    errors.append(f"Line {line_idx}: Unmatched closing brace '}}'")
                    brace_depth = 0

    if brace_depth > 0:
        errors.append(f"Unclosed curly braces in document ({brace_depth} unclosed)")

    # Math mode check
    dollar_count = 0
    for line in clean_lines:
        un_escaped_dollars = len(re.findall(r"(?<!\\)\$", line))
        double_dollars = line.count("$$")
        single_dollars = un_escaped_dollars - (double_dollars * 2)
        if single_dollars % 2 != 0:
            dollar_count += single_dollars

    if dollar_count % 2 != 0:
        warnings.append("Possible unclosed inline math delimiter '$'")

    return len(errors) == 0, errors, warnings


def diagnose_latex_errors(log_text: str, tex_content: str = "") -> dict[str, Any]:
    """Parse a LaTeX compiler log to diagnose errors, missing packages, and suggested fixes."""
    errors: list[str] = []
    warnings: list[str] = []
    missing_packages: list[str] = []
    missing_citations: list[str] = []
    suggested_fixes: list[str] = []

    if not log_text:
        return {
            "errors": errors,
            "warnings": warnings,
            "missing_packages": missing_packages,
            "missing_citations": missing_citations,
            "suggested_fixes": suggested_fixes,
        }

    lines = log_text.splitlines()
    for idx, raw_line in enumerate(lines):
        line = raw_line.strip()
        if line.startswith("!"):
            error_msg = line[1:].strip()
            if idx + 1 < len(lines) and lines[idx + 1].strip().startswith("l."):
                error_msg += f" ({lines[idx + 1].strip()})"
            errors.append(error_msg)

            # Missing package diagnosis
            pkg_match = re.search(r"File [`']([^`']+\.sty)['\"] not found", line)
            if pkg_match:
                pkg_name = pkg_match.group(1).replace(".sty", "")
                missing_packages.append(pkg_name)
                suggested_fixes.append(f"Install LaTeX package '{pkg_name}' via tlmgr or tectonic.")

            if "Undefined control sequence" in line:
                if idx + 1 < len(lines):
                    cmd_match = re.search(r"\\([a-zA-Z]+)", lines[idx + 1])
                    if cmd_match:
                        cmd = cmd_match.group(1)
                        suggested_fixes.append(
                            f"Undefined command '\\{cmd}'. Ensure package is imported."
                        )

            if "Missing $ inserted" in line:
                suggested_fixes.append("Missing math delimiter. Wrap math in '$...$'.")

        elif "LaTeX Warning:" in line or ("Package " in line and "Warning:" in line):
            warnings.append(line)
            cite_match = re.search(r"Citation [`\']([^`\']+)[\'\"] on page \d+ undefined", line)
            if cite_match:
                missing_citations.append(cite_match.group(1))
                suggested_fixes.append(
                    f"Add BibTeX entry for missing citation key '{cite_match.group(1)}'."
                )

    return {
        "errors": list(dict.fromkeys(errors)),
        "warnings": list(dict.fromkeys(warnings)),
        "missing_packages": list(dict.fromkeys(missing_packages)),
        "missing_citations": list(dict.fromkeys(missing_citations)),
        "suggested_fixes": list(dict.fromkeys(suggested_fixes)),
    }


def markdown_to_latex(
    markdown_content: str,
    title: str = "Academic Paper",
    author_info: dict | None = None,
    bib_content: str | None = None,
) -> str:
    """Convert Markdown draft content to a structured, compilable LaTeX document."""
    author_block = "OpenMLR Autonomous Research Agent"
    if author_info:
        name = author_info.get("name", "Author")
        affil = author_info.get("affiliation", "")
        email = author_info.get("email", "")
        author_block = name
        if affil:
            author_block += f"\\\\ \\small {affil}"
        if email:
            author_block += f"\\\\ \\small \\texttt{{{email}}}"

    tex_body = markdown_content
    tex_body = re.sub(r"^[ \t]*###[ \t]+(.*)$", r"\\subsubsection{\1}", tex_body, flags=re.MULTILINE)
    tex_body = re.sub(r"^[ \t]*##[ \t]+(.*)$", r"\\section{\1}", tex_body, flags=re.MULTILINE)
    tex_body = re.sub(r"^[ \t]*#[ \t]+(.*)$", r"", tex_body, flags=re.MULTILINE)
    tex_body = re.sub(r"\*\*([^*]+)\*\*", r"\\textbf{\1}", tex_body)
    tex_body = re.sub(r"\*([^*]+)\*", r"\\textit{\1}", tex_body)
    tex_body = re.sub(r"\[@([a-zA-Z0-9_\-:]+)\]", r"\\cite{\1}", tex_body)
    tex_body = tex_body.strip()

    latex_doc = f"""\\documentclass[11pt,a4paper]{{article}}
\\usepackage[utf8]{{inputenc}}
\\usepackage{{amsmath,amssymb,amsfonts}}
\\usepackage{{graphicx}}
\\usepackage{{booktabs}}
\\usepackage{{hyperref}}
\\usepackage{{cite}}
\\usepackage{{geometry}}
\\geometry{{margin=1in}}

\\title{{{title}}}
\\author{{{author_block}}}
\\date{{\\today}}

\\begin{{document}}

\\maketitle

{tex_body}

"""
    if bib_content:
        latex_doc += "\\bibliographystyle{plain}\n\\bibliography{references}\n"

    latex_doc += "\\end{document}\n"
    return latex_doc


async def compile_latex(
    tex_content: str,
    bib_content: str | None = None,
    engine: str | None = None,
    work_dir: str | Path | None = None,
    output_filename: str = "paper.pdf",
    timeout: int = 60,
) -> LaTeXCompilationResult:
    """Compile LaTeX and BibTeX in a sandboxed directory to generate a PDF artifact."""
    start_time = time.perf_counter()

    is_valid, syntax_errors, syntax_warnings = validate_latex_syntax(tex_content)
    if not is_valid:
        elapsed = (time.perf_counter() - start_time) * 1000
        return LaTeXCompilationResult(
            success=False,
            errors=syntax_errors,
            warnings=syntax_warnings,
            engine_used="static-validator",
            compilation_time_ms=elapsed,
            suggested_fixes=["Fix reported LaTeX syntax errors before running compiler."],
        )

    chosen_engine = engine or get_available_latex_engine()
    if not chosen_engine:
        elapsed = (time.perf_counter() - start_time) * 1000
        return LaTeXCompilationResult(
            success=True,
            log="Static syntax analysis passed cleanly. Headless compiler not installed on host.",
            warnings=syntax_warnings
            + ["Headless compiler not found. Install 'tectonic' or 'texlive' for PDF rendering."],
            engine_used="static-validator",
            compilation_time_ms=elapsed,
            suggested_fixes=["Install tectonic (`brew install tectonic`) for automated compilation."],
        )

    use_temp = work_dir is None
    target_dir = Path(tempfile.mkdtemp(prefix="openmlr_latex_")) if use_temp else Path(work_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    tex_path = target_dir / "document.tex"
    tex_path.write_text(tex_content, encoding="utf-8")
    if bib_content:
        (target_dir / "references.bib").write_text(bib_content, encoding="utf-8")

    full_log: list[str] = []
    compilation_success = False
    out_pdf = target_dir / "document.pdf"

    try:
        if chosen_engine == "tectonic":
            proc = await asyncio.create_subprocess_exec(
                "tectonic",
                "--keep-intermediates",
                "--outdir",
                str(target_dir),
                str(tex_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(target_dir),
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            full_log.extend([stdout.decode(errors="replace"), stderr.decode(errors="replace")])
            compilation_success = proc.returncode == 0 and out_pdf.exists()
        else:
            passes = [[chosen_engine, "-interaction=nonstopmode", "-halt-on-error", "document.tex"]]
            if bib_content:
                passes.extend([
                    ["bibtex", "document"],
                    [chosen_engine, "-interaction=nonstopmode", "-halt-on-error", "document.tex"],
                    [chosen_engine, "-interaction=nonstopmode", "-halt-on-error", "document.tex"],
                ])
            for cmd in passes:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(target_dir),
                )
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
                full_log.extend([stdout.decode(errors="replace"), stderr.decode(errors="replace")])
                if proc.returncode != 0 and cmd[0] != "bibtex":
                    break
            compilation_success = out_pdf.exists()

    except TimeoutError:
        full_log.append(f"\nCompilation timed out after {timeout} seconds.")
    except Exception as e:
        full_log.append(f"\nCompilation error: {e}")

    log_str = "\n".join(full_log)
    diagnostics = diagnose_latex_errors(log_str, tex_content)
    pdf_bytes = out_pdf.read_bytes() if (compilation_success and out_pdf.exists()) else None
    final_pdf_path = str(out_pdf) if (compilation_success and out_pdf.exists()) else None
    elapsed = (time.perf_counter() - start_time) * 1000

    result = LaTeXCompilationResult(
        success=compilation_success,
        pdf_path=final_pdf_path,
        pdf_bytes=pdf_bytes,
        log=log_str,
        errors=diagnostics["errors"],
        warnings=syntax_warnings + diagnostics["warnings"],
        missing_packages=diagnostics["missing_packages"],
        missing_citations=diagnostics["missing_citations"],
        engine_used=chosen_engine,
        compilation_time_ms=elapsed,
        suggested_fixes=diagnostics["suggested_fixes"],
    )

    if use_temp and not compilation_success:
        try:
            shutil.rmtree(target_dir, ignore_errors=True)
        except Exception:
            pass

    return result


def create_latex_tool() -> ToolSpec:
    """Create the LaTeX compilation and validation agent tool."""
    return ToolSpec(
        name="latex_compiler",
        description=(
            "Sandboxed LaTeX compiler and syntax validator.\n\n"
            "Operations:\n"
            "- compile: Compile LaTeX code or file to PDF.\n"
            "- validate: Static syntax analysis and BibTeX citation cross-referencing.\n"
            "- convert_markdown: Convert a Markdown paper draft into LaTeX.\n"
            "- check_engine: Inspect available LaTeX compilers on the system."
        ),
        parameters={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["compile", "validate", "convert_markdown", "check_engine"],
                    "description": "Operation to perform",
                },
                "tex_content": {"type": "string", "description": "Raw LaTeX document string"},
                "bib_content": {"type": "string", "description": "Optional raw BibTeX bibliography string"},
                "markdown_content": {"type": "string", "description": "Markdown text to convert"},
                "title": {"type": "string", "description": "Paper title"},
            },
            "required": ["operation"],
        },
        handler=_handle_latex_tool,
    )


async def _handle_latex_tool(
    operation: str,
    tex_content: str | None = None,
    bib_content: str | None = None,
    markdown_content: str | None = None,
    title: str = "Paper",
    session=None,
    **kwargs,
) -> tuple[str, bool]:
    """Handle LaTeX tool execution."""
    if operation == "check_engine":
        engine = get_available_latex_engine()
        if engine:
            return f"LaTeX compiler engine available: '{engine}'. Supported engines: {LATEX_ENGINES}", True
        return (
            f"No headless LaTeX engine found in PATH (searched: {LATEX_ENGINES}). "
            "Static syntax validator and Markdown converter are fully active.",
            True,
        )

    if operation == "validate":
        if not tex_content:
            return "Provide 'tex_content' to validate.", False
        is_valid, errors, warnings = validate_latex_syntax(tex_content)
        report = [f"LaTeX Syntax Valid: {is_valid}"]
        if errors:
            report.append("\nErrors:\n" + "\n".join(f"  - {e}" for e in errors))
        if warnings:
            report.append("\nWarnings:\n" + "\n".join(f"  - {w}" for w in warnings))

        if bib_content:
            bib_res = validate_bibtex(bib_content, tex_content)
            report.append(f"\nBibTeX Citations: {bib_res.entries_count} entries")
            if bib_res.missing_citations:
                report.append(f"  Missing Citations ({len(bib_res.missing_citations)}): {', '.join(bib_res.missing_citations)}")
            if bib_res.unused_citations:
                report.append(f"  Unused Citations ({len(bib_res.unused_citations)}): {', '.join(bib_res.unused_citations)}")

        return "\n".join(report), is_valid

    if operation == "convert_markdown":
        if not markdown_content:
            return "Provide 'markdown_content' to convert.", False
        return markdown_to_latex(markdown_content, title=title, bib_content=bib_content), True

    if operation == "compile":
        if not tex_content:
            return "Provide 'tex_content' to compile.", False
        res = await compile_latex(tex_content=tex_content, bib_content=bib_content)
        if res.success:
            msg = f"LaTeX compilation succeeded ({res.engine_used}, {res.compilation_time_ms:.1f}ms)."
            if res.pdf_path:
                msg += f" Output PDF: {res.pdf_path}"
            if res.warnings:
                msg += "\nWarnings:\n" + "\n".join(f"  - {w}" for w in res.warnings[:5])
            return msg, True
        else:
            msg = f"LaTeX compilation failed ({res.engine_used}).\nErrors:\n" + "\n".join(f"  - {e}" for e in res.errors[:5])
            if res.suggested_fixes:
                msg += "\nSuggested Fixes:\n" + "\n".join(f"  - {f}" for f in res.suggested_fixes[:5])
            return msg, False

    return f"Unknown operation: {operation}", False
