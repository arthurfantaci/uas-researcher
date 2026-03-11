---
name: uas-output-schema
description: Standardized output format for UAS research specialist agents
---

# UAS Research Output Format

Every specialist agent MUST produce a markdown file in `output/v2/specialists/` following this structure.

## Required Sections

```markdown
# [Domain Name] — V2 Research Findings

## Executive Summary
2-3 sentence overview of key recommendations and rationale.

## Recommendations

### Primary Recommendation: [Product/Approach Name]
- **Product:** Full name and model
- **Price:** USD
- **Weight:** Grams (if physical component)
- **Key Specs:** 3-5 most important specifications
- **Source URL:** Where to purchase
- **Why:** 2-3 sentences on selection rationale

### Alternatives Considered
| Option | Price | Key Advantage | Why Not Selected |
|--------|-------|---------------|-----------------|
| ... | ... | ... | ... |

## Integration Notes
How this component/system connects to other domains:
- **Dependencies:** What this requires from other specialists
- **Provides:** What this provides to other specialists
- **Constraints imposed:** Weight, power, UART, mounting, etc.

## Changes from V1
What changed vs the V1 report and WHY.

## Open Questions for Team
Questions that require input from other specialists before finalizing.

## Detailed Findings
[Domain-specific deep research — as thorough as needed]
```

## Rules
1. Cite sources with URLs for all product recommendations and technical claims
2. Provide honest cost estimates — do not undercount
3. Flag conflicts with other domains explicitly in "Open Questions for Team"
4. Weight estimates must be from datasheets, not guesses
5. All ArduPilot parameters must include the parameter name AND value
6. Write for a technical audience building their first autonomous UAS
