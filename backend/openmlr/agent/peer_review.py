"""Autonomous Multi-Agent Peer Review Simulation for OpenMLR.

Simulates a committee of 3 specialized academic reviewers:
- Reviewer 1: Theory & Conceptual Novelty
- Reviewer 2: Empirical Validation & Baselines
- Reviewer 3: Clarity, Reproducibility & Checklist
And 1 Meta-Reviewer (Area Chair) that consolidates reviews into a final verdict.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from typing import Any

from .llm import LLMProvider
from .review_prompts import (
    CONFERENCE_RUBRICS,
    REVIEWER_PERSONAS,
    ConferenceVenue,
    build_meta_reviewer_prompt,
    build_reviewer_system_prompt,
    build_reviewer_user_prompt,
)

logger = logging.getLogger(__name__)


@dataclass
class SingleReview:
    """Detailed evaluation from an individual reviewer agent."""

    reviewer_id: str
    reviewer_name: str
    role: str
    overall_score: int  # 1-10
    confidence: int  # 1-5
    summary: str
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    questions_for_authors: list[str] = field(default_factory=list)
    detailed_comments: str = ""
    recommendation: str = "Borderline"
    criteria_scores: dict[str, int] = field(default_factory=dict)
    raw_response: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SingleReview:
        return cls(
            reviewer_id=data.get("reviewer_id", "rev_unknown"),
            reviewer_name=data.get("reviewer_name", "Reviewer"),
            role=data.get("role", "Peer Reviewer"),
            overall_score=int(data.get("overall_score", 5)),
            confidence=int(data.get("confidence", 3)),
            summary=data.get("summary", ""),
            strengths=data.get("strengths", []),
            weaknesses=data.get("weaknesses", []),
            questions_for_authors=data.get("questions_for_authors", []),
            detailed_comments=data.get("detailed_comments", ""),
            recommendation=data.get("recommendation", "Borderline"),
            criteria_scores=data.get("criteria_scores", {}),
            raw_response=data.get("raw_response", ""),
        )


@dataclass
class MetaReview:
    """Consolidated Area Chair decision and synthesized revision plan."""

    decision: str  # e.g. "Accept", "Weak Accept", "Reject"
    decision_type: str  # "accept" | "reject" | "borderline"
    consensus_score: float  # 1.0 - 10.0
    confidence: int  # 1-5
    summary_of_consensus: str
    justification: str
    key_strengths: list[str] = field(default_factory=list)
    primary_shortcomings: list[str] = field(default_factory=list)
    actionable_revision_plan: list[str] = field(default_factory=list)
    raw_response: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MetaReview:
        return cls(
            decision=data.get("decision", "Borderline"),
            decision_type=data.get("decision_type", "borderline"),
            consensus_score=float(data.get("consensus_score", 5.0)),
            confidence=int(data.get("confidence", 3)),
            summary_of_consensus=data.get("summary_of_consensus", ""),
            justification=data.get("justification", ""),
            key_strengths=data.get("key_strengths", []),
            primary_shortcomings=data.get("primary_shortcomings", []),
            actionable_revision_plan=data.get("actionable_revision_plan", []),
            raw_response=data.get("raw_response", ""),
        )


@dataclass
class PeerReviewResult:
    """Full committee outcome containing all reviewer evaluations and the meta-review."""

    submission_title: str
    venue: str
    reviews: list[SingleReview] = field(default_factory=list)
    meta_review: MetaReview | None = None
    evaluated_at: float = field(default_factory=time.time)
    status: str = "completed"

    @property
    def average_score(self) -> float:
        if not self.reviews:
            return 0.0
        return sum(r.overall_score for r in self.reviews) / len(self.reviews)

    def to_dict(self) -> dict[str, Any]:
        return {
            "submission_title": self.submission_title,
            "venue": self.venue,
            "average_score": round(self.average_score, 2),
            "reviews": [r.to_dict() for r in self.reviews],
            "meta_review": self.meta_review.to_dict() if self.meta_review else None,
            "evaluated_at": self.evaluated_at,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PeerReviewResult:
        reviews = [SingleReview.from_dict(r) for r in data.get("reviews", [])]
        meta_dict = data.get("meta_review")
        meta = MetaReview.from_dict(meta_dict) if meta_dict else None
        return cls(
            submission_title=data.get("submission_title", ""),
            venue=data.get("venue", "iclr"),
            reviews=reviews,
            meta_review=meta,
            evaluated_at=data.get("evaluated_at", time.time()),
            status=data.get("status", "completed"),
        )


def _extract_json_payload(text: str) -> dict[str, Any] | None:
    """Extract JSON object from raw response text (handles markdown code fences)."""
    if not text or not text.strip():
        return None
    try:
        data = json.loads(text.strip())
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    block_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if block_match:
        try:
            data = json.loads(block_match.group(1).strip())
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            data = json.loads(text[start : end + 1])
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass
    return None


def _clean_list_field(val: Any) -> list[str]:
    if isinstance(val, list):
        return [str(item).strip() for item in val if str(item).strip()]
    if isinstance(val, str):
        return [s.strip("- ") for s in val.split("\n") if s.strip()]
    return []


class PeerReviewSimulator:
    """Autonomous peer review simulation coordinator."""

    def __init__(self, default_venue: ConferenceVenue = ConferenceVenue.ICLR):
        self.default_venue = default_venue

    def parse_reviewer_response(self, raw_text: str, persona: dict[str, Any]) -> SingleReview:
        """Parse LLM output into a SingleReview object with robust fallback."""
        payload = _extract_json_payload(raw_text)
        if payload:
            try:
                score_int = max(1, min(10, int(payload.get("overall_score", 5))))
            except (ValueError, TypeError):
                score_int = 5
            try:
                conf_int = max(1, min(5, int(payload.get("confidence", 3))))
            except (ValueError, TypeError):
                conf_int = 3

            return SingleReview(
                reviewer_id=payload.get("reviewer_id", persona["id"]),
                reviewer_name=payload.get("reviewer_name", persona["name"]),
                role=payload.get("role", persona["role"]),
                overall_score=score_int,
                confidence=conf_int,
                summary=str(payload.get("summary", "")),
                strengths=_clean_list_field(payload.get("strengths")),
                weaknesses=_clean_list_field(payload.get("weaknesses")),
                questions_for_authors=_clean_list_field(payload.get("questions_for_authors")),
                detailed_comments=str(payload.get("detailed_comments", "")),
                recommendation=str(payload.get("recommendation", "Borderline")),
                criteria_scores=payload.get("criteria_scores", {})
                if isinstance(payload.get("criteria_scores"), dict)
                else {},
                raw_response=raw_text,
            )

        # Fallback heuristic parser
        score_match = re.search(r"(?:score|rating|verdict)[:\s]*([1-9]|10)\b", raw_text, re.IGNORECASE)
        score_val = int(score_match.group(1)) if score_match else 5
        rec = "Accept" if score_val >= 7 else ("Reject" if score_val <= 4 else "Borderline")
        return SingleReview(
            reviewer_id=persona["id"],
            reviewer_name=persona["name"],
            role=persona["role"],
            overall_score=score_val,
            confidence=3,
            summary=raw_text[:300].strip(),
            detailed_comments=raw_text.strip(),
            recommendation=rec,
            raw_response=raw_text,
        )

    def parse_meta_review_response(self, raw_text: str, reviews: list[SingleReview]) -> MetaReview:
        """Parse Area Chair output into a MetaReview object."""
        payload = _extract_json_payload(raw_text)
        avg_score = sum(r.overall_score for r in reviews) / len(reviews) if reviews else 5.0

        if payload:
            try:
                consensus_float = round(float(payload.get("consensus_score", avg_score)), 2)
            except (ValueError, TypeError):
                consensus_float = round(avg_score, 2)
            try:
                conf_int = max(1, min(5, int(payload.get("confidence", 4))))
            except (ValueError, TypeError):
                conf_int = 4

            decision = str(payload.get("decision", "Borderline"))
            dec_type = payload.get("decision_type", "")
            if not dec_type:
                dec_type = "accept" if "accept" in decision.lower() else ("reject" if "reject" in decision.lower() else "borderline")

            return MetaReview(
                decision=decision,
                decision_type=dec_type,
                consensus_score=consensus_float,
                confidence=conf_int,
                summary_of_consensus=str(payload.get("summary_of_consensus", "")),
                justification=str(payload.get("justification", "")),
                key_strengths=_clean_list_field(payload.get("key_strengths")),
                primary_shortcomings=_clean_list_field(payload.get("primary_shortcomings")),
                actionable_revision_plan=_clean_list_field(payload.get("actionable_revision_plan")),
                raw_response=raw_text,
            )

        decision = "Accept" if avg_score >= 6.5 else ("Reject" if avg_score <= 4.5 else "Borderline")
        return MetaReview(
            decision=decision,
            decision_type="accept" if avg_score >= 6.5 else ("reject" if avg_score <= 4.5 else "borderline"),
            consensus_score=round(avg_score, 2),
            confidence=3,
            summary_of_consensus=raw_text[:400].strip(),
            justification=raw_text.strip(),
            raw_response=raw_text,
        )

    def summarize_reviews_for_meta(self, reviews: list[SingleReview]) -> str:
        """Format reviewer opinions for Area Chair synthesis."""
        sections = []
        for rev in reviews:
            strengths_str = "\n".join(f"  + {s}" for s in rev.strengths) or "  None listed"
            weaknesses_str = "\n".join(f"  - {w}" for w in rev.weaknesses) or "  None listed"
            questions_str = "\n".join(f"  ? {q}" for q in rev.questions_for_authors) or "  None"
            sections.append(
                f"### {rev.reviewer_name} ({rev.role})\n"
                f"- Overall Score: {rev.overall_score}/10 (Confidence: {rev.confidence}/5)\n"
                f"- Recommendation: {rev.recommendation}\n"
                f"- Summary: {rev.summary}\n"
                f"- Key Strengths:\n{strengths_str}\n"
                f"- Key Weaknesses:\n{weaknesses_str}\n"
                f"- Questions for Authors:\n{questions_str}\n"
                f"- Detailed Comments: {rev.detailed_comments[:500]}"
            )
        return "\n\n".join(sections)

    async def evaluate_submission(
        self,
        submission_text: str,
        venue: ConferenceVenue | str = ConferenceVenue.ICLR,
        title: str = "",
        context: dict[str, Any] | None = None,
        config: Any | None = None,
        custom_llm_fn: Callable[[list[dict[str, str]]], Any] | None = None,
    ) -> PeerReviewResult:
        """Run full autonomous peer review simulation with 3 reviewers + 1 Area Chair."""
        if isinstance(venue, str):
            try:
                venue_enum = ConferenceVenue(venue.lower())
            except ValueError:
                venue_enum = ConferenceVenue.GENERAL
        else:
            venue_enum = venue

        async def _call_model(messages: list[dict[str, str]]) -> str:
            if custom_llm_fn:
                res = custom_llm_fn(messages)
                if asyncio.iscoroutine(res):
                    res = await res
                return str(res)
            if config:
                res = await LLMProvider.generate(messages=messages, config=config)
                return res.content or ""
            return "{}"

        async def _evaluate_single(persona: dict[str, Any]) -> SingleReview:
            sys_prompt = build_reviewer_system_prompt(persona, venue_enum)
            user_prompt = build_reviewer_user_prompt(title, submission_text, context)
            messages = [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt},
            ]
            raw_response = await _call_model(messages)
            return self.parse_reviewer_response(raw_response, persona)

        reviews = await asyncio.gather(*[_evaluate_single(p) for p in REVIEWER_PERSONAS])

        reviews_summary = self.summarize_reviews_for_meta(list(reviews))
        meta_prompt = build_meta_reviewer_prompt(
            venue=venue_enum,
            title=title,
            submission_text=submission_text,
            reviews_summary=reviews_summary,
        )
        meta_messages = [
            {"role": "system", "content": f"You are the Area Chair for {CONFERENCE_RUBRICS[venue_enum]['name']}."},
            {"role": "user", "content": meta_prompt},
        ]
        meta_raw = await _call_model(meta_messages)
        meta_review = self.parse_meta_review_response(meta_raw, list(reviews))

        return PeerReviewResult(
            submission_title=title,
            venue=venue_enum.value,
            reviews=list(reviews),
            meta_review=meta_review,
            evaluated_at=time.time(),
            status="completed",
        )

    def format_markdown_report(self, result: PeerReviewResult) -> str:
        """Format peer review result into a publication-ready Markdown report."""
        meta = result.meta_review
        lines = [
            f"# Autonomous Peer Review Report: {result.submission_title or 'Research Submission'}",
            f"**Conference Venue:** {result.venue.upper()} | **Evaluated At:** {time.ctime(result.evaluated_at)}",
            "",
            "## 🏆 Area Chair Meta-Review & Decision",
        ]
        if meta:
            lines.extend(
                [
                    f"- **Final Decision:** `{meta.decision.upper()}`",
                    f"- **Consensus Score:** **{meta.consensus_score} / 10** (Confidence: {meta.confidence}/5)",
                    f"- **Decision Type:** {meta.decision_type.capitalize()}",
                    "",
                    "### Summary of Consensus",
                    meta.summary_of_consensus or "No consensus summary provided.",
                    "",
                    "### Decision Justification",
                    meta.justification or "No justification provided.",
                    "",
                    "### Actionable Revision Plan",
                ]
            )
            for i, plan in enumerate(meta.actionable_revision_plan, start=1):
                lines.append(f"{i}. {plan}")
            lines.append("")
        else:
            lines.append(f"- **Average Committee Score:** {result.average_score:.2f} / 10\n")

        lines.append("## 📋 Individual Reviewer Evaluations\n")
        for rev in result.reviews:
            lines.extend(
                [
                    f"### {rev.reviewer_name}: {rev.role}",
                    f"- **Score:** `{rev.overall_score}/10` | **Confidence:** `{rev.confidence}/5` | **Recommendation:** `{rev.recommendation}`",
                    f"- **Summary:** {rev.summary}",
                    "",
                    "#### Strengths:",
                ]
            )
            for s in rev.strengths:
                lines.append(f"- ✅ {s}")
            lines.append("\n#### Weaknesses:")
            for w in rev.weaknesses:
                lines.append(f"- ⚠️ {w}")
            if rev.questions_for_authors:
                lines.append("\n#### Questions for Authors:")
                for q in rev.questions_for_authors:
                    lines.append(f"- ❓ {q}")
            if rev.detailed_comments:
                lines.extend(["\n#### Detailed Critique:", rev.detailed_comments])
            lines.append("\n---\n")
        return "\n".join(lines)
