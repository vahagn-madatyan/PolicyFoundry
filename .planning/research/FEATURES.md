# Feature Research

**Domain:** AI-powered firewall policy management / network security policy management (NSPM)
**Researched:** 2026-03-07
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete. Derived from what Tufin, AlgoSec, FireMon, AWS Firewall Manager, Google Cloud Firewall Insights, Prowler, and open-source AWS security tools all provide as baseline.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Flow log ingestion and normalization** | Every NSPM and traffic analysis tool ingests logs. Without this, the tool has no data to work with. Users expect pointing at S3/local files and getting parsed, queryable data. | MEDIUM | VPC Flow Logs have well-documented v2-v7 formats. Parse space-delimited text, normalize to unified schema. S3 + local file support for Phase 1. |
| **Current rule fetching and display** | AlgoSec, FireMon, Tufin all show your existing rule base. Users must see what they have before they trust suggestions to change it. | LOW | boto3 `describe_security_group_rules` is straightforward. Translate to universal schema for display. |
| **Overly permissive rule detection** | Google Cloud Firewall Insights, AWS Firewall Manager, Prowler, and every NSPM tool flags `0.0.0.0/0` and wide port ranges. This is the most basic security hygiene check. | LOW | Compare rule CIDRs and port ranges against observed traffic. Flag rules wider than actual usage. No LLM needed for basic cases. |
| **Unused rule detection** | Every enterprise NSPM tool (Tufin, FireMon, AlgoSec) and Google Cloud Firewall Insights detect rules with zero traffic hits. This is the #1 rule cleanup action. | MEDIUM | Cross-reference flow log traffic against existing rules. Rules with no matching flows in observation window are candidates. Needs flow-to-rule association logic. |
| **Rule change suggestions with justification** | This is PolicyFoundry's core value prop. Every competitor provides recommendations. What matters is the quality of justification -- PCI-DSS 4.0 requires business justification for every rule. | HIGH | 4-stage LangGraph pipeline output. Each suggestion must include: what to change, why, risk level, confidence score, and business justification text. |
| **Human-readable output (terminal)** | CLI tools live and die by output quality. Security engineers need scannable, understandable results, not raw JSON dumps. Rich tables, color-coded risk levels, clear summaries. | LOW | Typer + Rich provides panels, tables, color coding, progress bars. Essential for CLI-first product. |
| **Machine-readable output (JSON)** | CI/CD integration is expected. Security engineers need to pipe output to other tools, SIEM, or ticket systems. JSON is the universal interchange format. | LOW | Serialize Pydantic models to JSON. Straightforward. |
| **Audit trail of suggestions** | PCI-DSS 4.0 Requirement 10 mandates audit trails for all security-relevant actions. SOC 2 requires tamper-proof logs. Even suggest-only mode must log what was proposed and why. | MEDIUM | Event-sourced immutable log in SQLite. Every proposal gets an AuditEvent with full lineage (run ID, model used, confidence, reasoning). |
| **Configuration file support** | Every CLI tool supports config files. Users need to configure LLM provider, AWS credentials reference, log sources, and target security groups without passing 20 CLI flags. | LOW | YAML config at `~/.policyfoundry/config.yaml`. Pydantic Settings handles env var overrides. Well-understood pattern. |
| **Dry-run / suggest-only mode** | Users MUST be able to run the tool without any risk of changes. AWS SG `DryRun` flag exists for a reason. Suggest-only is not optional for Phase 1 -- it IS the mode. | LOW | Default and only mode in Phase 1. No `apply` functionality ships initially. Output is advisory. |
| **Multiple output formats** | Security tooling outputs to various consumers: terminals, CI/CD, SIEM, ticketing. SARIF is the standard for CI/CD security findings. | MEDIUM | JSON (done with Pydantic), SARIF (static analysis standard, used by GitHub Code Scanning), Rich terminal. SARIF adds moderate complexity but is worth it for CI/CD adoption. |

### Differentiators (Competitive Advantage)

