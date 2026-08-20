"""Conference rubrics and persona prompts for autonomous peer review simulation.

Supports standard ML conference rubrics (ICLR, NeurIPS, ICML, CVPR, ACL, General ML)
and detailed evaluation personas for Theory & Novelty, Empirical Validation,
Clarity & Reproducibility, and Meta-Review (Area Chair).
"""

from __future__ import annotations

from enum import Enum
from typing import Any


class ConferenceVenue(str, Enum):
    """Supported academic conference evaluation venues."""

    ICLR = "iclr"
    NEURIPS = "neurips"
    ICML = "icml"
    CVPR = "cvpr"
    ACL = "acl"
    GENERAL = "general"


CONFERENCE_RUBRICS: dict[ConferenceVenue, dict[str, Any]] = {
    ConferenceVenue.ICLR: {
        "name": "International Conference on Learning Representations (ICLR)",
        "focus": "Deep learning, representation learning, mathematical soundness, architectural innovation",
        "scale": "1-10 (10: Top 5% of accepted papers; 8: Strong accept; 6: Weak accept; 5: Borderline; 3: Weak reject; 1: Strong reject)",
        "criteria": [
            "Novelty and significance of representation learning formulations",
            "Theoretical grounding and mathematical correctness",
            "Empirical performance against recognized competitive baselines",
            "Clarity of exposition, technical depth, and reproducible setup",
        ],
    },
    ConferenceVenue.NEURIPS: {
        "name": "Neural Information Processing Systems (NeurIPS)",
        "focus": "Theoretical foundation, statistical rigor, novel algorithms, societal & ethical impacts",
        "scale": "1-10 (10: Award quality; 8: Strong accept; 6: Weak accept; 5: Borderline; 3: Weak reject; 1: Strong reject)",
        "criteria": [
            "Originality and non-trivial conceptual advances",
            "Soundness of theoretical claims and empirical evaluations",
            "Completeness of ablation studies across diverse seeds and datasets",
            "Reproducibility checklist compliance (compute, hyperparameters, code availability)",
        ],
    },
    ConferenceVenue.ICML: {
        "name": "International Conference on Machine Learning (ICML)",
        "focus": "Algorithmic machine learning, optimization theory, statistical significance, computational complexity",
        "scale": "1-10 (10: Landmark contribution; 8: Strong accept; 6: Weak accept; 5: Borderline; 3: Weak reject; 1: Strong reject)",
        "criteria": [
            "Mathematical correctness and rigor of theoretical deductions",
            "Empirical validation with error bars and statistical hypothesis testing",
            "Algorithmic efficiency (FLOPs, latency, memory complexity)",
            "Honest discussion of failure modes and computational boundaries",
        ],
    },
    ConferenceVenue.CVPR: {
        "name": "IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)",
        "focus": "Visual intelligence, multimodal architectures, benchmark performance, computational efficiency",
        "scale": "1-10 (10: Oral/Best paper candidate; 8: Strong accept; 6: Weak accept; 5: Borderline; 3: Weak reject; 1: Strong reject)",
        "criteria": [
            "Visual reasoning novelty and architectural design",
            "Evaluation across standard vision benchmarks (e.g. ImageNet, COCO, ADE20K)",
            "Visual ablations, qualitative attention visualizations, and failure analysis",
            "Practical inference throughput and parameter scalability",
        ],
    },
    ConferenceVenue.ACL: {
        "name": "Association for Computational Linguistics (ACL)",
        "focus": "Language modeling, linguistic generalizations, prompting/reasoning paradigms, NLP benchmarks",
        "scale": "1-10 (10: Outstanding paper; 8: Strong accept; 6: Weak accept; 5: Borderline; 3: Weak reject; 1: Strong reject)",
        "criteria": [
            "Linguistic insight and NLP methodology novelty",
            "Evaluation across standard reasoning and NLP benchmarks (e.g. GSM8K, MMLU, GLUE)",
            "Human evaluation or automated metric calibration against hallucinations",
            "Dataset leakage checks and contamination mitigation",
        ],
    },
    ConferenceVenue.GENERAL: {
        "name": "General Machine Learning Conference",
        "focus": "Scientific rigor, novelty, empirical validation, reproducibility, and manuscript clarity",
        "scale": "1-10 (10: Exceptional; 8: Strong accept; 6: Weak accept; 5: Borderline; 3: Weak reject; 1: Strong reject)",
        "criteria": [
            "Conceptual novelty and formulation clarity",
            "Empirical comparison against standard baselines",
            "Ablation thoroughness and statistical reliability",
            "Writing quality, manuscript structure, and reproducibility",
        ],
    },
}

