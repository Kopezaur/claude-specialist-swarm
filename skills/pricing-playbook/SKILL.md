---
name: pricing-playbook
description: BTS-Synthetic Deal Desk pricing rules. Use whenever recommending commercial terms for an inbound RFP — covers discount bands, payment terms, term length, and concessions we will and will not make. Trigger on any request to propose pricing, discount, deal structure, or commercial position.
---

# Pricing Playbook

## List prices (Enterprise Data Platform)

| Tier | Annual list | What's included |
| --- | --- | --- |
| Starter | $120K | Up to 10TB ingest, 5 users, business hours support |
| Growth | $360K | Up to 50TB ingest, 25 users, 24/5 support, 99.9% SLA |
| Enterprise | $720K base | Unlimited ingest, unlimited users, 24/7 support, 99.95% SLA, dedicated CSM |

For deals above $500K, Enterprise is the only sensible tier.

## Discount bands

Discount is from list. **Maximum** discount by deal size:

| Annual deal size | Standard max discount | Strategic max discount |
| --- | --- | --- |
| < $250K | 10% | 15% |
| $250K – $500K | 15% | 20% |
| $500K – $1M | 20% | 25% |
| > $1M | 25% | 30% |

"Strategic" requires VP Sales sign-off, only granted when one or more of:
- Brand-name logo in a target vertical (we're targeting financial services, life sciences, government this year)
- Multi-year contract (3+ years committed)
- Reference customer agreement signed

## Payment terms

- **Default:** Annual upfront. Net 30.
- **Acceptable concessions:** Quarterly billing (no price change). Net 60 for Fortune 500 with strong credit.
- **Do not accept:** Net 90+. Monthly billing on annual commitments. Payment tied to milestones.

## Term length

- 1 year: standard, no discount uplift.
- 2 years: additional 3% discount from the discount band.
- 3 years: additional 5% discount, BUT requires annual price escalator of CPI + 2% (capped at 5%).

## Concessions we will make

- **Custom MSA**: yes, on deals > $500K, with legal sign-off.
- **Pilot/POC fees credited toward Year 1**: yes, on all deals.
- **Acceptance testing period**: yes, up to 30 days.
- **Volume true-up at year-end**: yes, with 10% buffer above committed volume.

## Concessions we will NOT make

- **MFN / most-favoured-nation pricing**: never. This is the single most poisonous clause for SaaS. Push back hard.
- **Liability cap above 12 months of fees**: never (insurance binding constraint).
- **Source code escrow**: not for our SaaS product.
- **Unlimited indemnification on data breach**: cap at 24 months of fees, with carve-outs.
- **Refund on termination for convenience**: pro-rated only, no penalty fees.

## Multi-year fixed pricing (no escalators)

Customers sometimes demand fixed pricing across a 3–5 year term with no escalators.

**Our position:** We will not sign a contract that is purely price-fixed over 5 years with no escalator of any kind. Inflation risk over that horizon is material.

**What we will offer instead:**
- 3-year term: CPI + 2% annual escalator, capped at 5% per year. Non-negotiable.
- 4–5 year term: Same escalator mechanism. In exchange we offer a deeper upfront discount (see discount bands).
- If the customer insists on "no escalators," the deal must be structured as 3+2 option years (not a committed 5-year), where option years reprice at then-current list minus the agreed discount band.

**Counter-language for "no escalators" demand:**
> "Pricing for committed years 1–3 is fixed at [agreed rate]. At the start of Year 4 and Year 5 (option periods), annual fees reprice at list minus [agreed discount]%, not to exceed a [X]% increase over the prior year."

**Counter-language for MFN clause:**
> "We do not offer MFN pricing guarantees. Our pricing is structured based on deal-specific scope, volume, and term. We will offer Acme the most competitive rate we can justify given those factors, but we cannot warrant that no other customer receives a different price for a different deal."

## Reading the room

If the RFP suggests the customer is also evaluating Databricks or Snowflake, expect aggressive pricing pressure. We can match their list but won't undercut by more than 10%. Our differentiator is total cost of ownership, not headline price.

If the RFP is for a known difficult-counterparty (procurement-heavy regulated industries), price the deal 5% higher than band to leave room for the haggle.

If the customer demands a discount above our strategic maximum (30%), document that as a walk-away condition and escalate to VP Sales before responding. Do not unilaterally concede beyond band without sign-off.