Features that set PolicyFoundry apart. These are what make it more than "yet another security group auditor."

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Traffic-to-rule AI pipeline** | The core differentiator. No existing open-source tool uses an agentic AI pipeline to go from raw VPC Flow Logs to specific, justified Security Group rule recommendations. Tufin/AlgoSec/FireMon do this with proprietary engines, but cost $50K+/year. Prowler/ScoutSuite audit configurations but don't analyze traffic patterns. PolicyFoundry bridges the gap. | HIGH | 4-stage LangGraph pipeline: Analyze traffic patterns, Assess security posture against current rules, Generate policy proposals, Decide actions. Each stage is a checkpointed node with structured Pydantic output. |
| **LLM-powered traffic pattern interpretation** | DuckDB aggregates the stats; the LLM interprets what the patterns MEAN. "Port 4443 traffic from 3 internal IPs to an external IP at 3am looks like data exfiltration" -- this contextual reasoning is impossible with rule-based tools. | HIGH | Stage 1 (Analyze) feeds pre-aggregated DuckDB statistics to the LLM. The LLM identifies clusters, anomalies, and suspicious patterns. Keeps token costs manageable by never sending raw logs. |
| **Local-first LLM (Ollama)** | Zero cloud costs, zero data leaving the network. Competitors like AlgoSec and Tufin are cloud-hosted SaaS. Security teams handling sensitive network data strongly prefer keeping it local. Ollama + LiteLLM routing means users control where their data goes. | MEDIUM | LiteLLM routes to Ollama by default. No API keys needed to get started. Trade-off: local models (Llama 3, Mistral) are less capable than Claude/GPT-4 for complex reasoning. Good enough for pattern detection; may struggle with nuanced policy generation. |
| **Pipeline checkpointing and resumability** | LangGraph SQLiteSaver checkpoints every pipeline stage. If the LLM call fails at Stage 3, resume from Stage 3 without re-running Stages 1-2. No competitor CLI offers this. Enterprise tools do, but at enterprise prices. | MEDIUM | LangGraph has native checkpointing. SQLiteSaver for CLI tier. Enables `policyfoundry replay --run-id X --from-stage assess`. Saves time and LLM costs on failures. |
| **Vendor-neutral universal rule schema** | PolicyFoundry defines rules in a universal format, then translates to vendor-specific API calls. This means the same analysis pipeline works for AWS SGs today and Palo Alto/Azure NSGs/GCP Firewall tomorrow. Tufin and AlgoSec are multi-vendor but proprietary. | MEDIUM | UniversalRule Pydantic model captures the superset of vendor capabilities. Adapter pattern translates bidirectionally. Phase 1 is AWS-only, but the schema is designed for multi-vendor from day one. |
| **Risk-scored recommendations with confidence levels** | Each suggestion includes a risk level (LOW/MEDIUM/HIGH/CRITICAL) and an AI confidence score (0.0-1.0). Security teams can filter by risk, prioritize high-confidence suggestions, and ignore low-confidence ones. No open-source tool provides calibrated confidence. | MEDIUM | Stage 4 (Decide) assigns risk levels and confidence. The LLM evaluates each proposal against organizational risk tolerance. Confidence calibration will improve with eval datasets over time. |
| **SARIF output for CI/CD integration** | SARIF (Static Analysis Results Interchange Format) is the standard for security findings in GitHub Code Scanning, Azure DevOps, and other CI/CD platforms. PolicyFoundry can run in CI/CD to flag security group drift on every pull request. No other traffic-analysis tool outputs SARIF. | MEDIUM | SARIF spec is well-documented. Map PolicyProposal to SARIF Result with rule ID, message, and severity. Enables "security-as-code" workflows where SG analysis runs alongside linting and tests. |
| **Event-sourced audit with full AI lineage** | Every suggestion records which LLM model produced it, what tokens it used, what it cost, and the full reasoning chain. This is beyond what PCI-DSS requires -- it enables trust-building with auditors who want to understand AI decision-making. | MEDIUM | AuditEvent model captures: model used, token count, cost, AI reasoning text, pipeline run ID, before/after rule state. Immutable append-only log in SQLite. |
| **Cost tracking per pipeline run** | Every LLM call records tokens in/out and estimated cost. Users see exactly what each analysis costs. Critical for local LLM users (compute time) and cloud LLM users (API costs). Budget limits prevent runaway spending. | LOW | LLMCallRecord model tracks per-call costs. Aggregate per run. LiteLLM provides cost estimation for most providers. Simple but valuable for adoption -- users hate surprise bills. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems. Deliberately NOT building these.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Auto-apply mode in Phase 1** | "Why suggest when you can just fix it?" Security automation feels like the end goal. | Auto-applying firewall rules without established trust is reckless. One bad AI suggestion could block production traffic or open attack surfaces. Trust must be earned through suggestion accuracy. Enterprise tools (Tufin, AlgoSec) took years to reach auto-apply. PCI-DSS requires human review of changes. | Suggest-only with clear, justified recommendations. Track suggestion acceptance rate. Graduate to auto-apply only after 100+ accurate suggestions with <5% false positive rate (Phase 2+). |
| **Real-time streaming analysis** | "I want alerts the moment something bad happens." Real-time sounds better than batch. | Streaming ingestion (Kafka, ClickHouse materialized views) adds enormous complexity to a CLI tool. VPC Flow Logs have inherent 10-minute aggregation delay anyway. The ROI of sub-minute analysis is near zero for policy management (policies change weekly, not per-second). Real-time is for SIEM/NDR tools, not policy tools. | Batch analysis on-demand or via cron. Micro-batch (30-60 second poll) in Phase 2 for near-real-time monitoring. Real-time threat detection is a different product category. |
| **Web GUI / dashboard** | "CLI is for developers, security teams want dashboards." Visual representation of network topology and rule coverage. | Building a web frontend (React/Next.js) doubles the codebase and halves iteration speed. The CLI is the product for Phase 1. Enterprise NSPM tools all have GUIs, but they also have 100+ person engineering teams. A solo/small team building CLI + web simultaneously ships neither well. | Rich terminal output via Typer + Rich. Optional Textual TUI for interactive exploration. JSON/SARIF output enables third-party visualization. Web dashboard is Phase 2 after CLI is proven. |
| **Multi-cloud support in Phase 1** | "We use AWS and Azure and GCP." Multi-cloud is the reality for enterprises. | Each cloud has different firewall primitives (AWS SGs vs Azure NSGs vs GCP Firewall Rules), different APIs, different log formats, and different quirks. Supporting three clouds triples the adapter work and triples the testing surface. Prove the pipeline works perfectly on one cloud first. | AWS-only for Phase 1. Universal rule schema is designed for multi-vendor from day one. Azure NSG and GCP Firewall adapters are Phase 2 once the pipeline is proven. |
| **Threat intelligence integration in Phase 1** | "Check IPs against threat feeds." AbuseIPDB, GreyNoise, VirusTotal lookups add context. | External API dependencies add latency, rate limits, API key management, and cost. Threat intel is valuable for the Assess stage but not essential for MVP. The core value is traffic-to-rule analysis, not IP reputation. Adding threat intel before the pipeline works end-to-end is premature optimization. | Placeholder tool interface in Stage 2. Implement with free tier APIs (AbuseIPDB, GreyNoise Community) in Phase 1.x after core pipeline is working. Design the tool interface now so it can be plugged in later. |
| **Natural language query interface** | "Ask questions about your network in English." Conversational AI interface for ad-hoc queries. | LLM-powered NLQ adds a separate interaction model alongside the structured pipeline. It requires prompt engineering, context management, and handling ambiguous queries -- all orthogonal to the core analysis pipeline. It is a different product experience that dilutes focus. | Structured CLI commands with clear options. DuckDB SQL queries for power users who want ad-hoc analysis. NLQ can be a Phase 2 feature after the structured pipeline is mature. |
| **Compliance report generation (PCI-DSS, SOC 2 formal reports)** | "Generate my PCI-DSS audit report." Compliance is a pain point and automation is appealing. | Formal compliance reports require deep domain expertise in each standard, legal review, and continuous updates as standards evolve. PCI-DSS 4.0 alone has hundreds of requirements. This is a separate product (see Vanta, Drata, Secureframe). PolicyFoundry should provide DATA for compliance, not generate the reports themselves. | Audit trail data exportable in standard formats (JSON, CSV). Compliance-relevant metadata on every suggestion (business justification, risk level, change history). Integrate with compliance platforms rather than replacing them. |
| **Custom rule language / DSL** | "Let me write custom detection rules." Users want to define their own analysis patterns. | A custom DSL is a language design problem, not a security problem. It requires parser, documentation, error handling, IDE support, and ongoing maintenance. The LLM pipeline should handle pattern detection. For custom rules, users can modify prompts or add tool functions. | Configurable analysis parameters in YAML (risk thresholds, port allowlists, CIDR exemptions). User-provided security policy YAML that the LLM references during analysis. Custom LangGraph tool functions for power users. |

