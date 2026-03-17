"""Tests for PDF change request export.

Verifies:
- Valid PDF output (magic bytes, non-trivial size)
- Metadata presence (run_id, title, rule count)
- Data rows from proposals/decisions
- Empty proposals edge case
- ExportError on write failure
"""

from __future__ import annotations

import zlib
from pathlib import Path

import pytest

from policyfoundry.exceptions import ExportError
from policyfoundry.export.change_request import export_pdf
from policyfoundry.export.models import flatten_to_entries
from policyfoundry.pipeline.excel_state import ExcelPipelineState


def _extract_pdf_text(pdf_path: Path) -> str:
    """Decompress FlateDecode streams from a PDF and return all text.

    fpdf2 compresses page content with zlib. This extracts and
    decompresses all streams so we can search for rendered text.
    """
    raw = pdf_path.read_bytes()
    parts: list[bytes] = []
    i = 0
    while True:
        # Try both line-ending variants
        start = raw.find(b"stream\n", i)
        offset = len(b"stream\n")
        if start == -1:
            start = raw.find(b"stream\r\n", i)
            offset = len(b"stream\r\n")
        if start == -1:
            break
        start += offset
        end = raw.find(b"endstream", start)
        if end == -1:
            break
        compressed = raw[start:end].rstrip()
        try:
            parts.append(zlib.decompress(compressed))
        except zlib.error:
            parts.append(compressed)
        i = end
    return b"".join(parts).decode("latin-1")


class TestExportPdfStructure:
    """Verify that export_pdf produces a valid PDF file."""

    def test_produces_valid_pdf_magic_bytes(
        self,
        sample_excel_state: ExcelPipelineState,
        tmp_path: Path,
    ) -> None:
        """Output file starts with %PDF magic bytes."""
        out = tmp_path / "change_request.pdf"
        result = export_pdf(sample_excel_state, out)

        assert result == out
        assert out.exists()

        raw = out.read_bytes()
        assert raw[:5] == b"%PDF-"

    def test_produces_nonzero_file(
        self,
        sample_excel_state: ExcelPipelineState,
        tmp_path: Path,
    ) -> None:
        """Output file has meaningful size (not just headers)."""
        out = tmp_path / "change_request.pdf"
        export_pdf(sample_excel_state, out)

        # With 2 data rows + metadata, should be well above 1KB
        assert out.stat().st_size > 1000

    def test_returns_path_object(
        self,
        sample_excel_state: ExcelPipelineState,
        tmp_path: Path,
    ) -> None:
        """Return value is a Path to the written file."""
        out = tmp_path / "output.pdf"
        result = export_pdf(sample_excel_state, out)
        assert isinstance(result, Path)
        assert result == out


class TestExportPdfMetadata:
    """Verify metadata header content in the generated PDF."""

    def test_contains_run_id(
        self,
        sample_excel_state: ExcelPipelineState,
        tmp_path: Path,
    ) -> None:
        """PDF content includes the run_id from pipeline state."""
        out = tmp_path / "change_request.pdf"
        export_pdf(sample_excel_state, out)

        text = _extract_pdf_text(out)
        run_id = sample_excel_state["run_id"]
        assert isinstance(run_id, str)
        assert run_id in text

    def test_contains_title(
        self,
        sample_excel_state: ExcelPipelineState,
        tmp_path: Path,
    ) -> None:
        """PDF content includes the document title."""
        out = tmp_path / "change_request.pdf"
        export_pdf(sample_excel_state, out)

        text = _extract_pdf_text(out)
        assert "Firewall Change Request" in text

    def test_contains_rule_count(
        self,
        sample_excel_state: ExcelPipelineState,
        tmp_path: Path,
    ) -> None:
        """PDF metadata shows correct rule count (excluding SKIP)."""
        out = tmp_path / "change_request.pdf"
        export_pdf(sample_excel_state, out)

        entries = flatten_to_entries(sample_excel_state)
        text = _extract_pdf_text(out)
        count_str = f"Total Rules: {len(entries)}"
        assert count_str in text

    def test_contains_source_type(
        self,
        sample_excel_state: ExcelPipelineState,
        tmp_path: Path,
    ) -> None:
        """PDF metadata includes source type label."""
        out = tmp_path / "change_request.pdf"
        export_pdf(sample_excel_state, out)

        text = _extract_pdf_text(out)
        assert "Excel Traffic Analysis" in text


