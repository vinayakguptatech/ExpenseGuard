# ExpenseGuard

**AI agent for automated expense policy compliance & invoice auditing**

## The problem

Finance teams manually review expense claims and vendor invoices for policy
violations — duplicate submissions, missing tax IDs, spend limits, split
billing to dodge approval thresholds. It's slow, easy to miss patterns
across hundreds of claims, and usually caught *after* money has already
moved.

## The solution

ExpenseGuard is a three-stage pipeline:

1. **OCR extraction** — a vision-capable LLM (Groq's Llama 4 Scout) reads
   an invoice/receipt image and extracts structured fields (vendor,
   amount, date, GSTIN, invoice number, category).
2. **Policy rule engine** — a deterministic, auditable set of rules checks
   the extracted fields (amount thresholds, duplicate invoice numbers,
   missing GSTIN, split-billing patterns, blocked categories).
3. **LLM reasoning agent** — turns rule violations into a plain-English
   explanation, an overall risk score, and a recommended action, so a
   non-technical reviewer instantly understands *why* something was flagged.

The rule engine is deliberately deterministic (not "the AI decided") —
the LLM's job is to explain and reason about violations, not to be the sole
arbiter of whether policy was broken. That split is what makes this
auditable enough for a real finance team to trust.

## Quickstart

```bash
pip install -r requirements.txt

# Optional but recommended — enables full LLM reasoning explanations.
# Without it, the app still runs using the rule engine's own messages.
# Get a free key (no credit card needed) at https://console.groq.com
export GROQ_API_KEY=your_key_here

streamlit run app.py
```

This launches a two-tab app:
- **Review invoices** — walks through 8 sample invoices, showing extracted
  fields, rule violations, risk score, and recommended action for each.
- **Impact dashboard** — aggregate stats, a violation-type breakdown chart,
  and an estimated analyst-hours-saved calculation.

## Project structure

```
expenseguard/
├── app.py                  # Streamlit UI (two tabs: review + dashboard)
├── policy_config.py        # Editable policy thresholds (no code changes needed)
├── policy_rules.py          # Deterministic rule engine
├── ocr_extraction.py        # Vision-LLM based field extraction (needs API key)
├── reasoning_agent.py        # LLM explanation + risk scoring layer
├── sample_invoices/
│   └── invoices.json        # 8 synthetic invoices (mix of clean + violating)
└── requirements.txt
```

## What it catches (demo dataset)

| Invoice | Issue |
|---|---|
| INV-2002 (2nd occurrence) | Duplicate invoice number reused |
| INV-2004 | Missing GSTIN above ₹5,000 |
| INV-2006 | Split billing — same vendor/day, combined total over threshold |
| INV-2008 | Blocked category (alcohol) |

## Razorpay angle

In production, this check would run **before** a vendor payout is
initiated through RazorpayX — catching policy violations pre-payment,
rather than during a post-hoc audit after the money has already left the
account.

## What's next

- Real OCR testing against scanned/photographed receipts (currently
  validated against clean sample images)
- Vendor-name fuzzy-matching to catch near-duplicate vendors
  ("Cafe Bloom" vs "Cafe Bloomm") used to evade duplicate detection
- Slack/email notification hook for high-risk flags
- Configurable policy per department/cost-center