## Feature Dependencies

```
[Flow Log Ingestion + Normalization]
    |
    +--requires--> [DuckDB Storage + Parquet Writer]
    |                  |
    |                  +--enables--> [Traffic Query Tool]
    |                                    |
    |                                    +--feeds--> [Stage 1: Analyze Traffic]
    |                                                    |
    +--requires--> [Current Rule Fetching (boto3)]       |
                       |                                 |
                       +--feeds--> [Stage 2: Assess Security]
                                       |
                                       +--feeds--> [Stage 3: Generate Policy]
                                                       |
                                                       +--feeds--> [Stage 4: Decide]
                                                                       |
                                                                       +--produces--> [Rule Suggestions with Justification]
                                                                       |                  |
                                                                       |                  +--consumed-by--> [Output Formatters (Rich/JSON/SARIF)]
                                                                       |                  |
                                                                       |                  +--consumed-by--> [Audit Trail]
                                                                       |
                                                                       +--gated-by--> [Human-in-the-Loop Review]

[LLM Client (LiteLLM + Ollama)]
    +--used-by--> [Stage 1: Analyze]
    +--used-by--> [Stage 2: Assess]
    +--used-by--> [Stage 3: Generate]
    +--used-by--> [Stage 4: Decide]

[Configuration System (YAML + Pydantic Settings)]
    +--used-by--> [Everything]

[Pipeline Checkpointing (SQLiteSaver)]
    +--wraps--> [LangGraph StateGraph]
    +--enables--> [Pipeline Resumability]

[Overly Permissive Detection] --requires--> [Current Rule Fetching] + [Flow Log Ingestion]
[Unused Rule Detection] --requires--> [Current Rule Fetching] + [Flow Log Ingestion] + [DuckDB Storage]
```

