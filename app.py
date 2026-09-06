import json
import os

import pandas as pd
import streamlit as st

from policy_rules import check_invoice
from reasoning_agent import get_risk_assessment

st.set_page_config(page_title="ExpenseGuard", layout="wide")
st.title("ExpenseGuard")
st.caption("AI agent for automated expense policy compliance & invoice auditing")

HAS_API_KEY = bool(os.environ.get("GROQ_API_KEY"))

with open("sample_invoices/invoices.json") as f:
    SAMPLE_INVOICES = json.load(f)


def run_pipeline(invoices):
    """Run every invoice through the rule engine + reasoning agent, building
    up the ledger as we go so duplicate/split-billing checks can see prior
    invoices - exactly like a real system processing a batch."""
    results = []
    ledger = []
    for inv in invoices:
        violations = check_invoice(inv, ledger)
        if HAS_API_KEY:
            assessment = get_risk_assessment(inv, violations)
        else:
            # Demo-safe fallback so the app works with zero setup
            if not violations:
                assessment = {
                    "risk_score": "low",
                    "explanation": "No policy violations detected.",
                    "recommended_action": "auto_approve",
                }
            else:
                severities = [v["severity"] for v in violations]
                risk = "high" if "high" in severities else "medium"
                assessment = {
                    "risk_score": risk,
                    "explanation": " | ".join(v["message"] for v in violations),
                    "recommended_action": "hold_for_review" if risk == "high" else "escalate_to_manager",
                }
        results.append({"invoice": inv, "violations": violations, "assessment": assessment})
        ledger.append(inv)
    return results


def assess_single(inv, ledger):
    """Run one invoice through rules + reasoning, same logic as run_pipeline
    but for a single ad-hoc invoice (used by the 'Try your own' tab)."""
    violations = check_invoice(inv, ledger)
    if HAS_API_KEY:
        assessment = get_risk_assessment(inv, violations)
    else:
        if not violations:
            assessment = {
                "risk_score": "low",
                "explanation": "No policy violations detected.",
                "recommended_action": "auto_approve",
            }
        else:
            severities = [v["severity"] for v in violations]
            risk = "high" if "high" in severities else "medium"
            assessment = {
                "risk_score": risk,
                "explanation": " | ".join(v["message"] for v in violations),
                "recommended_action": "hold_for_review" if risk == "high" else "escalate_to_manager",
            }
    return {"invoice": inv, "violations": violations, "assessment": assessment}


def render_result(r):
    inv = r["invoice"]
    risk = r["assessment"]["risk_score"]
    color = {"low": "green", "medium": "orange", "high": "red"}[risk]
    st.markdown(f"### Result: :{color}[{risk.upper()} RISK]")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Extracted / entered fields")
        st.json(inv)
    with col2:
        st.subheader("Assessment")
        st.markdown(f"**Recommended action:** {r['assessment']['recommended_action']}")
        st.markdown(f"**Explanation:** {r['assessment']['explanation']}")
        if r["violations"]:
            st.subheader("Rule violations")
            for v in r["violations"]:
                st.markdown(f"- **{v['rule']}** ({v['severity']}): {v['message']}")
        else:
            st.success("No rule violations.")


tab1, tab2, tab3 = st.tabs(["Review invoices", "Impact dashboard", "Try your own invoice"])

with tab1:
    if not HAS_API_KEY:
        st.info(
            "No GROQ_API_KEY set - running with rule-engine-only "
            "explanations. Set the env var to see full LLM reasoning."
        )

    results = run_pipeline(SAMPLE_INVOICES)

    for r in results:
        inv = r["invoice"]
        risk = r["assessment"]["risk_score"]
        color = {"low": "green", "medium": "orange", "high": "red"}[risk]

        with st.expander(
            f"{inv['invoice_number']} — {inv['vendor']} — ₹{inv['amount']:,.0f}  "
            f":{color}[{risk.upper()} RISK]"
        ):
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Extracted fields")
                st.json(inv)
            with col2:
                st.subheader("Assessment")
                st.markdown(f"**Risk:** :{color}[{risk.upper()}]")
                st.markdown(f"**Recommended action:** {r['assessment']['recommended_action']}")
                st.markdown(f"**Explanation:** {r['assessment']['explanation']}")
                if r["violations"]:
                    st.subheader("Rule violations")
                    for v in r["violations"]:
                        st.markdown(f"- **{v['rule']}** ({v['severity']}): {v['message']}")
                else:
                    st.success("No rule violations.")

