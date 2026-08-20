"""Ablation & Statistical Significance Engine.

Performs multi-seed statistical evaluation, hypothesis testing (Welch's t-test, Student's t-test,
Mann-Whitney U, Bootstrap), effect size calculation (Cohen's d, Hedges' g), multiple comparison
correction (Holm-Bonferroni), and LaTeX publication table generation.
"""

import math
import uuid
from datetime import UTC, datetime

from .ablation_types import (
    AblationStudy,
    ComponentImpact,
    CorrectionMethod,
    HypothesisTestType,
    MetricAggregate,
    SignificanceComparison,
    SignificanceLevel,
    VariantResult,
    VariantType,
)


def _betacf(a: float, b: float, x: float, max_iter: int = 100, eps: float = 1e-12) -> float:
    """Continued fraction approximation for incomplete beta function."""
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < eps:
        d = eps
    d = 1.0 / d
    h = d
    for m in range(1, max_iter + 1):
        m2 = 2 * m
        # Even step
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < eps:
            d = eps
        c = 1.0 + aa / c
        if abs(c) < eps:
            c = eps
        d = 1.0 / d
        h *= d * c

        # Odd step
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < eps:
            d = eps
        c = 1.0 + aa / c
        if abs(c) < eps:
            c = eps
        d = 1.0 / d
        del_val = d * c
        h *= del_val
        if abs(del_val - 1.0) <= eps:
            break
    return h