### Dependency Notes

- **Stage 1 (Analyze) requires DuckDB storage:** The LLM receives pre-aggregated statistics, not raw logs. DuckDB must be populated before analysis can begin.
- **Stage 2 (Assess) requires current rules:** Cannot assess security posture without knowing what rules exist. The firewall adapter must fetch and translate current rules before this stage runs.
- **Output formatters require pipeline completion:** SARIF/JSON/Rich output consumes the final pipeline state. Partial results are possible with checkpointing but full output needs all stages.
- **Audit trail requires pipeline metadata:** AuditEvent records reference pipeline run ID, LLM model, token counts. These come from pipeline execution, not standalone.
- **Unused rule detection requires both rule data AND flow log data:** This is a cross-reference operation. Cannot be done with rules alone or logs alone.
- **Human-in-the-loop gate conflicts with auto-apply:** Phase 1 has only human review. Auto-apply (Phase 2+) replaces the gate for low-risk changes but coexists for high-risk ones.

## MVP Definition

### Launch With (v1.0)

Minimum viable product -- what is needed to validate that AI-powered traffic-to-rule analysis works and is useful.

- [ ] **VPC Flow Log ingestion from S3 and local files** -- without data, nothing works
- [ ] **Normalization to unified 10-field schema** -- foundation for all analysis
- [ ] **DuckDB storage and Parquet persistence** -- enables fast analytical queries on multi-GB datasets
- [ ] **AWS Security Group rule fetching via boto3** -- must know current state to suggest changes
- [ ] **LLM client via LiteLLM with Ollama support** -- zero-cost local inference for development and privacy-conscious users
- [ ] **4-stage LangGraph pipeline (Analyze, Assess, Generate, Decide)** -- the core AI value proposition
- [ ] **Structured Pydantic output from every LLM call** -- type-safe, parseable, no free-text fragility
- [ ] **Pipeline checkpointing via SQLiteSaver** -- resume from failure without re-running expensive LLM calls
- [ ] **Rich terminal output with risk-colored tables** -- CLI-first product must have beautiful output
- [ ] **JSON output** -- machine-readable for integration
- [ ] **YAML configuration system** -- don't force 20 CLI flags on every invocation
- [ ] **Immutable audit log in SQLite** -- compliance readiness from day one
- [ ] **Suggest-only mode (no apply capability)** -- safety-first, build trust before automation

### Add After Validation (v1.x)

Features to add once the core pipeline is proven accurate and useful.

- [ ] **SARIF output for CI/CD integration** -- trigger: users ask to run PolicyFoundry in GitHub Actions
- [ ] **Threat intelligence tool (AbuseIPDB/GreyNoise free tier)** -- trigger: users want IP reputation context in assessments
- [ ] **Overly permissive rule detection as standalone command** -- trigger: users want quick SG audit without full pipeline
- [ ] **Unused rule detection as standalone command** -- trigger: users want cleanup recommendations without AI analysis
- [ ] **LLM cost tracking and budget limits** -- trigger: users move from Ollama to cloud LLM providers
- [ ] **Human-in-the-loop approval gate via LangGraph interrupt** -- trigger: users want to approve/reject individual suggestions interactively
- [ ] **Pipeline replay from checkpoint** -- trigger: users want to re-run from a specific stage after adjusting config
- [ ] **Cloud LLM support (AWS Bedrock Claude, OpenAI)** -- trigger: users want higher-quality analysis than local models provide

