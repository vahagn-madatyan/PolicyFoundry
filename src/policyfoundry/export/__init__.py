"""Export package — generates change request forms from pipeline state.

Public API:
    - ChangeRequestEntry: flattened display-ready row for export
    - flatten_to_entries: convert ExcelPipelineState → list[ChangeRequestEntry]
    - export_xlsx: write xlsx change request form (default or custom template)
    - export_pdf: write PDF change request document
"""

from policyfoundry.export.change_request import export_pdf, export_xlsx
from policyfoundry.export.models import ChangeRequestEntry, flatten_to_entries

__all__ = [
    "ChangeRequestEntry",
    "export_pdf",
    "export_xlsx",
    "flatten_to_entries",
]
