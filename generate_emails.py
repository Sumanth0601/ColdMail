"""
Generate personalized outreach emails for startup founders.

Reads founder_details.json, filters for contacts with valid emails,
and produces a ready-to-send JSON file with name, email, subject, and body.

Usage:
    python generate_emails.py

Output:
    generated_emails.json  — array of email drafts
    Also prints a summary to stdout.
"""

import json
import os
import re

import glob

# ── Config ──────────────────────────────────────────────────────────────────────

BASE_DIR = os.path.dirname(__file__)
OUTPUT_FILE = os.path.join(BASE_DIR, "generated_emails.json")

SUBJECT = "Backend Engineer — looking to join an early-stage team"

BODY_TEMPLATE = """Hey {first_name},

I'm Sumanth — a backend engineer at Cimpress where I own data pipelines processing 130M+ records/day at 99.9% SLA. I replaced a $30K/year SaaS tool by building the system from scratch with retry logic, schema validation, and parallel execution.

I also built and shipped a production FastAPI service end-to-end — JWT auth, CORS, 100% test coverage, CI/CD, and multi-environment rollout. I'm used to owning things start to finish.

I'm looking to join an early-stage team where I can take full ownership and move fast.

Would love to chat if you're open to it — I've attached my resume.

Best,
Sumanth"""


# ── Parse the NDJSON file ──────────────────────────────────────────────────────

def load_contacts(filepath: str):
    """
    Parse newline-delimited JSON (each object is separated by }\\n{).
    The file isn't a valid JSON array, so we split on '}\n{' boundaries.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        raw = f.read()

    # Split into individual JSON objects
    # The file has objects like: { ... }\n{ ... }\n{ ... }
    # We add commas between them and wrap in an array to parse as valid JSON
    # More robust: use regex to find each top-level { ... } block
    objects = []
    depth = 0
    start = None

    for i, ch in enumerate(raw):
        if ch == '{':
            if depth == 0:
                start = i
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and start is not None:
                try:
                    obj = json.loads(raw[start:i + 1])
                    objects.append(obj)
                except json.JSONDecodeError:
                    pass
                start = None

    return objects


# ── Generate emails ────────────────────────────────────────────────────────────

def generate_email(contact: dict):
    """Build an email draft from a contact dict. Returns None if no valid email."""

    email = contact.get("CURRENT_BUSINESS_EMAIL", "").strip()
    validation = contact.get("CURRENT_BUSINESS_EMAIL_VALIDATION_STATUS", "")

    # Fallback to the first email in EMAILS if CURRENT_BUSINESS_EMAIL is missing
    if not email:
        emails_field = contact.get("EMAILS", "").strip()
        if emails_field:
            email = emails_field.split(",")[0].strip()

    # Skip contacts without a valid email
    if not email:
        return None
        
    # Check validation only if it's the CURRENT_BUSINESS_EMAIL
    if email == contact.get("CURRENT_BUSINESS_EMAIL", "").strip():
        if validation and validation != "valid":
            return None

    first_name = contact.get("FIRST_NAME", "").strip()
    last_name = contact.get("LAST_NAME", "").strip()
    company = contact.get("COMPANY_NAME", "").strip()
    company_domain = contact.get("COMPANY_DOMAIN", "").strip()
    job_title = contact.get("JOB_TITLE", "").strip()

    # Build the full name for reference
    full_name = f"{first_name} {last_name}".strip()

    body = BODY_TEMPLATE.format(first_name=first_name if first_name else "there")

    return {
        "to_name": full_name,
        "to_email": email,
        "first_name": first_name,
        "last_name": last_name,
        "company": company,
        "company_domain": company_domain,
        "job_title": job_title,
        "subject": SUBJECT,
        "body": body,
    }


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    input_files = glob.glob(os.path.join(BASE_DIR, "exports", "*.json"))

    contacts = []
    for f in input_files:
        loaded = load_contacts(f)
        contacts.extend(loaded)
        print(f"📂 Loaded {len(loaded)} contacts from {os.path.basename(f)}")
    print(f"\nTotal loaded contacts: {len(contacts)}\n")

    emails = []
    skipped_no_email = 0
    skipped_invalid = 0
    seen_emails = set()  # deduplicate by email address

    for contact in contacts:
        draft = generate_email(contact)
        if draft is None:
            # Determine why it was skipped for the summary
            email = contact.get("CURRENT_BUSINESS_EMAIL", "").strip()
            if not email:
                emails_field = contact.get("EMAILS", "").strip()
                if emails_field:
                    email = emails_field.split(",")[0].strip()
            
            if not email:
                skipped_no_email += 1
            else:
                skipped_invalid += 1
            continue

        email_addr = draft["to_email"].lower()
        if email_addr in seen_emails:
            continue

        seen_emails.add(email_addr)
        emails.append(draft)

    # Write output
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(emails, f, indent=2, ensure_ascii=False)

    # Print summary
    print(f"✅ Generated {len(emails)} email drafts → generated_emails.json")
    print(f"⏭️  Skipped {skipped_no_email} (no email address)")
    print(f"⏭️  Skipped {skipped_invalid} (invalid email validation)")
    print()

    # Preview first 3
    print("─" * 60)
    print("PREVIEW (first 3 emails):")
    print("─" * 60)
    for i, draft in enumerate(emails[:3]):
        print(f"\n{'='*60}")
        print(f"  To:      {draft['to_name']} <{draft['to_email']}>")
        print(f"  Company: {draft['company']}")
        print(f"  Subject: {draft['subject']}")
        print(f"  {'─'*54}")
        print(f"  {draft['body'][:200]}...")
        print(f"{'='*60}")


if __name__ == "__main__":
    main()
