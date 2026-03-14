# Pitfalls Research

**Domain:** AI-powered firewall policy management (LLM pipeline analyzing VPC Flow Logs, suggesting AWS Security Group changes)
**Researched:** 2026-03-07
**Confidence:** HIGH (critical pitfalls verified against official docs and multiple sources)

## Critical Pitfalls

### Pitfall 1: LLM Hallucination Producing Overly Permissive Rules (0.0.0.0/0)

**What goes wrong:**
The LLM generates a Security Group rule recommendation with source CIDR `0.0.0.0/0` (or the IPv6 equivalent `::/0`), effectively opening a port to the entire internet. Worse, LLMs can hallucinate *split CIDR blocks* like `0.0.0.0/1` + `128.0.0.0/1` that together cover the full IPv4 space but dodge naive string-matching checks against `0.0.0.0/0`. The model presents these with high confidence and plausible business justifications, making them easy to rubber-stamp during human review.

**Why it happens:**
LLMs optimize for plausible, helpful responses -- not security correctness. When traffic patterns show legitimate connections from diverse sources, the model may generalize to a broad CIDR instead of enumerating specific ranges. Training data contains countless tutorials and Stack Overflow answers with `0.0.0.0/0` examples. The model has no understanding of blast radius.

**How to avoid:**
- Implement a **deterministic post-LLM validation layer** (not another LLM call) that rejects rules with:
  - Source/destination CIDR broader than a configurable threshold (e.g., /16 or wider)
  - Any CIDR that when combined with other proposed rules covers the full address space
  - Port ranges wider than necessary (e.g., 0-65535)
  - Protocol "any" (-1) without explicit user override
- Include an `ai_confidence` field on every rule; require human review for any rule below a configurable threshold
- Put maximum-permissiveness checks in the `rule_validator_tool` so the LLM's own Generate stage gets feedback before Decide
- Never allow `0.0.0.0/0` inbound without a CLI `--allow-public` flag that the user must explicitly pass

**Warning signs:**
- LLM generates rules with /0, /1, /2 CIDR blocks
- Generated rules consistently use wider CIDRs than the traffic data justifies
- Justification text says "for convenience" or "to ensure connectivity"
- Rules reference port ranges like 0-65535 or protocol -1

**Phase to address:**
Phase 1 (pipeline foundation). The deterministic validator must ship before any rule suggestion is ever shown to a user. This is the single most important safety mechanism in the entire system.

---

### Pitfall 2: Structured Output Parsing Failures with Ollama Local Models

**What goes wrong:**
Ollama models (especially smaller ones like 7B-13B) fail to produce valid JSON conforming to the Pydantic schema, causing `ValidationError` exceptions that crash the pipeline. Failures include: incomplete JSON (model stops mid-output without closing braces), extra commentary mixed into JSON, missing required fields, wrong data types (string instead of enum), and hallucinated field names. LiteLLM's integration with Ollama's `ollama_chat` endpoint has known issues where it does not return JSON-compatible structured output or follow tool-call formatting required by structured output frameworks.

**Why it happens:**
Ollama enforces JSON grammar at the token level but does not validate the full response against the schema. If the model hits its token limit mid-JSON, you get truncated output. Smaller models (7B) have weaker instruction-following ability for complex schemas. LiteLLM adds an abstraction layer that may not correctly pass `response_format` or `format: json` parameters to all Ollama backend versions. The `with_structured_output()` method in LangChain has model-specific behavior -- what works with OpenAI may silently fail with Ollama via LiteLLM.