### Future Consideration (v2+)

Features to defer until product-market fit is established.

- [ ] **Auto-apply mode with graduated autonomy** -- why defer: trust must be earned through suggestion accuracy; requires safety mechanisms (circuit breaker, kill switch, emergency revert)
- [ ] **Web dashboard with network topology visualization** -- why defer: doubles codebase; CLI must be proven first
- [ ] **Multi-cloud adapters (Azure NSG, GCP Firewall Rules)** -- why defer: each adapter is significant work; prove on AWS first
- [ ] **Palo Alto Cloud NGFW adapter** -- why defer: different API model, two-phase commit complexity
- [ ] **Compliance report generation (PCI-DSS, SOC 2)** -- why defer: deep domain expertise needed; better to integrate with compliance platforms
- [ ] **Team collaboration, RBAC, SSO** -- why defer: enterprise features for when there are enterprise customers
- [ ] **Micro-batch / near-real-time monitoring** -- why defer: batch analysis is sufficient for policy management cadence
- [ ] **Natural language query interface** -- why defer: different interaction model; dilutes focus on structured pipeline

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Flow log ingestion + normalization | HIGH | MEDIUM | P1 |
| DuckDB storage + Parquet | HIGH | MEDIUM | P1 |
| AWS SG rule fetching | HIGH | LOW | P1 |
| LiteLLM + Ollama LLM client | HIGH | MEDIUM | P1 |
| 4-stage LangGraph AI pipeline | HIGH | HIGH | P1 |
| Structured Pydantic LLM output | HIGH | MEDIUM | P1 |
| Pipeline checkpointing (SQLiteSaver) | MEDIUM | LOW | P1 |
| Rich terminal output | HIGH | LOW | P1 |
| JSON output | HIGH | LOW | P1 |
| YAML config system | MEDIUM | LOW | P1 |
| Immutable audit log | MEDIUM | MEDIUM | P1 |
| Suggest-only mode | HIGH | LOW | P1 |
| SARIF output | MEDIUM | MEDIUM | P2 |
| Threat intelligence tool | MEDIUM | MEDIUM | P2 |
| Overly permissive rule detection (standalone) | MEDIUM | LOW | P2 |
| Unused rule detection (standalone) | MEDIUM | MEDIUM | P2 |
| LLM cost tracking | LOW | LOW | P2 |
| Human-in-the-loop approval gate | MEDIUM | MEDIUM | P2 |
| Pipeline replay | LOW | LOW | P2 |
| Cloud LLM providers | MEDIUM | LOW | P2 |
| Auto-apply mode | HIGH | HIGH | P3 |
| Web dashboard | HIGH | HIGH | P3 |
| Multi-cloud adapters | HIGH | HIGH | P3 |
| Compliance reports | MEDIUM | HIGH | P3 |
| RBAC / SSO / team features | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for launch -- without these, the product does not deliver its core promise
- P2: Should have, add after core pipeline is proven -- these increase adoption and utility
- P3: Nice to have, future consideration -- these are Phase 2+ or enterprise tier features

## Competitor Feature Analysis

| Feature | Tufin / AlgoSec / FireMon | AWS Firewall Manager | Google Cloud Firewall Insights | Prowler / ScoutSuite | PolicyFoundry |
|---------|---------------------------|---------------------|-------------------------------|---------------------|---------------|
| Traffic-to-rule analysis | Yes (proprietary engines) | No (compliance only) | Yes (ML-based, GCP only) | No (config audit only) | Yes (LLM-powered, open source) |
| Overly permissive detection | Yes | Yes (content audit policies) | Yes (ML-powered) | Yes (basic CIS checks) | Yes (traffic-based, AI-enhanced) |
| Unused rule detection | Yes (hit count analysis) | No | Yes (ML predictions) | No | Yes (flow log cross-reference) |
| Rule change suggestions | Yes (with workflow) | No (flag only) | Yes (narrower ranges) | No | Yes (with business justification) |
| Compliance reporting | Yes (PCI-DSS, SOC 2, etc.) | Partial (compliance status) | No | Yes (CIS, NIST, PCI) | Phase 2 (audit data export) |
| Multi-vendor support | Yes (100+ vendors) | AWS only | GCP only | Multi-cloud | AWS Phase 1, multi-vendor later |
| Auto-apply rules | Yes (with approval workflow) | Yes (auto-remediation) | No | No | Phase 2+ (graduated autonomy) |
| CI/CD integration | Limited | CloudFormation hooks | No | JSON/CSV output | SARIF output for GitHub/Azure DevOps |
| Local / self-hosted | On-prem option ($$$) | N/A (AWS service) | N/A (GCP service) | Yes (CLI tool) | Yes (CLI + Ollama, zero cloud cost) |
| AI/LLM powered | AlgoSec AI bot (2025) | No | ML for predictions | No | Core architecture (agentic pipeline) |
| Audit trail | Yes (enterprise grade) | AWS CloudTrail | Stackdriver | Report generation | Event-sourced immutable log |
| Pricing | $50K-200K+/year | Per-policy pricing | Per-insight pricing | Free (open source) | Free CLI (open-core BSL 1.1) |
| Risk scoring | Yes | Limited | No | Severity levels | Yes (per-recommendation, calibrated) |

