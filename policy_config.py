"""
ExpenseGuard policy configuration.

This is intentionally kept as a plain Python dict (not hardcoded logic) so a
finance team could edit these values without touching code. In a real
deployment this would live in a database or a YAML file loaded at runtime.
"""

POLICY = {
    # Any single invoice above this amount (INR) requires manager approval.
    # If the flag "approved_by_manager" is missing/false, it's a violation.
    "max_amount_without_approval": 15000,

    # Invoice numbers must be unique across the ledger. Reusing one is a
    # classic sign of accidental (or deliberate) double reimbursement.
    "block_duplicate_invoice_numbers": True,

    # GST-registered vendors above this threshold must supply a valid GSTIN
    # (15-character alphanumeric) for the expense to be tax-compliant.
    "require_gstin_above_amount": 5000,

    # Splitting one purchase into multiple smaller invoices to duck under
    # the approval threshold is a known evasion pattern. We flag same-vendor,
    # same-day invoices whose combined total crosses the threshold.
    "flag_split_billing": True,
    "split_billing_window_days": 1,

    # Categories that are blocked outright regardless of amount.
    "blocked_categories": ["alcohol", "cash_advance", "personal_gifts"],
}

GSTIN_LENGTH = 15