REVIEWER_PERSONAS: list[dict[str, Any]] = [
    {
        "id": "rev_theory",
        "name": "Reviewer 1",
        "role": "Theory & Conceptual Novelty Specialist",
        "instructions": (
            "You are Reviewer 1, an expert in theoretical machine learning, mathematical formulations, "
            "and conceptual novelty. Your mission is to rigorously examine:\n"
            "1. Mathematical correctness of all theorems, equations, loss objectives, and bounds.\n"
            "2. Genuine conceptual novelty: does this work represent a fundamental advance or an incremental delta?\n"
            "3. Theoretical soundess: are underlying assumptions clearly stated, realistic, and mathematically consistent?\n"
            "4. Positioning against prior art: are related theoretical works fairly cited and distinguished?"
        ),
        "focus_areas": ["Mathematical Rigor", "Novelty", "Theoretical Soundness", "Prior Art Differentiation"],
    },
    {
        "id": "rev_empirical",
        "name": "Reviewer 2",
        "role": "Empirical Validation & Benchmark Specialist",
        "instructions": (
            "You are Reviewer 2, an expert in empirical deep learning experimentation, benchmark design, "
            "and ablation analysis. Your mission is to critically scrutinize:\n"
            "1. Baseline fairness: are state-of-the-art and standard baselines tuned properly and fairly compared?\n"
            "2. Ablation completeness: is every proposed component, loss term, or hyperparameter ablated in isolation?\n"
            "3. Statistical significance: are results reported across multiple seeds with error bars / confidence intervals?\n"
            "4. Dataset breadth: are evaluations conducted on representative, diverse, and non-trivial benchmarks?\n"
            "5. Compute & Efficiency: are FLOPs, wall-clock times, and memory footprints honestly reported?"
        ),
        "focus_areas": ["Baseline Fairness", "Ablation Completeness", "Statistical Significance", "Compute Efficiency"],
    },
    {
        "id": "rev_clarity",
        "name": "Reviewer 3",
        "role": "Clarity & Reproducibility Specialist",
        "instructions": (
            "You are Reviewer 3, an expert in scientific communication, manuscript organization, and reproducibility. "
            "Your mission is to evaluate:\n"
            "1. Writing quality & exposition: are the motivation, intuition, and technical contributions clearly explained?\n"
            "2. Visualizations & tables: are diagrams, loss curves, and result tables legible, intuitive, and properly labeled?\n"
            "3. Reproducibility checklist: are all hyperparameters, training recipes, dataset splits, and seeds specified?\n"
            "4. Artifact accessibility: is code, checkpoint release, or reproducible pseudo-code provided?\n"
            "5. Structural completeness: are citations complete, BibTeX keys correct, and limitations honestly addressed?"
        ),
        "focus_areas": ["Exposition Clarity", "Reproducibility Details", "Figure/Table Quality", "Limitations & Ethics"],
    },
]

META_REVIEWER_PROMPT = """You are the Senior Area Chair / Meta-Reviewer for {venue_name}.
Your job is to read the submission and the 3 independent reviews, synthesize the committee's consensus,
reconcile conflicting perspectives with expert judgment, and issue a definitive acceptance decision.

Reviewer Committee Reports:
{reviews_summary}

Submission Title: {title}
Submission Content / Abstract:
{submission_excerpt}

Evaluation Rubric:
- Venue: {venue_name}
- Criteria: {criteria_text}

Task:
Produce a structured Meta-Review with:
1. Decision: One of ["Strong Accept", "Accept", "Weak Accept", "Borderline", "Weak Reject", "Reject", "Strong Reject"]
2. Consensus Score: Numeric value 1.0 to 10.0 representing calibrated committee verdict
3. Confidence: 1 to 5
4. Summary of Consensus: 2-3 concise paragraphs synthesizing the major points of agreement and disagreement
5. Justification: Clear rationale for the decision based on conference standards
6. Key Strengths: Bullet points of undeniable strengths
7. Primary Shortcomings: Bullet points of critical weaknesses preventing higher acceptance or requiring fixes
8. Actionable Revision Plan: 3 to 6 concrete, numbered action items for the authors to improve their paper/research
"""