**How to avoid:**
- Use `langchain_ollama.ChatOllama` directly for Ollama instead of routing through LiteLLM for local development. Use LiteLLM only for cloud providers (Bedrock, OpenAI)
- Set `temperature: 0` for all security analysis calls to maximize schema adherence
- Implement a **retry-with-repair loop**: on `ValidationError`, feed the error message back to the LLM with the original prompt and ask it to fix the output (LangChain's `RetryOutputParser` pattern)
- Keep Pydantic schemas as flat as possible -- avoid deeply nested models in LLM-facing schemas. Use separate simpler schemas for LLM output, then map to your internal domain models
- Set `max_tokens` high enough that the model never truncates mid-JSON (monitor actual token usage vs. limit)
- Test every schema against your chosen Ollama model before integrating into the pipeline. Models like `qwen2.5:32b` and `llama3.1:70b` are significantly more reliable at structured output than 7B variants
- Pin Ollama model versions in config to prevent a model update from breaking parsing

**Warning signs:**
- `ValidationError` exceptions in pipeline logs
- Retry counts climbing above 2 per LLM call
- JSON responses with trailing natural language after the closing brace
- Different success rates between models for the same prompt

**Phase to address:**
Phase 1 (LLM integration). Must be validated in the first sprint where LLM calls are implemented. Create a test harness that runs every pipeline schema against the target Ollama model 50+ times to measure reliability.

---

### Pitfall 3: AWS Security Group Allow-Only Model vs. Universal Rule Schema DENY Actions

**What goes wrong:**
The LLM generates a `DENY` or `DROP` rule (because the traffic analysis shows malicious activity that should be blocked), the universal rule schema accepts it, but the AWS SG adapter cannot apply it -- Security Groups are allow-only. The pipeline either crashes with an unhandled error, silently drops the rule, or (worst case) translates it into an ALLOW rule by accident due to a translation bug.

**Why it happens:**
The universal rule schema (`UniversalRule.action`) supports ALLOW, DENY, DROP, and REJECT to accommodate multi-vendor scenarios (Palo Alto supports all). Developers build and test the pipeline end-to-end assuming the schema is the truth, forgetting that AWS SGs only support ALLOW. The LLM has no inherent knowledge of adapter capabilities and will recommend blocking malicious IPs -- a reasonable suggestion that happens to be impossible with SGs alone.

**How to avoid:**
- The Generate stage prompt **must** include adapter capabilities as context: "The target firewall only supports ALLOW rules. Do not generate DENY rules. To restrict traffic, recommend removing or tightening existing ALLOW rules."
- The `rule_validator_tool` must check `AdapterCapabilities.supports_deny_rules` and reject DENY/DROP/REJECT actions for AWS SG targets before the rule ever reaches the Decide stage
- Include adapter capability awareness in the pipeline state so every node knows what the target can do
- When the analysis identifies traffic to block, generate a separate "advisory" output suggesting NACLs (which do support deny) rather than trying to express it as an SG rule
- Add a translator-level assertion: `if action != ALLOW: raise UnsupportedRuleAction`

**Warning signs:**
- LLM generates "block IP X.X.X.X" rules for AWS SG targets
- Translation layer has if/else branches for action types it cannot actually translate
- Test suite only tests ALLOW rules against the AWS adapter

**Phase to address:**
Phase 1 (adapter implementation). The adapter capability system and prompt injection of capabilities must be built at the same time as the AWS SG adapter. Test with scenarios where traffic analysis clearly shows malicious activity to verify the pipeline handles it correctly.

---

### Pitfall 4: AWS Security Group 60-Rule Limit Exhaustion

**What goes wrong:**
The LLM generates 15 new rules for a Security Group that already has 50 inbound rules. The first 10 apply successfully. Rule 11 fails with `RulesPerSecurityGroupLimitExceeded`. The system is now in a partial-apply state: some rules applied, others did not, and the SG is in an inconsistent state relative to the pipeline's intent.

**Why it happens:**
AWS SGs default to 60 inbound + 60 outbound rules per group. The limit is not per-rule but per-CIDR-entry (a rule with 3 CIDRs counts as 3 toward the quota). Prefix list references count as the prefix list's max size, not its current size. Developers test with small rule sets and never hit the limit. The LLM has no awareness of remaining capacity.

**How to avoid:**
- Before the Generate stage, query current rule count and calculate remaining capacity. Pass `remaining_capacity: N` into the LLM prompt
- Implement a **pre-flight check** in the adapter: count existing rules + proposed rules and fail fast if the total would exceed the limit, before applying anything
- Use **atomic batching**: either all rules in a batch apply or none do. Since AWS SG API does not support transactions, implement this by: (1) dry-run all rules first, (2) track applied rules, (3) on failure, rollback all previously applied rules in the batch
- Consider rule consolidation: the LLM should merge overlapping CIDRs where possible (e.g., 10.0.1.0/24 + 10.0.2.0/24 on the same port could become 10.0.0.0/22)
- Surface the formula: `rules_per_SG * SGs_per_ENI <= 1000` total per network interface. Increasing rules per SG may require reducing SGs per ENI

**Warning signs:**
- SG rule count approaching 50 (83% of default limit)
- LLM generating many fine-grained rules instead of consolidated ones
- No pre-flight capacity check in the adapter
- Partial apply errors in audit log

**Phase to address:**
Phase 1 (adapter implementation). The pre-flight check must be part of the adapter's `validate_rule` and `dry_run` methods from day one. Rule consolidation is a Phase 2 optimization but the capacity check is not optional.

---

### Pitfall 5: LangGraph Checkpoint State Bloat from Flow Log Data

**What goes wrong:**
The `PipelineState` TypedDict stores `flow_logs: list[NormalizedFlowLog]` directly in state. LangGraph checkpoints save the full state at every node transition. With 100K flow logs at ~200 bytes each, that is ~20MB per checkpoint, times 5 nodes = 100MB per pipeline run. After 100 runs, the SQLite checkpoint database is 10GB. The CLI becomes slow to start, `replay` commands take minutes, and disk space on developer machines runs out.

**Why it happens:**
LangGraph stores a complete snapshot of state at every checkpoint by default. This is by design for time-travel debugging but catastrophic when state contains large datasets. Developers put flow logs in state for convenience during prototyping and never refactor.

**How to avoid:**
- **Never store raw flow logs in LangGraph state.** Store them in Parquet/DuckDB and pass only a reference (file path or query ID) in pipeline state
- Store only aggregated/summarized data in state (top talkers, port distributions, anomaly scores) -- the data the LLM actually needs
- Use state field `flow_log_ref: str` (path to Parquet file) instead of `flow_logs: list[NormalizedFlowLog]`
- Configure checkpoint TTL to auto-expire old checkpoints (LangGraph supports this)
- Consider `exit` durability mode if intermediate checkpoints are not needed for debugging -- this writes only at run completion

**Warning signs:**
- SQLite state database growing faster than 1MB per pipeline run
- `replay` command taking more than 5 seconds to load state
- `PipelineState` TypedDict containing any `list[...]` field with potentially unbounded size

**Phase to address:**
Phase 1 (pipeline state design). This must be decided in the architecture phase before any node is implemented. Changing state shape later requires migrating all existing checkpoints.

---

### Pitfall 6: AsyncSqliteSaver Hanging on Sync/Async Mismatch

**What goes wrong:**
The CLI uses `asyncio.run()` at the entrypoint and `AsyncSqliteSaver` for LangGraph checkpointing. But somewhere in the codebase, a synchronous method like `graph.invoke()` or `graph.get_state()` is called instead of `await graph.ainvoke()`. The program hangs indefinitely with no error message. This is extremely difficult to debug because there is no exception, no timeout, and no indication of what went wrong.

**Why it happens:**
LangGraph provides both sync and async APIs. The sync `SqliteSaver` and async `AsyncSqliteSaver` are separate classes that must match the invocation style. Developers switch between sync and async during development, or copy-paste examples that use `graph.invoke()` instead of `await graph.ainvoke()`. The `aiosqlite` library has also had breaking changes (v0.22.0 removed Thread inheritance) that cause `AttributeError` on `is_alive`.

**How to avoid:**
- Use synchronous `SqliteSaver` for the CLI tier. The CLI runs a single pipeline at a time; async checkpointing provides no benefit and adds this hanging risk. Use `asyncio.run()` only at the entrypoint, and let LangGraph's sync API handle the graph execution
- If async is required: create a strict rule that ALL graph interactions use async methods. Add a linting rule or wrapper that prevents calling `.invoke()`, `.get_state()`, `.get_state_history()` on async-checkpointed graphs
- Pin `aiosqlite` version in pyproject.toml to avoid breaking changes
- Add a 60-second timeout wrapper around all graph invocations so hangs become errors instead of infinite waits

**Warning signs:**
- CLI hangs after "Starting pipeline..." with no output
- Mix of `graph.invoke()` and `await graph.ainvoke()` calls in codebase
- `aiosqlite` version unpinned or recently updated
- No timeout on graph execution

**Phase to address:**
Phase 1 (pipeline orchestration). Decide sync vs. async for the checkpointer in the first implementation sprint. Recommendation: use sync `SqliteSaver` for CLI.

---

### Pitfall 7: VPC Flow Logs Data Gaps Leading to Wrong Security Conclusions

**What goes wrong:**
The LLM analyzes traffic patterns from VPC Flow Logs and concludes "no traffic on port 443 from subnet X" -- so it recommends removing the ALLOW rule for that traffic. In reality, the flow logs have gaps: SKIPDATA records indicate dropped log entries, the aggregation interval was 10 minutes so short-lived connections may not appear, and version 2 logs do not include flow direction or AWS service fields, making it impossible to distinguish load balancer traffic from direct traffic.

**Why it happens:**
VPC Flow Logs are **not** a complete packet capture. AWS explicitly documents that records may be skipped due to internal capacity constraints (log-status: SKIPDATA). Default aggregation is 10 minutes. Version 2 logs show only interface-local IPs, so traffic forwarded by a load balancer shows the LB's IP, not the original source. Developers treat flow logs as ground truth when they are best-effort samples.

**How to avoid:**
- Parse and surface the `log-status` field. Count SKIPDATA records per time window and include this in the LLM's analysis context: "Warning: 3% of records were skipped in this window. Conclusions about absent traffic are unreliable."
- Set the aggregation interval to 1 minute (Nitro instances do this automatically) in the test infrastructure Terraform
- Use version 5+ flow logs to get `flow-direction`, `pkt-srcaddr`, `pkt-dstaddr`, and `pkt-src-aws-service` fields. The parser must handle version differences gracefully
- Never recommend REMOVING an existing rule based solely on the absence of matching traffic. Require a configurable minimum observation window (e.g., 30 days) before considering traffic "absent"
- Include a `data_completeness_score` in the `TrafficAnalysis` output that the Assess and Generate stages use to temper their confidence

**Warning signs:**
- SKIPDATA records in flow logs being silently discarded during parsing
- Parser only handling version 2 fields
- LLM recommending rule removal after analyzing less than 7 days of data
- No data completeness metric in traffic analysis output

**Phase to address:**
Phase 1 (ingestion layer). The parser must handle SKIPDATA and version detection from the first implementation. The minimum observation window should be a configurable safety parameter.

---

### Pitfall 8: boto3 Is Not Async -- Blocking the Event Loop

**What goes wrong:**
The project constraint says "All I/O operations must be async/await." The adapter interface declares `async def get_rules()`, `async def apply_rule()`, etc. But boto3 is synchronous -- it does blocking HTTP calls. Wrapping a sync boto3 call in an `async def` does NOT make it non-blocking; it blocks the entire asyncio event loop, freezing the CLI during AWS API calls and preventing concurrent operations.

**Why it happens:**
boto3 does not support asyncio and has no plans to until a major rewrite. Developers see `async def` in the adapter interface, use `await self.client.describe_security_groups()`, and it "works" because Python allows calling sync code from async functions -- but the event loop is blocked. This is invisible in a CLI that makes one API call at a time but becomes a correctness issue if any concurrent operations are added.

**How to avoid:**
- Wrap boto3 calls in `asyncio.loop.run_in_executor(None, sync_function)` to run them in a thread pool. This is the recommended pattern for using synchronous libraries in async code
- Alternatively, use `aioboto3` (drop-in async replacement for boto3) which provides true async AWS API calls
- Document clearly that the boto3 client methods are sync wrappers and must always go through the executor
- Do NOT declare boto3 wrapper methods as `async def` without the executor pattern -- this is misleading

**Warning signs:**
- `async def` methods that directly call boto3 without `run_in_executor`
- CLI freezing during AWS API calls (no Rich spinner/progress updates)
- Import of `boto3` without `aioboto3` or `run_in_executor` pattern nearby

**Phase to address:**
Phase 1 (adapter implementation). Decide between `aioboto3` and `run_in_executor` pattern before writing the first adapter method.

---

### Pitfall 9: AWS Security Group Eventual Consistency Race Conditions

**What goes wrong:**
The pipeline reads current rules (`describe_security_group_rules`), generates recommendations, and applies a new rule. Then it reads rules again to verify -- but the new rule is not yet visible due to eventual consistency. The pipeline concludes the apply failed and either retries (creating a duplicate) or reports an error. Alternatively: the pipeline creates an SG and immediately tries to add rules, but the SG does not exist yet in the API's view.

**Why it happens:**
The EC2 API is eventually consistent. `authorize_security_group_ingress` returns success before the change is propagated to all API endpoints. Subsequent `describe` calls may not reflect the change for several seconds. This is documented AWS behavior, not a bug.

**How to avoid:**
- After any mutating API call, implement a **poll-with-backoff** verification: retry `describe` with exponential backoff (1s, 2s, 4s) until the expected rule appears, up to a configurable timeout
- Separate the "apply" and "verify" steps in the audit log. Log "APPLIED (pending verification)" then "VERIFIED" as separate events
- For the suggest-only Phase 1, this is low risk since no rules are actually applied. But the verification pattern must be built into the adapter from the start for Phase 2+
- Consider using `DryRun=True` before actual apply to catch permission errors without triggering consistency issues

**Warning signs:**
- Intermittent "rule not found" errors after successful apply calls
- Duplicate rules appearing in Security Groups
- Tests passing locally but failing in CI (timing-dependent)

**Phase to address:**
Phase 2 (auto-apply). In Phase 1 suggest-only mode, the read path (fetching current rules) is the primary concern and has lower consistency risk. The full verification pattern is needed when apply is implemented.

---

### Pitfall 10: Audit Trail Gaps -- Events Without Full LLM Lineage

**What goes wrong:**
The audit log records that a rule was proposed and the final rule spec, but does not capture: which LLM model version produced it, what prompt was sent, what traffic data the LLM saw, what the LLM's raw response was before Pydantic parsing, or which previous pipeline stages influenced the decision. When an auditor asks "why did the AI recommend opening port 8080?" the team cannot reconstruct the reasoning chain.

**Why it happens:**
The `AuditEvent` schema has `llm_model_used` and `ai_reasoning` fields, which seems sufficient. But `ai_reasoning` is a summary generated by the LLM itself (which can hallucinate its own reasoning). The actual prompt, the DuckDB query results that fed the analysis, and the intermediate stage outputs are only in LangGraph checkpoints -- which may have been garbage-collected, or may not include the full LLM request/response.

**How to avoid:**
- Store the full prompt and raw LLM response for every LLM call that contributes to a rule decision. Use LangSmith traces for development, but for production audit compliance, store these locally in the SQLite audit database (not dependent on a third-party SaaS)
- Include a `pipeline_run_id` + `stage_name` + `checkpoint_id` reference in every audit event so the full state can be reconstructed from checkpoints
- Add `input_data_hash` to audit events -- a hash of the traffic data that was analyzed -- so you can verify the analysis was based on a specific dataset
- Set checkpoint TTL to at least match audit retention (1 year for PCI-DSS compliance)
- Write audit events synchronously and treat write failures as pipeline failures -- never silently drop audit records

**Warning signs:**
- Audit events with `ai_reasoning: ""` or generic boilerplate
- No way to map an audit event back to the specific LLM call that produced it
- Checkpoint TTL shorter than audit retention requirement
- LangSmith as the only trace storage (external dependency for compliance data)

**Phase to address:**
Phase 1 (audit system). The audit event schema and write path must be implemented alongside the first pipeline node. Retrofitting audit lineage after the pipeline is built always results in gaps.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Storing flow logs directly in LangGraph state | Simpler state management, no external storage needed | Checkpoint bloat, 10x storage costs, slow replays | Never -- use Parquet file references from day one |
| Using string-based LLM output parsing instead of `with_structured_output` | Works with any model, no tool-calling support needed | Fragile regex parsing, breaks on model updates, no type safety | Never for this project -- Pydantic structured output is a core requirement |
| Hardcoding prompt templates instead of loading from files | Faster iteration in early development | Cannot A/B test prompts, version history lost, cannot swap per-model | Only for first prototype sprint; externalize by week 3 |
| Single SQLite file for checkpoints + audit + state | One fewer dependency, simpler config | Audit data mixed with expendable checkpoint data; cannot set different retention policies | Only in MVP if clear migration path exists to separate DBs |
| Skipping the DryRun step for AWS SG rule application | Faster apply, fewer API calls | No pre-validation of IAM permissions, rule limits hit at apply time | Never -- DryRun is free and catches errors early |
| Using synchronous SqliteSaver instead of async | Simpler code, no hanging bugs, easier debugging | Cannot run concurrent pipelines (irrelevant for CLI v1) | Acceptable for CLI tier; switch to PostgresSaver for cloud tier |

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Ollama via LiteLLM | Assuming `with_structured_output()` works identically to OpenAI -- it does not; LiteLLM may not pass JSON format correctly to Ollama | Use `langchain_ollama.ChatOllama` directly for local Ollama. Use LiteLLM only for cloud providers |
| AWS SG via boto3 | Declaring adapter methods `async def` but calling sync boto3 directly, blocking the event loop | Use `run_in_executor()` or `aioboto3` for all boto3 calls within async contexts |
| AWS SG rule application | Not handling `InvalidPermission.Duplicate` error when the same rule already exists | Check for existing rules before apply; handle duplicate gracefully as a no-op with warning |
| DuckDB + Parquet | Loading entire Parquet file into memory for a filtered query | Use DuckDB's Parquet reader with `WHERE` clauses to leverage columnar predicate pushdown |
| LangGraph SQLiteSaver | Not setting `check_same_thread=False` or mixing sync/async invocation styles | SqliteSaver handles this internally with a lock; stick to one invocation style (sync or async) consistently |
| VPC Flow Logs from S3 | Assuming all log files use the same field format and ordering | Parse the header/version field first; handle version 2-5+ differences; do not assume field positions |
| LangSmith tracing | Enabling tracing in production without considering that prompts and responses contain customer network data | Make LangSmith optional; provide local-only audit logging; warn users about data sent to LangSmith |

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Loading all flow logs into Python memory before writing to Parquet | Works fine with 10K records; OOM at 1M+ | Use streaming ingestion: async generator yields batches, writer flushes to Parquet incrementally | >500K records per ingestion (~100MB raw) |
| DuckDB `SELECT *` on Parquet without column pruning | Queries complete slowly, high memory usage | Select only needed columns; DuckDB reads only referenced columns from Parquet | >1GB Parquet file, or queries on high-cardinality columns |
| Sending raw DuckDB query results (full table) to the LLM | Token limit exceeded, high latency, high cost | Pre-aggregate in DuckDB (top-N, group-by summaries); send statistics, not rows | >100 result rows from any traffic query |
| Single-threaded boto3 calls when fetching rules from multiple SGs | Each API call takes 200-500ms; 10 SGs = 5 seconds of blocking | Batch with ThreadPoolExecutor or use aioboto3 for concurrent fetches | >5 Security Groups in a single analysis |
| SQLite checkpoint database without WAL mode | Write contention if audit writer and checkpoint writer overlap | Enable WAL mode on SQLite: `PRAGMA journal_mode=WAL` | Concurrent pipeline runs or audit writes during pipeline execution |

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| LLM recommending rules based on hallucinated traffic patterns not present in the data | False sense of security; rules that don't address actual traffic | Cross-validate every LLM traffic claim against DuckDB queries; add a verification node that spot-checks LLM assertions |
| Storing AWS credentials in config YAML instead of env vars | Credentials committed to git, leaked in logs | Use env var references only (`api_key_env: PALO_API_KEY`); add pre-commit hook to scan for credential patterns |
| Not restricting which IAM actions the CLI's role can perform | If the CLI is compromised, attacker gets full SG modification access | Create a minimal IAM policy: `ec2:DescribeSecurityGroup*`, `ec2:AuthorizeSecurityGroup*`, `ec2:RevokeSecurityGroup*` only on specific SGs |
| Audit log stored in user-writable SQLite without integrity checks | Malicious user (or bug) modifies audit history to cover tracks | Append-only table design with hash-chain integrity (each event includes hash of previous event); consider write-ahead checksum |
| LLM prompt injection via crafted flow log data | Attacker crafts traffic that creates flow log entries containing prompt injection strings | Sanitize all data fed to LLM prompts; treat flow log data as untrusted input; use separate system/user prompt boundaries |
| Suggesting temporary "break-glass" rules without expiration enforcement | Emergency rules with 0.0.0.0/0 stay forever after the incident | All rules with `expires_at` must have a background job or CLI reminder to verify expiration; surface stale temporary rules prominently |

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Showing all rule recommendations in a flat list without risk grouping | User overwhelmed by 30 suggestions; misses the 2 critical ones | Group by risk level (CRITICAL first), show summary counts, let user drill into categories |
| Requiring AWS credentials to run any CLI command including `--help` | User cannot explore the tool without AWS setup; terrible onboarding | Lazy-load AWS connections only when commands actually need them; include a `demo` mode with sample data |
| No progress feedback during LLM inference (Ollama can take 30-60s per call) | User thinks CLI is frozen; kills the process | Rich progress spinner showing: current stage, elapsed time, model name, token count streaming |
| Showing raw Pydantic model dumps as output | User sees `{'risk_level': 'high', 'ai_confidence': 0.72}` -- meaningless to security engineers | Use Rich tables, color-coded risk levels, plain-English justifications, and show the proposed AWS CLI equivalent command |
| Error messages exposing internal stack traces | User sees `pydantic.ValidationError` traceback instead of actionable guidance | Catch known error types; show "LLM returned invalid output for stage Analyze. Retrying (2/3)..." instead of traceback |
| No `--dry-run` mode for the overall CLI | User cannot preview what the tool will do before it accesses AWS | Add `--dry-run` that runs the pipeline with sample/cached data and shows what would happen without any AWS API calls |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Flow log parser:** Often missing handling for SKIPDATA/NODATA log-status values -- verify parser surfaces data completeness metrics
- [ ] **AWS SG adapter:** Often missing handling for `InvalidPermission.Duplicate` errors -- verify idempotent apply behavior
- [ ] **AWS SG adapter:** Often missing prefix list rule counting -- verify rules referencing prefix lists count as max_size toward quota, not as 1
- [ ] **LLM structured output:** Often missing retry-on-parse-failure logic -- verify pipeline retries with error feedback, not just re-sends the same prompt
- [ ] **Audit trail:** Often missing the full prompt text and raw LLM response -- verify every audit event can reconstruct the complete decision chain
- [ ] **Checkpoint storage:** Often missing TTL configuration -- verify old checkpoints are cleaned up automatically
- [ ] **Human-in-the-loop gate:** Often missing resume-after-restart capability -- verify that if the CLI exits while waiting for approval, the pipeline can resume from the checkpoint
- [ ] **Pipeline state:** Often missing error accumulation -- verify that a failure in stage 2 does not lose stage 1 results; errors append, do not overwrite
- [ ] **Config system:** Often missing validation of Ollama model availability -- verify the CLI checks that the configured Ollama model is actually pulled/available before starting a pipeline run
- [ ] **Rule translation:** Often missing IPv6 support -- verify AWS SG adapter handles `Ipv6Ranges` in addition to `IpRanges`

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Overly permissive rule applied to SG | MEDIUM | 1. Immediately revoke the rule using rollback handle from audit log 2. Review audit trail to identify which pipeline run caused it 3. Add the specific CIDR pattern to the validator blocklist 4. Re-run pipeline with corrected validation |
| Checkpoint database corrupted | LOW | 1. Delete the SQLite checkpoint file 2. Re-run the pipeline from scratch (all data is in Parquet/DuckDB) 3. Audit events are in a separate table/file and unaffected |
| LLM model update breaks structured output | MEDIUM | 1. Pin model version in config and revert to last known working version 2. Run the schema test harness against the new model version 3. Adjust prompts or simplify schemas if needed 4. Only upgrade model after test harness passes |
| 60-rule limit hit during batch apply | HIGH | 1. Rollback all partially-applied rules from the current batch 2. Consolidate existing rules (merge overlapping CIDRs) to free capacity 3. Request AWS quota increase if consolidation is insufficient 4. Re-run pipeline with capacity-aware generation |
| AsyncSqliteSaver hanging | LOW | 1. Kill the process (it will not recover on its own) 2. Switch to sync SqliteSaver 3. Pipeline resumes from last checkpoint automatically |
| Audit log gaps discovered during compliance review | HIGH | 1. Cross-reference LangSmith traces (if enabled) with audit events to identify gaps 2. Reconstruct missing events from checkpoint history 3. Implement the hash-chain integrity check to detect future gaps 4. Document the gap in the compliance report |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| LLM hallucinating overly permissive rules | Phase 1 -- deterministic validator | Unit tests with intentionally overly-permissive LLM outputs; validator must reject 100% of 0.0.0.0/0 rules |
| Structured output parsing failures | Phase 1 -- LLM integration | Schema reliability test harness: 50 runs per schema, >95% parse success rate required |
| Allow-only SG model vs DENY rules | Phase 1 -- adapter capability system | Integration test: generate rules for malicious traffic against AWS SG target; verify no DENY rules reach apply |
| 60-rule limit exhaustion | Phase 1 -- adapter pre-flight checks | Test: attempt to add rules to a nearly-full SG; verify graceful failure with clear error |
| Checkpoint state bloat | Phase 1 -- pipeline state design | Measure: checkpoint size must be <1MB per node transition; reject state designs that store raw logs |
| Async/sync mismatch hanging | Phase 1 -- pipeline orchestration | Verify: no `graph.invoke()` calls exist in codebase when using async checkpointer; or use sync checkpointer |
| VPC Flow Log data gaps | Phase 1 -- ingestion layer | Verify: parser surfaces SKIPDATA count; data_completeness_score appears in TrafficAnalysis output |
| boto3 blocking event loop | Phase 1 -- adapter implementation | Verify: all boto3 calls wrapped in executor; or aioboto3 used; Rich spinner runs during API calls |
| Eventual consistency race conditions | Phase 2 -- auto-apply | Integration test: apply rule then immediately verify; confirm poll-with-backoff handles delay |
| Audit trail gaps | Phase 1 -- audit system | Verify: every LLM call in a pipeline run has a corresponding audit record with prompt hash and response hash |

## Sources

- [AWS VPC Flow Log Records](https://docs.aws.amazon.com/vpc/latest/userguide/flow-log-records.html) -- official documentation on versions, fields, SKIPDATA, aggregation intervals
- [AWS Security Group Rules](https://docs.aws.amazon.com/vpc/latest/userguide/security-group-rules.html) -- official documentation on rule limits and counting
- [AWS Security Group Quota Optimization](https://repost.aws/articles/AR_rIppDrsRvKFHzb8LTjs3Q/optimizing-security-groups-in-aws-managing-growth-and-quota-constraints) -- rule counting formula, ENI limits, prefix list counting
- [LangGraph Interrupts Documentation](https://docs.langchain.com/oss/python/langgraph/interrupts) -- official docs on interrupt_before, deterministic ordering, resume mechanics
- [LangGraph Persistence Guide](https://fast.io/resources/langgraph-persistence/) -- checkpoint bloat, TTL, durability modes
- [LangGraph State Management Best Practices](https://sparkco.ai/blog/mastering-langgraph-state-management-in-2025/) -- reducer patterns, state schema design
- [AsyncSqliteSaver Hanging Issue](https://github.com/langchain-ai/langgraph/issues/1800) -- sync/async mismatch causing infinite hang
- [LiteLLM Structured Output Bug with Ollama](https://github.com/BerriAI/litellm/issues/10616) -- ollama_chat endpoint not returning structured output
- [LangChain Structured Output with Ollama TypeError](https://github.com/langchain-ai/langchain/issues/34107) -- version-specific parsing failures
- [Ollama Structured Outputs Documentation](https://docs.ollama.com/capabilities/structured-outputs) -- grammar enforcement, truncation risk, validation limitations
- [Ollama Structured Output Issues](https://www.glukhov.org/post/2025/10/ollama-gpt-oss-structured-output-issues/) -- model-specific failures, reasoning trace interference
- [boto3 Async Discussion](https://github.com/boto/boto3/discussions/3531) -- confirmed no native async support planned
- [EC2 API Eventual Consistency](https://www.cloudavail.com/blog/2014/07/18/eventual-consistency-ec2-api/) -- documented consistency behavior
- [boto3-post-conditions for Eventual Consistency](https://github.com/jeking3/boto3-post-conditions) -- workaround patterns
- [DuckDB Memory Management](https://duckdb.org/2024/07/09/memory-management) -- streaming execution, when memory spikes occur
- [DuckDB High Memory with Parquet](https://github.com/duckdb/duckdb/issues/17262) -- 4GB RAM for 120MB Parquet file
- [Hidden Risks of AI-Driven Firewall Policy Management](https://www.titania.com/about-us/news/hidden-risks-of-ai-driven-firewall-policy-management) -- lack of contextual awareness, operationally flawed rules
- [LLM Security Risks 2026](https://sombrainc.com/blog/llm-security-risks-2026) -- hallucination in production systems
- [OWASP LLM Top 10 2025](https://deepstrike.io/blog/owasp-llm-top-10-vulnerabilities-2025) -- LLM-specific vulnerability patterns
- [Event Sourcing Pitfalls](https://dzone.com/articles/event-sourcing-guide-when-to-use-avoid-pitfalls) -- schema versioning, GDPR, replay complexity
- [Event Sourcing with SQLite](https://www.sqliteforum.com/p/building-event-sourcing-systems-with) -- append-only design patterns

---
*Pitfalls research for: AI-powered firewall policy management (PolicyFoundry)*
*Researched: 2026-03-07*
