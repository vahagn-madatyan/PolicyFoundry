"""Pipeline prompt templates and formatting functions."""

from policyfoundry.pipeline.prompts.analyze import ANALYZE_SYSTEM_PROMPT
from policyfoundry.pipeline.prompts.assess import ASSESS_SYSTEM_PROMPT
from policyfoundry.pipeline.prompts.decide import DECIDE_SYSTEM_PROMPT
from policyfoundry.pipeline.prompts.generate import GENERATE_SYSTEM_PROMPT

__all__ = [
    "ANALYZE_SYSTEM_PROMPT",
    "ASSESS_SYSTEM_PROMPT",
    "DECIDE_SYSTEM_PROMPT",
    "GENERATE_SYSTEM_PROMPT",
]