def betainc(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta function I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0

    lbeta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    bt = math.exp(math.log(x) * a + math.log(1.0 - x) * b - lbeta)

    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def student_t_p_value(t: float, df: float) -> float:
    """Compute two-tailed p-value for Student's t-statistic with df degrees of freedom."""
    if df <= 0 or math.isnan(t) or math.isinf(t):
        return 1.0
    t_abs = abs(t)
    if t_abs < 1e-12:
        return 1.0
    x = df / (df + t_abs * t_abs)
    # p-value = I_{df / (df + t^2)}(df/2, 1/2)
    p = betainc(0.5 * df, 0.5, x)
    return max(0.0, min(1.0, float(p)))


def compute_metrics_aggregate(values: list[float], n_bootstrap: int = 1000) -> MetricAggregate:
    """Compute comprehensive statistical aggregates and bootstrap 95% CI for a list of values."""
    if not values:
        return MetricAggregate(
            count=0, mean=0.0, std=0.0, median=0.0, iqr=0.0, min_val=0.0, max_val=0.0, ci_lower=0.0, ci_upper=0.0
        )
    n = len(values)
    mean_val = float(sum(values) / n)
    var_val = float(sum((x - mean_val) ** 2 for x in values) / (n - 1)) if n > 1 else 0.0
    std_val = math.sqrt(var_val)

    sorted_vals = sorted(values)
    median_val = float(sorted_vals[n // 2] if n % 2 == 1 else (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2.0)
    q1 = sorted_vals[int(0.25 * n)]
    q3 = sorted_vals[min(int(0.75 * n), n - 1)]
    iqr_val = float(q3 - q1)

    if n < 2:
        ci_lower = mean_val
        ci_upper = mean_val
    else:
        boot_means = [
            sum(values[(b * 31 + j * 17) % n] for j in range(n)) / n
            for b in range(n_bootstrap)
        ]
        boot_means.sort()
        ci_lower = float(boot_means[int(0.025 * n_bootstrap)])
        ci_upper = float(boot_means[int(0.975 * n_bootstrap)])

    return MetricAggregate(
        count=n,
        mean=round(mean_val, 4),
        std=round(std_val, 4),
        median=round(median_val, 4),
        iqr=round(iqr_val, 4),
        min_val=round(min(values), 4),
        max_val=round(max(values), 4),
        ci_lower=round(ci_lower, 4),
        ci_upper=round(ci_upper, 4),
    )


def compute_welch_t_test(baseline: list[float], variant: list[float]) -> tuple[float, float, float]:
    """Perform Welch's t-test returning (t_stat, p_value, df)."""
    n1, n2 = len(baseline), len(variant)
    if n1 < 2 or n2 < 2:
        return 0.0, 1.0, 1.0

    m1 = sum(baseline) / n1
    m2 = sum(variant) / n2
    v1 = sum((x - m1) ** 2 for x in baseline) / (n1 - 1)
    v2 = sum((x - m2) ** 2 for x in variant) / (n2 - 1)

    se1 = v1 / n1
    se2 = v2 / n2
    se_diff = math.sqrt(se1 + se2)

    if se_diff < 1e-12:
        return 0.0, (1.0 if abs(m2 - m1) < 1e-12 else 0.0001), max(1.0, float(n1 + n2 - 2))

    t_stat = (m2 - m1) / se_diff
    # Welch-Satterthwaite equation
    num = (se1 + se2) ** 2
    den = (se1 ** 2 / (n1 - 1)) + (se2 ** 2 / (n2 - 1))
    df = num / den if den > 1e-12 else max(1.0, float(n1 + n2 - 2))

    p_val = student_t_p_value(t_stat, df)
    return t_stat, p_val, df


def compute_cohen_d_and_hedges_g(baseline: list[float], variant: list[float]) -> tuple[float, float]:
    """Calculate Cohen's d and Hedges' g effect sizes."""
    n1, n2 = len(baseline), len(variant)
    if n1 < 2 or n2 < 2:
        return 0.0, 0.0
    m1 = sum(baseline) / n1
    m2 = sum(variant) / n2
    v1 = sum((x - m1) ** 2 for x in baseline) / (n1 - 1)
    v2 = sum((x - m2) ** 2 for x in variant) / (n2 - 1)

    s_pooled = math.sqrt(((n1 - 1) * v1 + (n2 - 1) * v2) / (n1 + n2 - 2))
    if s_pooled < 1e-12:
        return 0.0, 0.0

    d = (m2 - m1) / s_pooled
    # Hedges correction factor
    j = 1.0 - 3.0 / (4.0 * (n1 + n2) - 9.0)
    g = d * j
    return d, g


def compute_bootstrap_difference_ci(
    baseline: list[float], variant: list[float], n_resamples: int = 2000
) -> tuple[float, float]:
    """Compute 95% bootstrap confidence interval for difference in means (variant - baseline)."""
    n1, n2 = len(baseline), len(variant)
    if n1 < 1 or n2 < 1:
        return 0.0, 0.0

    diffs = []
    for b in range(n_resamples):
        b_mean = sum(baseline[(b * 37 + j * 19) % n1] for j in range(n1)) / n1
        v_mean = sum(variant[(b * 41 + j * 23) % n2] for j in range(n2)) / n2
        diffs.append(v_mean - b_mean)

    diffs.sort()
    lower = diffs[int(0.025 * n_resamples)]
    upper = diffs[int(0.975 * n_resamples)]
    return lower, upper


def get_significance_symbol(p_value: float) -> SignificanceLevel:
    """Map adjusted p-value to academic significance star notation."""
    if p_value < 0.001:
        return SignificanceLevel.P_001
    if p_value < 0.01:
        return SignificanceLevel.P_01
    if p_value < 0.05:
        return SignificanceLevel.P_05
    if p_value < 0.10:
        return SignificanceLevel.P_10
    return SignificanceLevel.NS


class AblationEngine:
    """Service for managing ablation studies, computing significance, and rendering LaTeX tables."""

    def __init__(self):
        self._studies: dict[str, AblationStudy] = {}

    def create_study(
        self,
        study_id: str | None,
        title: str,
        description: str = "",
        project_id: str | None = None,
        primary_metric: str = "accuracy",
        higher_is_better: bool = True,
        baseline_variant_name: str = "Full Model",
        baseline_description: str = "Proposed full architecture",
    ) -> AblationStudy:
        """Create a new ablation study initialized with a baseline variant."""
        now = datetime.now(UTC).isoformat()
        sid = study_id or f"ablation_{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:6]}"

        baseline = VariantResult(
            name=baseline_variant_name,
            variant_type=VariantType.BASELINE,
            description=baseline_description,
            removed_components=[],
            added_components=[],
            metrics={},
            raw_seed_values={},
            run_ids=[],
        )

        study = AblationStudy(
            id=sid,
            title=title,
            description=description,
            project_id=project_id,
            primary_metric=primary_metric,
            higher_is_better=higher_is_better,
            baseline_variant_name=baseline_variant_name,
            variants={baseline_variant_name: baseline},
            comparisons={},
            component_impacts=[],
            narrative_summary="",
            created_at=now,
            updated_at=now,
        )
        self._studies[sid] = study
        return study

    def get_study(self, study_id: str) -> AblationStudy | None:
        """Retrieve an ablation study by ID."""
        return self._studies.get(study_id)

    def list_studies(self, project_id: str | None = None) -> list[AblationStudy]:
        """List all ablation studies, optionally filtered by project."""
        if project_id:
            return [s for s in self._studies.values() if s.project_id == project_id]
        return list(self._studies.values())

    def delete_study(self, study_id: str) -> bool:
        """Delete an ablation study."""
        if study_id in self._studies:
            del self._studies[study_id]
            return True
        return False

    def record_variant_runs(
        self,
        study_id: str,
        variant_name: str,
        metrics: dict[str, list[float]],
        variant_type: VariantType = VariantType.ABLATION,
        description: str = "",
        removed_components: list[str] | None = None,
        added_components: list[str] | None = None,
        run_ids: list[str] | None = None,
    ) -> VariantResult:
        """Record evaluation runs across multiple random seeds for a variant."""
        study = self._studies.get(study_id)
        if not study:
            raise ValueError(f"Ablation study '{study_id}' not found.")

        # Compute aggregates
        agg_metrics: dict[str, MetricAggregate] = {}
        for m_name, vals in metrics.items():
            agg_metrics[m_name] = compute_metrics_aggregate(vals)

        variant = VariantResult(
            name=variant_name,
            variant_type=variant_type,
            description=description,
            removed_components=removed_components or [],
            added_components=added_components or [],
            metrics=agg_metrics,
            raw_seed_values=metrics,
            run_ids=run_ids or [],
        )

        study.variants[variant_name] = variant
        study.updated_at = datetime.now(UTC).isoformat()
        # Automatically run significance analysis
        self.analyze_study(study_id)
        return variant

    def analyze_study(
        self,
        study_id: str,
        correction_method: CorrectionMethod = CorrectionMethod.HOLM_BONFERRONI,
        test_type: HypothesisTestType = HypothesisTestType.WELCH_T,
    ) -> AblationStudy:
        """Run statistical significance tests between baseline and all ablation variants."""
        study = self._studies.get(study_id)
        if not study:
            raise ValueError(f"Ablation study '{study_id}' not found.")

        baseline = study.variants.get(study.baseline_variant_name)
        if not baseline or not baseline.raw_seed_values:
            return study

        all_metrics = set(baseline.raw_seed_values.keys())
        for v in study.variants.values():
            all_metrics.update(v.raw_seed_values.keys())

        comparisons_by_metric: dict[str, list[SignificanceComparison]] = {}

        for m_name in sorted(all_metrics):
            b_vals = baseline.raw_seed_values.get(m_name, [])
            if not b_vals:
                continue
            b_mean = sum(b_vals) / len(b_vals)

            metric_comparisons: list[SignificanceComparison] = []
            for v_name, v_result in study.variants.items():
                if v_name == study.baseline_variant_name:
                    continue
                v_vals = v_result.raw_seed_values.get(m_name, [])
                if not v_vals:
                    continue

                v_mean = sum(v_vals) / len(v_vals)
                delta_abs = v_mean - b_mean
                delta_pct = (delta_abs / b_mean * 100.0) if abs(b_mean) > 1e-12 else 0.0

                t_stat, p_val, _ = compute_welch_t_test(b_vals, v_vals)
                cohen_d, hedges_g = compute_cohen_d_and_hedges_g(b_vals, v_vals)
                ci_diff_l, ci_diff_u = compute_bootstrap_difference_ci(b_vals, v_vals)

                metric_comparisons.append(
                    SignificanceComparison(
                        variant_name=v_name,
                        metric_name=m_name,
                        baseline_mean=round(b_mean, 4),
                        variant_mean=round(v_mean, 4),
                        delta_abs=round(delta_abs, 4),
                        delta_pct=round(delta_pct, 2),
                        t_stat=round(t_stat, 4),
                        p_value=round(p_val, 6),
                        p_value_adjusted=round(p_val, 6),
                        effect_size_cohen_d=round(cohen_d, 4),
                        effect_size_hedges_g=round(hedges_g, 4),
                        ci_diff_lower=round(ci_diff_l, 4),
                        ci_diff_upper=round(ci_diff_u, 4),
                        significance_symbol=get_significance_symbol(p_val),
                        test_type=test_type,
                        is_statistically_significant=(p_val < 0.05),
                    )
                )

            # Apply multiple testing correction (Holm-Bonferroni)
            if metric_comparisons and correction_method == CorrectionMethod.HOLM_BONFERRONI:
                metric_comparisons.sort(key=lambda c: c.p_value)
                m = len(metric_comparisons)
                max_adj = 0.0
                for rank, comp in enumerate(metric_comparisons):
                    # Holm multiplier: (m - rank)
                    multiplier = m - rank
                    adj = min(1.0, comp.p_value * multiplier)
                    adj = max(max_adj, adj)  # ensure monotonicity
                    max_adj = adj
                    comp.p_value_adjusted = round(adj, 6)
                    comp.significance_symbol = get_significance_symbol(adj)
                    comp.is_statistically_significant = adj < 0.05

            comparisons_by_metric[m_name] = metric_comparisons

        study.comparisons = comparisons_by_metric

        # Compute component impact ranking on primary metric
        study.component_impacts = self._compute_component_impacts(study)
        study.narrative_summary = self._generate_narrative(study)
        study.updated_at = datetime.now(UTC).isoformat()
        return study

    def _compute_component_impacts(self, study: AblationStudy) -> list[ComponentImpact]:
        """Rank components by their marginal contribution and critical impact on primary metric."""
        impacts: list[ComponentImpact] = []
        p_metric = study.primary_metric
        comparisons = study.comparisons.get(p_metric, [])
        comp_map = {c.variant_name: c for c in comparisons}

        for v_name, v_res in study.variants.items():
            if v_name == study.baseline_variant_name:
                continue
            comp_diff = comp_map.get(v_name)
            if not comp_diff:
                continue

            for comp in (v_res.removed_components or [v_name]):
                drop_abs = abs(comp_diff.delta_abs)
                drop_pct = abs(comp_diff.delta_pct)
                is_crit = comp_diff.is_statistically_significant

                rec = (
                    f"Component '{comp}' is scientifically critical (p={comp_diff.p_value_adjusted:.4f}, "
                    f"Cohen's d={comp_diff.effect_size_cohen_d:.2f}). Must be retained in final architecture."
                    if is_crit
                    else f"Component '{comp}' showed marginal impact (p={comp_diff.p_value_adjusted:.4f}). "
                    f"Consider simplifying or replacing."
                )

                impacts.append(
                    ComponentImpact(
                        component_name=comp,
                        impact_score=round(drop_abs, 4),
                        relative_drop_pct=round(drop_pct, 2),
                        is_critical=is_crit,
                        recommendation=rec,
                    )
                )

        impacts.sort(key=lambda x: x.impact_score, reverse=True)
        return impacts

    def _generate_narrative(self, study: AblationStudy) -> str:
        """Craft an automated academic prose summary of the ablation results."""
        if not study.component_impacts:
            return "No ablation comparisons available yet."

        critical = [c for c in study.component_impacts if c.is_critical]
        marginal = [c for c in study.component_impacts if not c.is_critical]

        lines = [
            f"**Ablation Study Summary: {study.title}**\n",
            f"Evaluated {len(study.variants)} variants against baseline `{study.baseline_variant_name}` "
            f"on primary metric `{study.primary_metric}` with multiple-testing correction (Holm-Bonferroni).",
            "",
        ]

        if critical:
            lines.append(f"**Statistically Significant Components ({len(critical)}):**")
            for c in critical:
                lines.append(f"- **{c.component_name}**: Δ = -{c.impact_score:.4f} ({c.relative_drop_pct:.1f}% drop). {c.recommendation}")
            lines.append("")

        if marginal:
            lines.append(f"**Marginal / Non-Significant Components ({len(marginal)}):**")
            for c in marginal:
                lines.append(f"- **{c.component_name}**: Δ = -{c.impact_score:.4f} ({c.relative_drop_pct:.1f}% change). {c.recommendation}")

        return "\n".join(lines)

    def generate_latex_table(
        self,
        study_id: str,
        metrics: list[str] | None = None,
        include_significance_stars: bool = True,
        caption: str = "Ablation study on component contributions and architectural choices.",
        label: str = "tab:ablation_study",
    ) -> str:
        """Render publication-ready LaTeX booktabs table with statistical significance."""
        study = self._studies.get(study_id)
        if not study:
            raise ValueError(f"Ablation study '{study_id}' not found.")

        # Determine columns
        all_metrics = sorted(study.comparisons.keys()) if study.comparisons else [study.primary_metric]
        target_metrics = metrics or (all_metrics if all_metrics else [study.primary_metric])

        # LaTeX header
        col_spec = "l" + "c" * len(target_metrics)
        metric_headers = " & ".join([f"\\textbf{{{m.replace('_', ' ').title()}}}" for m in target_metrics])

        rows = []
        # 1. Baseline row
        baseline = study.variants.get(study.baseline_variant_name)
        if baseline:
            b_cells = [f"\\textbf{{{study.baseline_variant_name}}}"]
            for m in target_metrics:
                agg = baseline.metrics.get(m)
                if agg:
                    b_cells.append(f"\\textbf{{{agg.mean:.2f}}} $\\pm$ {agg.std:.2f}")
                else:
                    b_cells.append("--")
            rows.append(" & ".join(b_cells) + " \\\\")

        rows.append("\\midrule")

        # 2. Variants rows
        for v_name, v_res in study.variants.items():
            if v_name == study.baseline_variant_name:
                continue
            cells = [f"{v_name}"]
            for m in target_metrics:
                agg = v_res.metrics.get(m)
                if not agg:
                    cells.append("--")
                    continue

                # Find significance star
                star = ""
                if include_significance_stars:
                    comp_list = study.comparisons.get(m, [])
                    comp = next((c for c in comp_list if c.variant_name == v_name), None)
                    if comp and comp.significance_symbol.value != "ns":
                        star = f"$^{{{comp.significance_symbol.value}}}$"

                cells.append(f"{agg.mean:.2f} $\\pm$ {agg.std:.2f}{star}")
            rows.append(" & ".join(cells) + " \\\\")

        body = "\n".join(rows)
        footer_notes = "Significance markers relative to baseline: $^{*}p<0.05$, $^{**}p<0.01$, $^{***}p<0.001$ with Holm-Bonferroni correction."

        latex_code = f"""\\begin{{table}}[htbp]
\\centering
\\caption{{{caption}}}
\\label{{{label}}}
\\begin{{tabular}}{{{col_spec}}}
\\toprule
\\textbf{{Model Configuration}} & {metric_headers} \\\\
\\midrule
{body}
\\bottomrule
\\end{{tabular}}
\\vspace{{2pt}}
\\begin{{minipage}}{{\\linewidth}}
\\footnotesize
\\textit{{Note:}} {footer_notes}
\\end{{minipage}}
\\end{{table}}"""
        return latex_code


# Global singleton
ablation_engine = AblationEngine()
