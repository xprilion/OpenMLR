"""Tests for BibTeX validator service."""

import pytest

from openmlr.services.bibtex_validator import (
    BibtexEntry,
    extract_latex_citations,
    normalize_bibtex,
    parse_bibtex,
    validate_bibtex,
)

pytestmark = pytest.mark.asyncio


class TestBibtexEntry:
    def test_get_field_case_insensitive(self):
        entry = BibtexEntry(
            key="vaswani2017",
            entry_type="inproceedings",
            fields={"Title": "Attention Is All You Need", "YEAR": "2017"},
        )
        assert entry.get("title") == "Attention Is All You Need"
        assert entry.get("year") == "2017"
        assert entry.get("missing", "default") == "default"

    def test_to_bibtex(self):
        entry = BibtexEntry(
            key="test2024",
            entry_type="article",
            fields={"author": "Alice", "title": "A Paper", "year": "2024"},
        )
        bib = entry.to_bibtex()
        assert "@article{test2024," in bib
        assert "author = {Alice}," in bib
        assert "title = {A Paper}," in bib
        assert "year = {2024}," in bib


class TestExtractLatexCitations:
    def test_extract_various_cite_commands(self):
        tex = r"""
        According to \cite{vaswani2017, devlin2018}, transformers are effective.
        Prior work \citep[see][p. 10]{brown2020gpt3} demonstrated few-shot learning.
        As shown by \citet{he2016deep}, residual connections help.
        Also see \autocite{kingma2014adam} and \nocite{radford2019}.
        % Ignored comment \cite{ignored2021}
        """
        citations = extract_latex_citations(tex)
        assert "vaswani2017" in citations
        assert "devlin2018" in citations
        assert "brown2020gpt3" in citations
        assert "he2016deep" in citations
        assert "kingma2014adam" in citations
        assert "radford2019" in citations
        assert "ignored2021" not in citations

    def test_empty_latex_returns_empty_set(self):
        assert extract_latex_citations("") == set()


class TestParseBibtex:
    def test_parse_valid_bibtex(self):
        bib = r"""
        @article{vaswani2017,
            author = {Ashish Vaswani and Noam Shazeer},
            title = {Attention Is All You Need},
            journal = {NeurIPS},
            year = {2017}
        }

        @inproceedings{he2016,
            author = "Kaiming He and Xiangyu Zhang",
            title = "Deep Residual Learning for Image Recognition",
            booktitle = "CVPR",
            year = "2016"
        }
        """
        entries, errors = parse_bibtex(bib)
        assert len(errors) == 0
        assert len(entries) == 2

        e1 = entries[0]
        assert e1.key == "vaswani2017"
        assert e1.entry_type == "article"
        assert "Vaswani" in e1.get("author")
        assert e1.get("year") == "2017"

        e2 = entries[1]
        assert e2.key == "he2016"
        assert e2.entry_type == "inproceedings"
        assert e2.get("title") == "Deep Residual Learning for Image Recognition"

    def test_parse_malformed_header_records_error(self):
        bib = "@invalid_header\n@article{valid2020, title={Valid}, year={2020}}"
        entries, errors = parse_bibtex(bib)
        assert len(errors) > 0
        assert len(entries) == 1
        assert entries[0].key == "valid2020"


class TestValidateBibtex:
    def test_valid_bibtex_with_latex(self):
        bib = """
        @article{vaswani2017,
            author = {Vaswani et al.},
            title = {Attention Is All You Need},
            journal = {NeurIPS},
            year = {2017}
        }
        """
        tex = r"We use self-attention \cite{vaswani2017} in our model."
        res = validate_bibtex(bib, tex)
        assert res.valid is True
        assert res.entries_count == 1
        assert len(res.errors) == 0
        assert len(res.missing_citations) == 0

    def test_detects_missing_citations_and_unused_citations(self):
        bib = """
        @article{vaswani2017,
            author = {Vaswani et al.},
            title = {Attention Is All You Need},
            journal = {NeurIPS},
            year = {2017}
        }
        @article{unused2020,
            author = {Unused Author},
            title = {Unused Paper},
            journal = {Nature},
            year = {2020}
        }
        """
        tex = r"As shown in \cite{vaswani2017} and \cite{missing2023}."
        res = validate_bibtex(bib, tex)
        assert res.valid is False
        assert "missing2023" in res.missing_citations
        assert "unused2020" in res.unused_citations

    def test_detects_duplicate_citation_keys(self):
        bib = """
        @article{dupKey,
            author = {A},
            title = {Paper A},
            journal = {J},
            year = {2020}
        }
        @article{dupKey,
            author = {B},
            title = {Paper B},
            journal = {J},
            year = {2021}
        }
        """
        res = validate_bibtex(bib)
        assert res.valid is False
        assert "dupKey" in res.duplicate_keys
        assert any("Duplicate citation key" in e for e in res.errors)

    def test_warns_on_missing_required_fields(self):
        bib = """
        @article{incomplete2021,
            title = {Incomplete Paper}
        }
        """
        res = validate_bibtex(bib)
        assert any("missing recommended field 'author'" in w for w in res.warnings)
        assert any("missing recommended field 'journal'" in w for w in res.warnings)


class TestNormalizeBibtex:
    def test_normalizes_entries(self):
        bib = """
        @article{  testKey  ,
            year={2022},
            title={Some Title},
            author={John}
        }
        """
        normalized = normalize_bibtex(bib)
        assert "@article{testKey," in normalized
        assert "author = {John}," in normalized
        assert "title = {Some Title}," in normalized
        assert "year = {2022}," in normalized
