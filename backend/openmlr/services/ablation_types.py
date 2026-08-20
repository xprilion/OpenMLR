"""Type definitions and Pydantic data models for the Ablation & Statistical Significance Engine."""

from enum import Enum

from pydantic import BaseModel, Field


class SignificanceLevel(str, Enum):
    """Standard academic statistical significance notation."""
    P_001 = "***"   # p < 0.001
    P_01 = "**"     # p < 0.01
    P_05 = "*"      # p < 0.05
    P_10 = "."      # p < 0.10
    NS = "ns"       # not significant (p >= 0.10)


class HypothesisTestType(str, Enum):
    """Statistical hypothesis testing methods."""
    STUDENT_T = "student_t"
    WELCH_T = "welch_t"
    MANN_WHITNEY = "mann_whitney"
    BOOTSTRAP = "bootstrap"


class CorrectionMethod(str, Enum):
    """Multiple comparison correction methods."""
    HOLM_BONFERRONI = "holm_bonferroni"
    BENJAMINI_HOCHBERG = "benjamini_hochberg"
    NONE = "none"


class VariantType(str, Enum):
    """Type of research model/method configuration."""
    BASELINE = "baseline"
    ABLATION = "ablation"
    ADDITION = "addition"
    MODIFICATION = "modification"


class MetricAggregate(BaseModel):
    """Statistical summary of multi-seed metric evaluation runs."""
    count: int = Field(..., description="Number of independent seed evaluations")
    mean: float = Field(..., description="Sample mean")
    std: float = Field(..., description="Sample standard deviation")
    median: float = Field(..., description="Sample median")
    iqr: float = Field(..., description="Interquartile range")
    min_val: float = Field(..., description="Minimum recorded value")
    max_val: float = Field(..., description="Maximum recorded value")
    ci_lower: float = Field(..., description="95% confidence interval lower bound")
    ci_upper: float = Field(..., description="95% confidence interval upper bound")


class VariantResult(BaseModel):
    """Evaluation result for an ablation or baseline variant."""
    name: str = Field(..., description="Variant unique name / label")
    variant_type: VariantType = Field(default=VariantType.ABLATION)
    description: str = Field(default="")
    removed_components: list[str] = Field(default_factory=list, description="Components omitted in this ablation")
    added_components: list[str] = Field(default_factory=list, description="Components added in this variant")
    metrics: dict[str, MetricAggregate] = Field(default_factory=dict, description="Aggregated metric statistics")
    raw_seed_values: dict[str, list[float]] = Field(default_factory=dict, description="Raw per-seed numeric values")
    run_ids: list[str] = Field(default_factory=list, description="Associated experiment run IDs")


class SignificanceComparison(BaseModel):
    """Pairwise statistical hypothesis test between baseline and an ablation variant."""
    variant_name: str = Field(..., description="Ablated or modified variant name")
    metric_name: str = Field(..., description="Target metric name")
    baseline_mean: float = Field(..., description="Mean of the baseline model")
    variant_mean: float = Field(..., description="Mean of the variant")
    delta_abs: float = Field(..., description="Absolute change: variant_mean - baseline_mean")
    delta_pct: float = Field(..., description="Percentage change relative to baseline")
    t_stat: float = Field(..., description="Computed test statistic")
    p_value: float = Field(..., description="Raw two-tailed p-value")
    p_value_adjusted: float = Field(..., description="Multiple testing adjusted p-value")
    effect_size_cohen_d: float = Field(..., description="Standardized effect size (Cohen's d)")
    effect_size_hedges_g: float = Field(..., description="Sample-size corrected effect size (Hedges' g)")
    ci_diff_lower: float = Field(..., description="95% CI of the mean difference lower bound")
    ci_diff_upper: float = Field(..., description="95% CI of the mean difference upper bound")
    significance_symbol: SignificanceLevel = Field(..., description="Significance marker (***, **, *, ., ns)")
    test_type: HypothesisTestType = Field(default=HypothesisTestType.WELCH_T)
    is_statistically_significant: bool = Field(..., description="True if adjusted p < 0.05")


class ComponentImpact(BaseModel):
    """Component contribution analysis ranking."""
    component_name: str = Field(..., description="Name of the isolated component or technique")
    impact_score: float = Field(..., description="Absolute degradation or contribution magnitude")
    relative_drop_pct: float = Field(..., description="Percentage drop when removed")
    is_critical: bool = Field(..., description="Whether removal causes statistically significant drop")
    recommendation: str = Field(..., description="Actionable recommendation for final architecture")


class AblationStudy(BaseModel):
    """Complete ablation study container."""
    id: str = Field(..., description="Unique study identifier")
    title: str = Field(..., description="Title of the ablation study")
    description: str = Field(default="")
    project_id: str | None = Field(default=None)
    primary_metric: str = Field(default="accuracy", description="Primary performance metric")
    higher_is_better: bool = Field(default=True, description="Whether higher values represent better performance")
    baseline_variant_name: str = Field(..., description="Name of the full/baseline variant")
    variants: dict[str, VariantResult] = Field(default_factory=dict, description="Map of variant names to results")
    comparisons: dict[str, list[SignificanceComparison]] = Field(
        default_factory=dict, description="Pairwise statistical comparisons per metric"
    )
    component_impacts: list[ComponentImpact] = Field(default_factory=list)
    narrative_summary: str = Field(default="", description="Auto-generated scientific prose report")
    created_at: str = Field(..., description="Creation timestamp ISO")
    updated_at: str = Field(..., description="Last update timestamp ISO")


class CreateStudyRequest(BaseModel):
    """Request payload for creating an ablation study."""
    id: str | None = None
    title: str
    description: str = ""
    project_id: str | None = None
    primary_metric: str = "accuracy"
    higher_is_better: bool = True
    baseline_variant_name: str = "Full Model"
    baseline_description: str = "Proposed full architecture with all components"


class RecordRunsRequest(BaseModel):
    """Request payload for recording runs for a variant."""
    variant_name: str
    variant_type: VariantType = VariantType.ABLATION
    description: str = ""
    removed_components: list[str] = Field(default_factory=list)
    added_components: list[str] = Field(default_factory=list)
    metrics: dict[str, list[float]] = Field(..., description="Map of metric names to lists of seed values")
    run_ids: list[str] = Field(default_factory=list)


class AnalyzeStudyRequest(BaseModel):
    """Request payload to trigger statistical significance analysis."""
    correction_method: CorrectionMethod = CorrectionMethod.HOLM_BONFERRONI
    test_type: HypothesisTestType = HypothesisTestType.WELCH_T


class LatexTableRequest(BaseModel):
    """Request payload for LaTeX table generation."""
    metrics: list[str] | None = None
    include_significance_stars: bool = True
    caption: str = "Ablation study on component contributions and architectural choices."
    label: str = "tab:ablation_study"
