"""Unit and integration tests for autonomous multi-agent peer review simulation."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from openmlr.agent.peer_review import (
    MetaReview,
    PeerReviewResult,
    PeerReviewSimulator,
    SingleReview,
    _extract_json_payload,
)
from openmlr.agent.review_prompts import (
    CONFERENCE_RUBRICS,
    REVIEWER_PERSONAS,
    ConferenceVenue,
    build_meta_reviewer_prompt,
    build_reviewer_system_prompt,
    build_reviewer_user_prompt,
)
from openmlr.app import app


class TestReviewPrompts:
    def test_conference_rubrics_completeness(self):
        for venue in [
            ConferenceVenue.ICLR,
            ConferenceVenue.NEURIPS,
            ConferenceVenue.ICML,
            ConferenceVenue.CVPR,
            ConferenceVenue.ACL,
            ConferenceVenue.GENERAL,
        ]:
            assert venue in CONFERENCE_RUBRICS
            rubric = CONFERENCE_RUBRICS[venue]
            assert "name" in rubric
            assert "criteria" in rubric
            assert len(rubric["criteria"]) >= 3

    def test_reviewer_personas_completeness(self):
        assert len(REVIEWER_PERSONAS) == 3
        ids = [p["id"] for p in REVIEWER_PERSONAS]
        assert "rev_theory" in ids
        assert "rev_empirical" in ids
        assert "rev_clarity" in ids

    def test_build_reviewer_system_prompt(self):
        persona = REVIEWER_PERSONAS[0]
        prompt = build_reviewer_system_prompt(persona, ConferenceVenue.ICLR)
        assert "Theory & Conceptual Novelty" in prompt
        assert "International Conference on Learning Representations" in prompt
        assert "overall_score" in prompt

    def test_build_reviewer_user_prompt(self):
        prompt = build_reviewer_user_prompt(
            title="Scalable Attention Mechanism",
            submission_text=r"\section{Introduction} Here is our paper.",
            context={"target_benchmark": "ImageNet-1k"},
        )
        assert "Scalable Attention Mechanism" in prompt
        assert "ImageNet-1k" in prompt
        assert "Introduction" in prompt

    def test_build_meta_reviewer_prompt(self):
        prompt = build_meta_reviewer_prompt(
            venue=ConferenceVenue.NEURIPS,
            title="Ablation Analysis of MoE",
            submission_text="We investigate sparse Mixture of Experts.",
            reviews_summary="Reviewer 1: Score 8. Reviewer 2: Score 7.",
        )
        assert "Neural Information Processing Systems" in prompt
        assert "Ablation Analysis of MoE" in prompt
        assert "decision" in prompt


class TestPeerReviewDataModels:
    def test_single_review_roundtrip(self):
        review = SingleReview(
            reviewer_id="rev_theory",
            reviewer_name="Reviewer 1",
            role="Theory Specialist",
            overall_score=8,
            confidence=4,
            summary="Strong mathematical formulation of the lower bound.",
            strengths=["Novel theorem 1", "Clean proof in Appendix"],
            weaknesses=["Assumes Lipschitz continuity everywhere"],
            questions_for_authors=["Can bound be tightened for non-convex loss?"],
            detailed_comments="Detailed remarks here...",
            recommendation="Accept",
            criteria_scores={"novelty": 9, "soundness": 8},
        )
        data = review.to_dict()
        assert data["overall_score"] == 8
        assert data["reviewer_id"] == "rev_theory"
        assert len(data["strengths"]) == 2

        restored = SingleReview.from_dict(data)
        assert restored.overall_score == 8
        assert restored.recommendation == "Accept"
        assert restored.strengths[0] == "Novel theorem 1"

    def test_meta_review_roundtrip(self):
        meta = MetaReview(
            decision="Accept",
            decision_type="accept",
            consensus_score=7.8,
            confidence=4,
            summary_of_consensus="All reviewers agree the method is sound and effective.",
            justification="Consistent empirical gains across 4 benchmarks.",
            key_strengths=["Strong empirical results", "Clean formal proof"],
            primary_shortcomings=["Missing comparison to baseline X"],
            actionable_revision_plan=["Add baseline X to Table 2", "Clarify notation in Eq 4"],
        )
        data = meta.to_dict()
        assert data["decision"] == "Accept"
        assert data["consensus_score"] == 7.8

        restored = MetaReview.from_dict(data)
        assert restored.decision == "Accept"
        assert len(restored.actionable_revision_plan) == 2

    def test_peer_review_result_average_score(self):
        r1 = SingleReview(
            reviewer_id="r1",
            reviewer_name="Reviewer 1",
            role="Theory",
            overall_score=8,
            confidence=4,
            summary="Great",
        )
        r2 = SingleReview(
            reviewer_id="r2",
            reviewer_name="Reviewer 2",
            role="Empirical",
            overall_score=6,
            confidence=3,
            summary="Solid",
        )
        result = PeerReviewResult(
            submission_title="Test Paper",
            venue="iclr",
            reviews=[r1, r2],
        )
        assert result.average_score == 7.0
        data = result.to_dict()
        assert data["average_score"] == 7.0
        assert len(data["reviews"]) == 2


class TestJsonAndHeuristicParsing:
    def test_extract_json_payload_clean(self):
        raw = '{"overall_score": 8, "confidence": 4, "summary": "Great work"}'
        res = _extract_json_payload(raw)
        assert res is not None
        assert res["overall_score"] == 8

    def test_extract_json_payload_code_fence(self):
        raw = """Here is my review:
