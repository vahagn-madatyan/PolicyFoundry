"""Excel pipeline prompt templates and formatting functions."""

from policyfoundry.pipeline.excel_prompts.analyze import EXCEL_ANALYZE_SYSTEM_PROMPT
from policyfoundry.pipeline.excel_prompts.assess import EXCEL_ASSESS_SYSTEM_PROMPT
from policyfoundry.pipeline.excel_prompts.decide import EXCEL_DECIDE_SYSTEM_PROMPT
from policyfoundry.pipeline.excel_prompts.generate import EXCEL_GENERATE_SYSTEM_PROMPT

__all__ = [
    "EXCEL_ANALYZE_SYSTEM_PROMPT",
    "EXCEL_ASSESS_SYSTEM_PROMPT",
    "EXCEL_DECIDE_SYSTEM_PROMPT",
    "EXCEL_GENERATE_SYSTEM_PROMPT",
]
