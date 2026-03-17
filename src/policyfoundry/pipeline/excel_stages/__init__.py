"""Excel pipeline stage functions."""

from policyfoundry.pipeline.excel_stages.analyze import excel_analyze_stage
from policyfoundry.pipeline.excel_stages.assess import excel_assess_stage
from policyfoundry.pipeline.excel_stages.decide import excel_decide_stage
from policyfoundry.pipeline.excel_stages.generate import excel_generate_stage
from policyfoundry.pipeline.excel_stages.validate import excel_validate_proposals

__all__ = [
    "excel_analyze_stage",
    "excel_assess_stage",
    "excel_decide_stage",
    "excel_generate_stage",
    "excel_validate_proposals",
]