### Key Competitive Insights

1. **The gap PolicyFoundry fills:** No open-source tool combines traffic analysis with AI-powered rule recommendation. Prowler/ScoutSuite audit configurations but don't analyze traffic. AWS Firewall Manager flags compliance issues but doesn't suggest specific rule changes based on traffic patterns. The enterprise NSPM tools (Tufin, AlgoSec, FireMon) do this but cost $50K+/year.

2. **Google Cloud Firewall Insights is the closest analog:** It analyzes traffic patterns to recommend narrower IP/port ranges and uses ML to predict future rule usage. But it is GCP-only, cloud-native (no self-hosting), and does not use LLMs for contextual reasoning.

3. **Skybox Security shut down in February 2025:** This left a gap in the NSPM market. Organizations migrating from Skybox need alternatives, and PolicyFoundry could capture the "self-hosted, cost-effective" segment.

4. **AlgoSec and Tufin added AI features in 2025:** Both introduced AI-powered bots and automated optimization. The market is moving toward AI-assisted policy management, validating PolicyFoundry's approach.

5. **Prowler and ScoutSuite are the open-source competition:** They audit AWS configurations against CIS/NIST/PCI benchmarks. PolicyFoundry differentiates by analyzing actual traffic patterns, not just static configurations.

## Sources

- [FireMon vs AlgoSec vs Tufin comparison](https://www.firemon.com/firemon-vs-algosec-vs-tufin/) -- Feature comparison of major NSPM vendors
- [Top Network Security Policy Management Solutions (AIMultiple)](https://aimultiple.com/network-security-policy-management-solutions) -- NSPM feature categories and market overview
- [AWS Firewall Manager features](https://aws.amazon.com/firewall-manager/features/) -- AWS native SG management capabilities
- [Google Cloud Firewall Insights overview](https://docs.google.com/cloud/network-intelligence-center/docs/firewall-insights/concepts/overview) -- ML-powered rule recommendations on GCP
- [Improve Security Groups using VPC Flow Logs (cloudonaut)](https://cloudonaut.io/improve-security-groups-using-vpc-flow-logs-aws-config/) -- Traffic-based SG recommendation methodology
- [PCI-DSS 4.0 firewall requirements (FwChange)](https://fwchange.com/blog/pci-dss-firewall-compliance) -- Compliance requirements for firewall changes
- [PCI-DSS 4.0 requirements guide (Linford)](https://linfordco.com/blog/pci-dss-4-0-requirements-guide/) -- Mandatory audit trail requirements
- [Skybox Security shutdown (Xcitium)](https://www.xcitium.com/blog/news/what-is-skybox/) -- Skybox operations ceased February 2025
- [NSPM comparison (FortMatrix)](https://sudhir.is-a.dev/posts/NSPM_Comparison/) -- Independent comparison of AlgoSec, Tufin, FireMon
- [Prowler open source security tool](https://github.com/JasonTeixeira/Prowler) -- CIS/NIST/PCI compliance auditing CLI
- [VPC Flow Logs documentation (AWS)](https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs.html) -- Official log format reference
- [AWS-SG-Analyzer (GitHub)](https://github.com/SherifTalaat/AWS-SG-Analyzer) -- Open source SG analysis tool
- [flowlogs-reader (GitHub)](https://github.com/obsrvbl-oss/flowlogs-reader) -- CLI tool for VPC Flow Log reading

---
*Feature research for: AI-powered firewall policy management (PolicyFoundry)*
*Researched: 2026-03-07*
