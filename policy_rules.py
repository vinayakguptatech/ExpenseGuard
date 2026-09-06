"""
Deterministic policy rule engine.

Deliberately NOT an LLM call - these are hard, auditable business rules.
Finance/compliance reviewers trust deterministic checks far more than
"the AI decided this was fine". The LLM reasoning agent (reasoning_agent.py)
is layered on TOP of this for the fuzzier judgment calls.
"""

from datetime import datetime
from policy_config import POLICY, GSTIN_LENGTH


def check_invoice(invoice: dict, ledger: list) -> list:
    """
    Check a single invoice against policy.

    invoice: dict with keys like vendor, amount, date, gstin,
             invoice_number, category, approved_by_manager
    ledger:  list of previously-seen invoice dicts, used to detect
             duplicates and split-billing patterns.

    Returns a list of violation dicts: {rule, severity, message}
    """
    violations = []

    amount = invoice.get("amount", 0)
    vendor = invoice.get("vendor", "unknown")
    invoice_number = invoice.get("invoice_number")
    gstin = invoice.get("gstin")
    category = (invoice.get("category") or "").lower()
    approved = invoice.get("approved_by_manager", False)

    # 1. Amount threshold without approval
    if amount > POLICY["max_amount_without_approval"] and not approved:
        violations.append({
            "rule": "amount_exceeds_threshold",
            "severity": "high",
            "message": (
                f"₹{amount:,.0f} exceeds the ₹{POLICY['max_amount_without_approval']:,} "
                f"threshold and has no manager approval on file."
            ),
        })

    # 2. Duplicate invoice number
    if POLICY["block_duplicate_invoice_numbers"] and invoice_number:
        for prior in ledger:
            if prior.get("invoice_number") == invoice_number and prior is not invoice:
                violations.append({
                    "rule": "duplicate_invoice_number",
                    "severity": "high",
                    "message": (
                        f"Invoice number {invoice_number} was already submitted "
                        f"by {prior.get('vendor', 'a vendor')} on {prior.get('date')}."
                    ),
                })
                break

    # 3. Missing/invalid GSTIN above threshold
    if amount > POLICY["require_gstin_above_amount"]:
        if not gstin:
            violations.append({
                "rule": "missing_gstin",
                "severity": "medium",
                "message": (
                    f"₹{amount:,.0f} claim has no GSTIN on file, required above "
                    f"₹{POLICY['require_gstin_above_amount']:,}."
                ),
            })
        elif len(gstin) != GSTIN_LENGTH:
            violations.append({
                "rule": "invalid_gstin",
                "severity": "medium",
                "message": f"GSTIN '{gstin}' is {len(gstin)} characters, expected {GSTIN_LENGTH}.",
            })

    # 4. Split billing - same vendor, same day (or within window), combined total over threshold
    if POLICY["flag_split_billing"] and invoice.get("date"):
        try:
            inv_date = datetime.fromisoformat(invoice["date"])
            same_window = [
                p for p in ledger
                if p.get("vendor") == vendor
                and p.get("date")
                and abs((datetime.fromisoformat(p["date"]) - inv_date).days) <= POLICY["split_billing_window_days"]
            ]
            combined = sum(p.get("amount", 0) for p in same_window) + (
                amount if invoice not in same_window else 0
            )
            if len(same_window) >= 1 and combined > POLICY["max_amount_without_approval"] and not approved:
                violations.append({
                    "rule": "possible_split_billing",
                    "severity": "high",
                    "message": (
                        f"{vendor} has {len(same_window)} other invoice(s) within "
                        f"{POLICY['split_billing_window_days']} day(s); combined total "
                        f"₹{combined:,.0f} crosses the approval threshold."
                    ),
                })
        except ValueError:
            pass  # malformed date, skip split-billing check

    # 5. Blocked categories
    if category in POLICY["blocked_categories"]:
        violations.append({
            "rule": "blocked_category",
            "severity": "high",
            "message": f"Category '{category}' is not a reimbursable expense type.",
        })

    return violations
