"""Unit tests for Ablation & Statistical Significance Engine."""

from openmlr.services.ablation_engine import (
    AblationEngine,
    compute_bootstrap_difference_ci,
    compute_cohen_d_and_hedges_g,
    compute_metrics_aggregate,
    compute_welch_t_test,
    get_significance_symbol,
    student_t_p_value,
)
from openmlr.services.ablation_types import (
    CorrectionMethod,
    SignificanceLevel,
    VariantType,
)


def test_betainc_and_student_t():
    # Symmetric t-dist df=10, t=0 -> p=1.0
    assert abs(student_t_p_value(0.0, 10.0) - 1.0) < 1e-6
    # Large t should give very small p-value
    p_large = student_t_p_value(5.0, 20.0)
    assert p_large < 0.001
    # Invalid or zero df
    assert student_t_p_value(2.0, 0.0) == 1.0
    assert student_t_p_value(float("nan"), 10.0) == 1.0


def test_compute_metrics_aggregate():
    values = [0.85, 0.86, 0.84, 0.88, 0.87]
    agg = compute_metrics_aggregate(values)
    assert agg.count == 5
    assert 0.85 <= agg.mean <= 0.87
    assert agg.std > 0
    assert agg.min_val == 0.84
    assert agg.max_val == 0.88
    assert agg.ci_lower <= agg.mean <= agg.ci_upper


def test_compute_welch_t_test():
    # Baseline vs significantly worse variant
    baseline = [0.92, 0.93, 0.91, 0.94, 0.92]
    worse_variant = [0.80, 0.81, 0.79, 0.82, 0.80]

    t_stat, p_val, df = compute_welch_t_test(baseline, worse_variant)
    assert t_stat < -10.0  # (variant - baseline) is negative
    assert p_val < 0.001
    assert df > 0


def test_cohen_d_and_hedges_g():
    baseline = [10.0, 10.5, 9.5, 10.2]
    variant = [8.0, 8.2, 7.8, 8.1]
    d, g = compute_cohen_d_and_hedges_g(baseline, variant)
    assert d < -3.0
    assert abs(g) <= abs(d)


def test_bootstrap_difference_ci():
    baseline = [100.0, 102.0, 98.0]
    variant = [90.0, 92.0, 88.0]
    lower, upper = compute_bootstrap_difference_ci(baseline, variant)
    assert lower < 0
    assert upper < 0
    assert lower <= upper


def test_significance_symbol():
    assert get_significance_symbol(0.0001) == SignificanceLevel.P_001
    assert get_significance_symbol(0.005) == SignificanceLevel.P_01
    assert get_significance_symbol(0.03) == SignificanceLevel.P_05
    assert get_significance_symbol(0.08) == SignificanceLevel.P_10
    assert get_significance_symbol(0.20) == SignificanceLevel.NS


def test_ablation_engine_workflow():
    engine = AblationEngine()
    study = engine.create_study(
        study_id="study_test_1",
        title="Attention Layer Ablation",
        description="Testing removing FlashAttention and RoPE",
        project_id="proj_1",
        primary_metric="accuracy",
        higher_is_better=True,
        baseline_variant_name="Full Model",
    )
    assert study.id == "study_test_1"
    assert "Full Model" in study.variants

    # 1. Record Baseline runs
    engine.record_variant_runs(
        study_id="study_test_1",
        variant_name="Full Model",
        variant_type=VariantType.BASELINE,
        metrics={"accuracy": [0.94, 0.95, 0.945, 0.952, 0.948], "latency_ms": [12.0, 12.5, 11.8]},
    )

    # 2. Record Ablation 1 (statistically significant drop)
    engine.record_variant_runs(
        study_id="study_test_1",
        variant_name="w/o RoPE",
        variant_type=VariantType.ABLATION,
        removed_components=["Rotary Position Embeddings"],
        metrics={"accuracy": [0.88, 0.87, 0.89, 0.875, 0.882], "latency_ms": [11.5, 11.2, 11.9]},
    )

    # 3. Record Ablation 2 (marginal change)
    engine.record_variant_runs(
        study_id="study_test_1",
        variant_name="w/o QK-Norm",
        variant_type=VariantType.ABLATION,
        removed_components=["Query-Key Normalization"],
        metrics={"accuracy": [0.942, 0.946, 0.944, 0.948, 0.945], "latency_ms": [12.1, 12.3, 11.9]},
    )

    # Analyze study
    analyzed = engine.analyze_study("study_test_1", correction_method=CorrectionMethod.HOLM_BONFERRONI)
    assert "accuracy" in analyzed.comparisons
    comparisons = analyzed.comparisons["accuracy"]
    assert len(comparisons) == 2

    # Check component impact ranking
    assert len(analyzed.component_impacts) >= 2
    # Top impact should be RoPE
    assert analyzed.component_impacts[0].component_name == "Rotary Position Embeddings"
    assert analyzed.component_impacts[0].is_critical is True

    # Check narrative
    assert "Ablation Study Summary" in analyzed.narrative_summary
    assert "Rotary Position Embeddings" in analyzed.narrative_summary

    # Generate LaTeX table
    latex = engine.generate_latex_table("study_test_1")
    assert "\\begin{table}" in latex
    assert "\\textbf{Full Model}" in latex
    assert "w/o RoPE" in latex
    assert "\\bottomrule" in latex

    # List and delete
    assert len(engine.list_studies("proj_1")) == 1
    assert engine.delete_study("study_test_1") is True
    assert engine.get_study("study_test_1") is None
