"""IngestionResult model for tracking ingestion run statistics."""

from pydantic import BaseModel, Field

from policyfoundry.ingestion.schema import NormalizedFlowLog


class IngestionResult(BaseModel):
    """Tracks the outcome of a log ingestion run.

    Provides accumulated statistics: record count, duplicates removed,
    errors skipped, source files processed, and warnings.
    """

    records: list[NormalizedFlowLog] = Field(
        default_factory=lambda: list[NormalizedFlowLog]()
    )
    total_lines: int = 0
    duplicates_removed: int = 0
    errors_skipped: int = 0
    source_files: list[str] = Field(default_factory=lambda: list[str]())
    warnings: list[str] = Field(default_factory=lambda: list[str]())
