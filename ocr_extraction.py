"""
OCR / field extraction layer.

Uses Groq's vision model (Llama 4 Scout) - a genuinely free, permanent
tier with no credit card required. Get a key at https://console.groq.com

Requires a GROQ_API_KEY environment variable. If you don't have one yet,
use sample_invoices/invoices.json to demo the rest of the pipeline (see
app.py's "Try a sample invoice" tab).
"""

import base64
import json
import os

from groq import Groq

EXTRACTION_PROMPT = """You are an invoice/receipt data extraction engine.
Look at the attached image and extract the following fields as JSON only,
with no other text:

{
  "vendor": string,
  "date": "YYYY-MM-DD" or null,
  "amount": number (the final total, not a line item),
  "gstin": string or null (15-character GSTIN if present),
  "invoice_number": string or null,
  "category": one of ["office_supplies","travel","printing","food",
                       "alcohol","cash_advance","personal_gifts","other"]
}

If a field isn't visible on the document, use null. Respond with ONLY the
JSON object, no markdown fences, no commentary.
"""


def extract_invoice_fields(image_path: str) -> dict:
    """
    Send an invoice/receipt image to Groq's vision model and get back
    structured fields.

    image_path: path to a .jpg/.png file on disk.
    """
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

    with open(image_path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")

    media_type = "image/png" if image_path.lower().endswith("png") else "image/jpeg"

    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": EXTRACTION_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{media_type};base64,{image_data}"},
                    },
                ],
            }
        ],
    )

    raw_text = response.choices[0].message.content.strip()
    raw_text = raw_text.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        return {"error": "Could not parse model output", "raw": raw_text}
