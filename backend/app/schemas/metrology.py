from pydantic import BaseModel, Field


class MetrologyProfileRead(BaseModel):
    profile_key: str
    display_name: str
    magnitude: str
    required_inputs: list[str]
    supported_units: list[str]
    uncertainty_components: list[str]
    result_columns: list[str]
    notes: str | None = None


class MetrologyPreviewInput(BaseModel):
    profile_key: str = Field(min_length=1, max_length=80)
    reference_value: float
    indications: list[float] = Field(min_length=1)
    resolution: float = Field(gt=0)
    pattern_uncertainty: float | None = Field(default=None, gt=0)
    k: float = Field(default=2.0, gt=0)


class MetrologyPreviewResult(BaseModel):
    average: float
    error: float
    repeatability_uncertainty: float
    resolution_uncertainty: float
    combined_uncertainty: float
    expanded_uncertainty: float
