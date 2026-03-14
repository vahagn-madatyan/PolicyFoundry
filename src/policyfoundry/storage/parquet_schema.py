"""Explicit PyArrow schema mapping NormalizedFlowLog fields to Arrow types.

All 12 NormalizedFlowLog fields plus dedup_hash column. IP addresses and
enum fields are stored as strings for DuckDB query compatibility.
"""

import pyarrow as pa

FLOW_LOG_SCHEMA = pa.schema([
    pa.field("timestamp", pa.timestamp("us", tz="UTC")),
    pa.field("src_ip", pa.string()),
    pa.field("dst_ip", pa.string()),
    pa.field("src_port", pa.int32()),
    pa.field("dst_port", pa.int32()),
    pa.field("protocol", pa.string()),
    pa.field("action", pa.string()),
    pa.field("bytes_transferred", pa.int64()),
    pa.field("rule_id", pa.string()),
    pa.field("app_name", pa.string()),
    pa.field("flow_direction", pa.string()),
    pa.field("packets_count", pa.int64()),
    pa.field("dedup_hash", pa.string()),
])