class TestExportPdfDataRows:
    """Verify table data content in the generated PDF."""

    def test_contains_proposal_ids(
        self,
        sample_excel_state: ExcelPipelineState,
        tmp_path: Path,
    ) -> None:
        """PDF includes proposal IDs from non-SKIP decisions."""
        out = tmp_path / "change_request.pdf"
        export_pdf(sample_excel_state, out)

        text = _extract_pdf_text(out)
        # prop-001 (CREATE) and prop-002 (UPDATE) should be present
        assert "prop-001" in text
        assert "prop-002" in text
        # prop-003 (SKIP) should be excluded
        assert "prop-003" not in text

    def test_contains_action_values(
        self,
        sample_excel_state: ExcelPipelineState,
        tmp_path: Path,
    ) -> None:
        """PDF includes action values from decisions."""
        out = tmp_path / "change_request.pdf"
        export_pdf(sample_excel_state, out)

        text = _extract_pdf_text(out)
        assert "CREATE" in text
        assert "UPDATE" in text

    def test_contains_protocol(
        self,
        sample_excel_state: ExcelPipelineState,
        tmp_path: Path,
    ) -> None:
        """PDF includes protocol information."""
        out = tmp_path / "change_request.pdf"
        export_pdf(sample_excel_state, out)

        text = _extract_pdf_text(out)
        assert "TCP" in text


class TestExportPdfEmpty:
    """Verify behavior with empty proposals."""

    def test_empty_proposals_valid_pdf(
        self,
        sample_excel_state_empty: ExcelPipelineState,
        tmp_path: Path,
    ) -> None:
        """Empty proposals produce a valid PDF with magic bytes."""
        out = tmp_path / "empty.pdf"
        result = export_pdf(sample_excel_state_empty, out)

        assert result == out
        assert out.exists()
        raw = out.read_bytes()
        assert raw[:5] == b"%PDF-"

    def test_empty_proposals_contains_no_rules_message(
        self,
        sample_excel_state_empty: ExcelPipelineState,
        tmp_path: Path,
    ) -> None:
        """Empty proposals PDF shows 'No rules proposed' message."""
        out = tmp_path / "empty.pdf"
        export_pdf(sample_excel_state_empty, out)

        text = _extract_pdf_text(out)
        assert "No rules proposed" in text

    def test_empty_proposals_contains_metadata(
        self,
        sample_excel_state_empty: ExcelPipelineState,
        tmp_path: Path,
    ) -> None:
        """Empty proposals PDF still has metadata (run_id, title)."""
        out = tmp_path / "empty.pdf"
        export_pdf(sample_excel_state_empty, out)

        text = _extract_pdf_text(out)
        run_id = sample_excel_state_empty["run_id"]
        assert isinstance(run_id, str)
        assert run_id in text
        assert "Firewall Change Request" in text


class TestExportPdfErrors:
    """Verify error handling for PDF export."""

    def test_write_failure_raises_export_error(
        self,
        sample_excel_state: ExcelPipelineState,
    ) -> None:
        """Writing to a non-existent directory raises ExportError."""
        bad_path = Path("/nonexistent/dir/output.pdf")

        with pytest.raises(ExportError) as exc_info:
            export_pdf(sample_excel_state, bad_path)

        assert exc_info.value.error_code == "PDF_EXPORT_FAILED"
        assert "output_path" in exc_info.value.details

    def test_write_failure_preserves_cause(
        self,
        sample_excel_state: ExcelPipelineState,
    ) -> None:
        """ExportError chains the original exception as __cause__."""
        bad_path = Path("/nonexistent/dir/output.pdf")

        with pytest.raises(ExportError) as exc_info:
            export_pdf(sample_excel_state, bad_path)

        assert exc_info.value.__cause__ is not None

    def test_write_failure_includes_rule_count(
        self,
        sample_excel_state: ExcelPipelineState,
    ) -> None:
        """ExportError details include rule_count for diagnostics."""
        bad_path = Path("/nonexistent/dir/output.pdf")

        with pytest.raises(ExportError) as exc_info:
            export_pdf(sample_excel_state, bad_path)

        assert "rule_count" in exc_info.value.details
