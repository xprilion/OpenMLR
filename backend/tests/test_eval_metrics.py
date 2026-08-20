"""Tests for evaluation metrics in the OpenMLR benchmark harness."""

import pytest

from openmlr.eval.metrics import (
    BenchmarkAggregateSummary,
    HypothesisMetric,
    MetricTolerance,
    ReproductionMetric,
    SpeedupMetric,
)


class TestMetricTolerance:
    def test_within_relative_tolerance(self):
        tol = MetricTolerance(relative_tolerance=0.05, absolute_tolerance=0.01)
        assert tol.is_within_tolerance(100.0, 104.0) is True
        assert tol.is_within_tolerance(100.0, 95.5) is True
        assert tol.is_within_tolerance(100.0, 90.0) is False

    def test_within_absolute_tolerance_when_target_zero(self):
        tol = MetricTolerance(relative_tolerance=0.05, absolute_tolerance=0.02)
        assert tol.is_within_tolerance(0.0, 0.01) is True
        assert tol.is_within_tolerance(0.0, 0.05) is False


class TestReproductionMetric:
    def test_successful_accuracy_reproduction(self):
        metric = ReproductionMetric(
            metric_name="accuracy",
            reported_value=0.930,
            reproduced_value=0.925,
            tolerance=MetricTolerance(relative_tolerance=0.02),
            lower_is_better=False,
        )
        assert metric.is_successful is True
        assert metric.percentage_error == pytest.approx((0.005 / 0.930) * 100, rel=1e-3)
        assert metric.absolute_delta == pytest.approx(0.005, rel=1e-4)

    def test_higher_value_better_than_reported(self):
        metric = ReproductionMetric(
            metric_name="accuracy",
            reported_value=0.930,
            reproduced_value=0.950,
            lower_is_better=False,
        )
        assert metric.is_successful is True

    def test_lower_is_better_loss_reproduction(self):
        metric = ReproductionMetric(
            metric_name="val_loss",
            reported_value=1.45,
            reproduced_value=1.35,  # Better than reported
            lower_is_better=True,
        )
        assert metric.is_successful is True

    def test_failed_reproduction_outside_tolerance(self):
        metric = ReproductionMetric(
            metric_name="accuracy",
            reported_value=0.930,
            reproduced_value=0.850,
            tolerance=MetricTolerance(relative_tolerance=0.03),
            lower_is_better=False,
        )
        assert metric.is_successful is False

    def test_to_dict(self):
        metric = ReproductionMetric(
            metric_name="accuracy",
            reported_value=0.90,
            reproduced_value=0.90,
        )
        d = metric.to_dict()
        assert d["metric_name"] == "accuracy"
        assert d["is_successful"] is True
        assert d["percentage_error"] == 0.0


class TestSpeedupMetric:
    def test_speedup_success_exceeds_target(self):
        speedup = SpeedupMetric(
            baseline_latency_ms=30.0,
            optimized_latency_ms=15.0,
            target_speedup=1.5,
            baseline_memory_mb=1000.0,
            optimized_memory_mb=600.0,
            numerical_correctness_passed=True,
        )
        assert speedup.speedup_ratio == pytest.approx(2.0, rel=1e-3)
        assert speedup.latency_reduction_pct == pytest.approx(50.0, rel=1e-3)
        assert speedup.memory_reduction_ratio == pytest.approx(1.667, rel=1e-2)
        assert speedup.is_successful is True

    def test_speedup_fails_on_numerical_mismatch(self):
        speedup = SpeedupMetric(
            baseline_latency_ms=30.0,
            optimized_latency_ms=10.0,  # 3.0x speedup
            target_speedup=1.5,
            numerical_correctness_passed=False,  # Failed check
        )
        assert speedup.is_successful is False

    def test_speedup_fails_below_target(self):
        speedup = SpeedupMetric(
            baseline_latency_ms=30.0,
            optimized_latency_ms=25.0,  # 1.2x speedup
            target_speedup=1.5,
            numerical_correctness_passed=True,
        )
        assert speedup.is_successful is False

    def test_to_dict(self):
        speedup = SpeedupMetric(
            baseline_latency_ms=20.0,
            optimized_latency_ms=10.0,
        )
        d = speedup.to_dict()
        assert d["speedup_ratio"] == 2.0
        assert d["is_successful"] is True


class TestHypothesisMetric:
    def test_high_quality_hypothesis_succeeds(self):
        hyp = HypothesisMetric(
            novelty_score=0.90,
            soundness_score=0.85,
            testability_score=0.80,
            clarity_score=0.90,
            min_passing_score=0.70,
        )
        assert hyp.composite_score >= 0.80
        assert hyp.is_successful is True

    def test_low_quality_hypothesis_fails(self):
        hyp = HypothesisMetric(
            novelty_score=0.40,
            soundness_score=0.50,
            testability_score=0.30,
            clarity_score=0.50,
            min_passing_score=0.70,
        )
        assert hyp.composite_score < 0.70
        assert hyp.is_successful is False

    def test_to_dict(self):
        hyp = HypothesisMetric(
            novelty_score=0.8,
            soundness_score=0.8,
            testability_score=0.8,
            clarity_score=0.8,
        )
        d = hyp.to_dict()
        assert d["is_successful"] is True
        assert d["composite_score"] == pytest.approx(0.8, rel=1e-3)


class TestBenchmarkAggregateSummary:
    def test_summary_statistics_and_confidence_interval(self):
        summary = BenchmarkAggregateSummary(
            total_tasks=4,
            passed_tasks=3,
            failed_tasks=1,
            errored_tasks=0,
            total_execution_time_s=12.0,
            task_latencies_s=[2.5, 3.0, 3.5, 3.0],
            speedup_ratios=[1.8, 2.2],
            reproduction_percentage_errors=[2.1, 3.4],
            hypothesis_scores=[0.85, 0.78],
        )
        assert summary.pass_rate == 0.75
        assert summary.mean_task_latency_s == 3.0
        assert summary.mean_speedup == pytest.approx(2.0, rel=1e-3)
        assert summary.mean_reproduction_mape == pytest.approx(2.75, rel=1e-3)
        assert summary.mean_hypothesis_score == pytest.approx(0.815, rel=1e-3)

        ci = summary.calculate_confidence_interval([1.0, 2.0, 3.0, 4.0, 5.0])
        assert ci[0] < 3.0 < ci[1]

        d = summary.to_dict()
        assert d["pass_rate_percentage"] == 75.0
        assert d["total_tasks"] == 4
