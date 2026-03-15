"""Log ingestion pipeline: parse, deduplicate, and ingest flow logs."""

from policyfoundry.ingestion.column_detect import detect_columns
from policyfoundry.ingestion.dedup import compute_dedup_key
from policyfoundry.ingestion.excel import ingest_excel_file
from policyfoundry.ingestion.excel_schema import (
    ColumnMapping,
    ExcelIngestionResult,
    ExcelTrafficRecord,
)
from policyfoundry.ingestion.local import ingest_local_files
from policyfoundry.ingestion.parser import parse_vpc_flow_log_line
from policyfoundry.ingestion.result import IngestionResult
from policyfoundry.ingestion.s3 import ingest_from_s3

__all__ = [
    "ColumnMapping",
    "ExcelIngestionResult",
    "ExcelTrafficRecord",
    "IngestionResult",
    "compute_dedup_key",
    "detect_columns",
    "ingest_excel_file",
    "ingest_from_s3",
    "ingest_local_files",
    "parse_vpc_flow_log_line",
]