with tab2:
    st.subheader("Batch impact summary")

    results = run_pipeline(SAMPLE_INVOICES)
    total = len(results)
    flagged = [r for r in results if r["violations"]]
    high_risk = [r for r in results if r["assessment"]["risk_score"] == "high"]

    col1, col2, col3 = st.columns(3)
    col1.metric("Invoices processed", total)
    col2.metric("Flagged for review", len(flagged))
    col3.metric("High risk", len(high_risk))

    st.divider()
    st.markdown("**Estimated impact (assumption-based)**")
    st.markdown(
        "Assuming a mid-size company processes **5,000 expense claims/month** "
        f"and this sample's **{len(flagged)}/{total} ({len(flagged)/total:.0%}) flag rate** "
        "holds, that's roughly "
        f"**{int(5000 * len(flagged) / total):,} claims/month** that would need review — "
        "each taking a finance analyst an estimated 5 minutes to check manually. "
        f"That's about **{int(5000 * len(flagged) / total * 5 / 60):,} analyst-hours/month** "
        "ExpenseGuard could save by pre-flagging only the invoices that actually need eyes."
    )

    st.divider()
    st.markdown("**Violation breakdown**")
    rule_counts = {}
    for r in results:
        for v in r["violations"]:
            rule_counts[v["rule"]] = rule_counts.get(v["rule"], 0) + 1
    if rule_counts:
        df = pd.DataFrame(
            {"rule": list(rule_counts.keys()), "count": list(rule_counts.values())}
        ).sort_values("count", ascending=False)
        st.bar_chart(df.set_index("rule"))
    else:
        st.write("No violations found in this batch.")

    st.divider()
    st.markdown(
        "**Razorpay angle:** in production, this check would run "
        "*before* a vendor payout is initiated through RazorpayX — "
        "catching policy violations pre-payment instead of during a "
        "post-hoc audit, when the money has already left the account."
    )

with tab3:
    st.subheader("Check a new invoice")
    st.caption(
        "This is the live input path — a real user would land here to check "
        "one new invoice, either by uploading an image or typing in the details."
    )

    input_mode = st.radio(
        "How do you want to provide the invoice?",
        ["Upload an image (uses AI OCR)", "Enter details manually"],
        horizontal=True,
    )

    if input_mode == "Upload an image (uses AI OCR)":
        uploaded_file = st.file_uploader("Upload an invoice/receipt image", type=["png", "jpg", "jpeg"])

        if uploaded_file is not None:
            if not HAS_API_KEY:
                st.warning(
                    "OCR extraction needs GROQ_API_KEY to be set - it calls a vision "
                    "model to read the image. Use 'Enter details manually' instead, "
                    "or set the key and re-upload."
                )
            else:
                # Save the upload to a temp file since extract_invoice_fields expects a path
                temp_path = f"_temp_{uploaded_file.name}"
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                st.image(uploaded_file, caption="Uploaded invoice", width=300)

                with st.spinner("Reading invoice with AI OCR..."):
                    from ocr_extraction import extract_invoice_fields
                    extracted = extract_invoice_fields(temp_path)

                os.remove(temp_path)

                if "error" in extracted:
                    st.error(f"Could not extract fields: {extracted.get('raw', extracted['error'])}")
                else:
                    st.success("Fields extracted. Review before checking policy:")
                    extracted.setdefault("approved_by_manager", False)
                    st.json(extracted)
                    if st.button("Run policy check on these fields"):
                        result = assess_single(extracted, SAMPLE_INVOICES)
                        render_result(result)

    else:
        with st.form("manual_invoice_form"):
            col1, col2 = st.columns(2)
            with col1:
                vendor = st.text_input("Vendor name", value="New Vendor Pvt Ltd")
                amount = st.number_input("Amount (₹)", min_value=0, value=5000, step=100)
                date = st.date_input("Invoice date")
                invoice_number = st.text_input("Invoice number", value="INV-3001")
            with col2:
                gstin = st.text_input("GSTIN (leave blank if none)", value="")
                category = st.selectbox(
                    "Category",
                    ["office_supplies", "travel", "printing", "food",
                     "alcohol", "cash_advance", "personal_gifts", "other"],
                )
                approved = st.checkbox("Already approved by manager?")

            submitted = st.form_submit_button("Run policy check")

        if submitted:
            invoice = {
                "vendor": vendor,
                "amount": amount,
                "date": date.isoformat(),
                "gstin": gstin or None,
                "invoice_number": invoice_number,
                "category": category,
                "approved_by_manager": approved,
            }
            result = assess_single(invoice, SAMPLE_INVOICES)
            render_result(result)