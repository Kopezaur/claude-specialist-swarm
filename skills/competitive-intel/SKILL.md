---
name: competitive-intel
description: BTS-Synthetic competitive battlecards for the Enterprise Data Platform space. Use whenever assessing who else is likely competing for an RFP and how to position against them. Covers Databricks, Snowflake, Microsoft Fabric, and Google BigQuery as the four most common competitors we see in enterprise deals.
---

# Competitive Intelligence

Use this when the coordinator asks you to identify competitors and recommend positioning.

## Pattern matching: who's in the deal?

| RFP signal | Likely competitor |
| --- | --- |
| Lots of mentions of "Lakehouse architecture", "MLflow integration", "Delta tables" | **Databricks** |
| Heavy SQL emphasis, "data marketplace", "secure data sharing", existing Snowflake user mentioned | **Snowflake** |
| Customer is heavy Microsoft shop, Azure-only, mentions of Power BI integration | **Microsoft Fabric** |
| Customer is GCP-native, mentions BigQuery ML, Looker | **Google BigQuery** |
| RFP asks about open-source compatibility / no vendor lock-in | Possibly Databricks, possibly an open-source rival like Trino+Iceberg |

If two or more of these signals appear, both competitors are likely shortlisted.

## Battlecards

### vs. Databricks

**Their strengths:**
- Strong ML/AI story (MLflow, Mosaic)
- Lakehouse / Delta is genuinely good for very large-scale workloads
- Open file format reduces lock-in concern
- Brand momentum among data engineering teams

**Their weaknesses:**
- Total cost of ownership often surprises customers (compute spend ramps fast)
- Less mature on BI / analyst-friendly tooling
- Spark-based query latency for interactive analytics can be poor

**Our angles:**
- Lead with TCO: produce a 3-year cost projection. We win on predictable spend.
- Position on time-to-insight for analyst personas, not just engineers.
- Don't fight on ML breadth. Concede that and pivot.

**Trap to avoid:**
- Don't try to out-engineer them on Spark or Iceberg. You'll lose on technical ground.

---

### vs. Snowflake

**Their strengths:**
- Best-in-class analyst experience
- Mature data sharing
- "Just works" reputation

**Their weaknesses:**
- Expensive at scale (the standard procurement complaint)
- Less flexible for unstructured / semi-structured / real-time
- ML/AI story is bolted-on, not native

**Our angles:**
- Lead with workload coverage: real-time, semi-structured, unstructured.
- Highlight ML-native architecture.
- Run a TCO comparison at customer's projected scale — usually wins on year 2+.

**Trap to avoid:**
- Don't try to out-analyst-tool Snowflake on day 1. They've been polishing that experience for a decade.

---

### vs. Microsoft Fabric

**Their strengths:**
- E5 license inclusion makes the headline price look free
- Tight Power BI integration
- Already deployed in the customer's tenant

**Their weaknesses:**
- Maturity gaps in core capabilities (still catching up on basic features)
- Lock-in to Azure-only
- Performance consistency varies

**Our angles:**
- Honest TCO including Microsoft consulting hours
- Multi-cloud story (don't lock yourself in)
- Maturity: we've been doing this for 8 years; they've been doing it for 18 months.

**Trap to avoid:**
- Don't compete on Power BI integration. We integrate, they own.
- Don't dismiss the "free with E5" claim. Acknowledge it directly and reframe to TCO.

---

### vs. Google BigQuery

**Their strengths:**
- Truly serverless analytics — no cluster management
- Strong on standard SQL workloads
- Vertex AI integration is genuinely useful

**Their weaknesses:**
- GCP-only (deal-breaker for multi-cloud customers)
- Less mature governance / data-mesh story
- Streaming ingest costs add up

**Our angles:**
- Multi-cloud flexibility
- Governance and data-mesh maturity
- Workload portability

**Trap to avoid:**
- Don't claim better serverless than BigQuery. We're not.

## When competitors are named in the RFP

If the RFP discloses its vendor shortlist, do not guess — analyse each named competitor directly. Skip pattern matching for named competitors; use it only to assess unnamed ones.

For named competitors, your output structure changes:
1. For each named competitor: threat level (HIGH / MEDIUM / LOW) + why
2. Their specific strengths on THIS RFP (not generic)
3. Their specific weaknesses on THIS RFP (not generic)
4. Our one-line counter-positioning message
5. One trap per competitor

For unnamed competitors in the shortlist ("a regional vendor we will not name"):
- Assess what segment the unnamed vendor is likely from, based on RFP signals
- Apply pattern-matching table above
- Assign a threat level with rationale

## Ranked threat analysis (required)

After individual battlecards, always close with:

```
THREAT RANKING
1. [Competitor] — [why they are the biggest threat on this specific deal]
2. [Competitor] — ...
3. [Competitor] — ...

Our primary target to displace: [single competitor]
Reason: [one sentence]

Win probability: HIGH / MEDIUM / LOW
Rationale: [1–2 sentences — what tips the deal toward or away from us]

Our best opening move: [single specific recommendation, e.g. "Run a 3-year TCO comparison against Microsoft Fabric at Acme's actual Azure spend"]
```

## How to format your output

For each competitor (named or inferred):
1. Why they are in this deal (cite RFP signals or stated shortlist)
2. Their strengths AGAINST OUR ANGLES on this deal
3. Their weaknesses we can exploit
4. Our one-line counter-positioning message
5. One trap

Then the ranked threat analysis block above.