def build_reviewer_system_prompt(persona: dict[str, Any], venue: ConferenceVenue) -> str:
    """Build system prompt for an individual reviewer agent."""
    rubric = CONFERENCE_RUBRICS.get(venue, CONFERENCE_RUBRICS[ConferenceVenue.GENERAL])
    criteria_str = "\n".join(f"- {c}" for c in rubric["criteria"])

    return f"""You are an expert peer reviewer for {rubric['name']}.
{persona['instructions']}

Conference Evaluation Scale: {rubric['scale']}
Core Evaluation Criteria:
{criteria_str}

Respond with a well-structured review. Your response MUST be valid JSON (or wrapped in ```json ... ```) with the following structure:
{{
  "reviewer_id": "{persona['id']}",
  "reviewer_name": "{persona['name']}",
  "role": "{persona['role']}",
  "overall_score": <integer from 1 to 10>,
  "confidence": <integer from 1 to 5>,
  "summary": "<concise 2-4 sentence summary of paper's contribution>",
  "strengths": [
    "<strength 1>",
    "<strength 2>",
    "<strength 3>"
  ],
  "weaknesses": [
    "<weakness 1>",
    "<weakness 2>",
    "<weakness 3>"
  ],
  "questions_for_authors": [
    "<question 1>",
    "<question 2>"
  ],
  "detailed_comments": "<in-depth section-by-section or thematic critique>",
  "recommendation": "<Accept / Weak Accept / Borderline / Weak Reject / Reject>",
  "criteria_scores": {{
    "novelty": <1-10>,
    "empirical_soundness": <1-10>,
    "clarity": <1-10>,
    "reproducibility": <1-10>
  }}
}}
"""


def build_reviewer_user_prompt(
    title: str,
    submission_text: str,
    context: dict[str, Any] | None = None,
) -> str:
    """Build user prompt containing the research submission text."""
    parts = []
    if title:
        parts.append(f"# Submission Title: {title}\n")
    if context:
        parts.append(f"## Research Context / Target Metrics:\n{context}\n")
    parts.append("## Submission Manuscript / Proposal Content:\n")
    parts.append(submission_text)
    return "\n".join(parts)


def build_meta_reviewer_prompt(
    venue: ConferenceVenue,
    title: str,
    submission_text: str,
    reviews_summary: str,
) -> str:
    """Build Area Chair meta-review prompt."""
    rubric = CONFERENCE_RUBRICS.get(venue, CONFERENCE_RUBRICS[ConferenceVenue.GENERAL])
    criteria_text = "; ".join(rubric["criteria"])
    excerpt = submission_text[:2000] if len(submission_text) > 2000 else submission_text

    meta_prompt = META_REVIEWER_PROMPT.format(
        venue_name=rubric["name"],
        reviews_summary=reviews_summary,
        title=title or "Untitled Research Submission",
        submission_excerpt=excerpt,
        criteria_text=criteria_text,
    )

    return f"""{meta_prompt}

Respond in structured JSON (or wrapped in ```json ... ```) with the following exact keys:
{{
  "decision": "<Strong Accept | Accept | Weak Accept | Borderline | Weak Reject | Reject | Strong Reject>",
  "decision_type": "<accept | reject | borderline>",
  "consensus_score": <float between 1.0 and 10.0>,
  "confidence": <integer from 1 to 5>,
  "summary_of_consensus": "<comprehensive synthesis of reviews>",
  "justification": "<detailed decision rationale>",
  "key_strengths": [
    "<key strength 1>",
    "<key strength 2>"
  ],
  "primary_shortcomings": [
    "<primary shortcoming 1>",
    "<primary shortcoming 2>"
  ],
  "actionable_revision_plan": [
    "<actionable revision item 1>",
    "<actionable revision item 2>",
    "<actionable revision item 3>"
  ]
}}
"""