```json
{
  "overall_score": 7,
  "confidence": 3,
  "summary": "Good empirical findings"
}
```
Thank you."""
        res = _extract_json_payload(raw)
        assert res is not None
        assert res["overall_score"] == 7

    def test_parse_reviewer_response_json(self):
        sim = PeerReviewSimulator()
        persona = REVIEWER_PERSONAS[0]
        raw = json.dumps(
            {
                "reviewer_id": "rev_theory",
                "reviewer_name": "Reviewer 1",
                "role": "Theory",
                "overall_score": 9,
                "confidence": 5,
                "summary": "Outstanding paper",
                "strengths": ["Clear proof", "Rigorous"],
                "weaknesses": ["Minor notation typos"],
                "questions_for_authors": ["Clarify lemma 2"],
                "detailed_comments": "Looks very promising.",
                "recommendation": "Strong Accept",
            }
        )
        review = sim.parse_reviewer_response(raw, persona)
        assert review.overall_score == 9
        assert review.confidence == 5
        assert len(review.strengths) == 2
        assert review.recommendation == "Strong Accept"

    def test_parse_reviewer_response_heuristic_fallback(self):
        sim = PeerReviewSimulator()
        persona = REVIEWER_PERSONAS[1]
        raw = "I evaluate this paper thoroughly. Score: 8. The baselines are strong and the results convincing."
        review = sim.parse_reviewer_response(raw, persona)
        assert review.overall_score == 8
        assert review.recommendation == "Accept"
        assert review.reviewer_id == "rev_empirical"

    def test_parse_meta_review_response(self):
        sim = PeerReviewSimulator()
        raw = json.dumps(
            {
                "decision": "Strong Accept",
                "decision_type": "accept",
                "consensus_score": 8.5,
                "confidence": 5,
                "summary_of_consensus": "Unanimous accept from all reviewers.",
                "justification": "Significant theoretical and empirical impact.",
                "key_strengths": ["Rigorous theory", "Extensive benchmarks"],
                "primary_shortcomings": [],
                "actionable_revision_plan": ["Publish open-source code and weights"],
            }
        )
        meta = sim.parse_meta_review_response(raw, [])
        assert meta.decision == "Strong Accept"
        assert meta.decision_type == "accept"
        assert meta.consensus_score == 8.5
        assert len(meta.actionable_revision_plan) == 1


class TestPeerReviewSimulatorAsync:
    @pytest.mark.asyncio
    async def test_evaluate_submission_with_mock_llm(self):
        sim = PeerReviewSimulator()

        async def mock_llm_fn(messages):
            sys_msg = next((m["content"] for m in messages if m["role"] == "system"), "")
            if "Area Chair" in sys_msg:
                return json.dumps(
                    {
                        "decision": "Accept",
                        "decision_type": "accept",
                        "consensus_score": 8.0,
                        "confidence": 4,
                        "summary_of_consensus": "Reviewers favor acceptance based on novelty.",
                        "justification": "Solid empirical and theoretical evidence.",
                        "key_strengths": ["Clear formulation", "Strong baseline comparisons"],
                        "primary_shortcomings": ["Needs more seeds in Table 1"],
                        "actionable_revision_plan": [
                            "Run 5 seeds on CIFAR-100",
                            "Expand Appendix B with proofs",
                        ],
                    }
                )
            # Individual reviewer response
            return json.dumps(
                {
                    "overall_score": 8,
                    "confidence": 4,
                    "summary": "Well written research proposal with sound methodology.",
                    "strengths": ["Novel architecture", "Rigorous analysis"],
                    "weaknesses": ["Minor computational overhead"],
                    "questions_for_authors": ["What is the inference latency on RTX 4090?"],
                    "detailed_comments": "A solid contribution to representation learning.",
                    "recommendation": "Accept",
                }
            )

        submission_text = r"""
        \title{Transformer Self-Attention with Sub-Quadratic Kernel Approximations}
        \section{Abstract} We introduce a novel attention kernel that reduces time complexity to O(N log N).
        \section{Experiments} We evaluate on Wikitext-103 and achieve 18.2 perplexity.
        """

        result = await sim.evaluate_submission(
            submission_text=submission_text,
            venue=ConferenceVenue.ICLR,
            title="Transformer Self-Attention with Sub-Quadratic Kernel Approximations",
            custom_llm_fn=mock_llm_fn,
        )

        assert len(result.reviews) == 3
        assert result.venue == "iclr"
        assert result.meta_review is not None
        assert result.meta_review.decision == "Accept"
        assert result.meta_review.consensus_score == 8.0

        # Verify markdown report formatting
        report = sim.format_markdown_report(result)
        assert "# Autonomous Peer Review Report" in report
        assert "Area Chair Meta-Review & Decision" in report
        assert "ACCEPT" in report
        assert "Reviewer 1" in report
        assert "Reviewer 2" in report
        assert "Reviewer 3" in report


class TestPeerReviewRoutes:
    @pytest.mark.asyncio
    async def test_get_rubrics(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/review/rubrics")
            assert resp.status_code == 200
            data = resp.json()
            assert "rubrics" in data
            assert "iclr" in data["rubrics"]
            assert "neurips" in data["rubrics"]
            assert "personas" in data
            assert len(data["personas"]) == 3

    @pytest.mark.asyncio
    async def test_post_evaluate_submission(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            with patch.object(
                PeerReviewSimulator,
                "evaluate_submission",
                new_callable=AsyncMock,
            ) as mock_eval:
                mock_eval.return_value = PeerReviewResult(
                    submission_title="Fast Linear Attention",
                    venue="iclr",
                    reviews=[
                        SingleReview(
                            reviewer_id="rev_theory",
                            reviewer_name="Reviewer 1",
                            role="Theory",
                            overall_score=8,
                            confidence=4,
                            summary="Novel theory.",
                        )
                    ],
                    meta_review=MetaReview(
                        decision="Accept",
                        decision_type="accept",
                        consensus_score=8.0,
                        confidence=4,
                        summary_of_consensus="Solid work.",
                        justification="Well supported.",
                    ),
                )
                payload = {
                    "submission_text": "We present Fast Linear Attention with provable convergence bounds.",
                    "venue": "iclr",
                    "title": "Fast Linear Attention",
                }
                resp = await client.post("/api/review/evaluate", json=payload)
                assert resp.status_code == 200
                data = resp.json()
                assert data["submission_title"] == "Fast Linear Attention"
                assert data["venue"] == "iclr"
                assert "meta_review" in data
                assert data["meta_review"]["decision"] == "Accept"
                assert "markdown_report" in data
