"""
Send personalized outreach emails to startup founders.

Reads generated_emails.json, attaches your resume, and sends via Gmail SMTP
with rate limiting to avoid spam filters.

Features:
  - Rate limiting: random 30-90s delay between emails
  - Daily batch limit: configurable (default 20/day)
  - Resume tracking: logs sent emails to sent_log.json so you can resume
  - Dry-run mode: preview without sending
  - Resume PDF auto-attached

Setup:
  1. Enable 2FA on your Gmail account
  2. Generate an App Password: https://myaccount.google.com/apppasswords
  3. Set environment variables:
       export GMAIL_ADDRESS="your_email@gmail.com"
       export GMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"

Usage:
  python send_emails.py --dry-run          # Preview emails (no sending)
  python send_emails.py --batch-size 35     # Send 5 emails this run
  python send_emails.py                    # Send up to DAILY_LIMIT emails
  python send_emails.py --reset            # Clear sent log and start over
"""

import argparse
import json
import os
import random
import smtplib
import sys
import time
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ── Config ──────────────────────────────────────────────────────────────────────

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EMAILS_FILE = os.path.join(BASE_DIR, "generated_emails.json")
SENT_LOG_FILE = os.path.join(BASE_DIR, "sent_log.json")
RESUME_FILE = os.path.join(BASE_DIR, "Sumanth_Resume.pdf")

DAILY_LIMIT = 25             # Max emails per run (Gmail safe zone)
MIN_DELAY_SECONDS = 45        # Min seconds between emails
MAX_DELAY_SECONDS = 120       # Max seconds between emails

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587


# ── Sent log management ────────────────────────────────────────────────────────

def load_sent_log() -> dict:
    """Load the sent log. Returns {email_address: {timestamp, status}}."""
    if os.path.exists(SENT_LOG_FILE):
        with open(SENT_LOG_FILE, "r") as f:
            return json.load(f)
    return {}


def save_sent_log(log: dict):
    """Persist the sent log."""
    with open(SENT_LOG_FILE, "w") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)


def mark_sent(log: dict, email: str, status: str = "sent"):
    """Mark an email as sent in the log."""
    log[email.lower()] = {
        "timestamp": datetime.now().isoformat(),
        "status": status,
    }
    save_sent_log(log)


# ── Email sending ──────────────────────────────────────────────────────────────

def create_message(draft: dict, from_email: str) -> MIMEMultipart:
    """Build a MIME email with the resume attached."""
    msg = MIMEMultipart()
    msg["From"] = f"Sumanth <{from_email}>"
    msg["To"] = f"{draft['to_name']} <{draft['to_email']}>"
    msg["Subject"] = draft["subject"]

    # Body
    msg.attach(MIMEText(draft["body"], "plain"))

    # Attach resume
    if os.path.exists(RESUME_FILE):
        with open(RESUME_FILE, "rb") as f:
            resume = MIMEApplication(f.read(), _subtype="pdf")
            resume.add_header(
                "Content-Disposition",
                "attachment",
                filename="Sumanth_Resume.pdf",
            )
            msg.attach(resume)

    return msg


def send_batch(drafts: list[dict], dry_run: bool = False, batch_limit: int = DAILY_LIMIT):
    """Send a batch of emails with rate limiting."""
    gmail_address = os.environ.get("GMAIL_ADDRESS", "")
    gmail_password = os.environ.get("GMAIL_APP_PASSWORD", "")

    if not dry_run and (not gmail_address or not gmail_password):
        print("❌ Missing credentials. Set these environment variables:")
        print("   export GMAIL_ADDRESS='your_email@gmail.com'")
        print("   export GMAIL_APP_PASSWORD='xxxx xxxx xxxx xxxx'")
        print()
        print("   To generate an App Password:")
        print("   https://myaccount.google.com/apppasswords")
        sys.exit(1)

    sent_log = load_sent_log()

    # Filter out already-sent emails
    pending = [
        d for d in drafts
        if d["to_email"].lower() not in sent_log or not sent_log[d["to_email"].lower()].get("status", "").startswith("sent")
    ]

    if not pending:
        print("✅ All emails have already been sent! Nothing to do.")
        print(f"   ({len(sent_log)} emails in sent log)")
        print(f"   Use --reset to clear the sent log and start over.")
        return

    total_sent = len(sent_log)
    to_send = pending[:batch_limit]
    remaining = len(pending) - len(to_send)

    print(f"📊 Status:")
    print(f"   Total drafts:    {len(drafts)}")
    print(f"   Already sent:    {total_sent}")
    print(f"   Pending:         {len(pending)}")
    print(f"   This batch:      {len(to_send)}")
    print(f"   After this run:  {remaining} remaining")
    print(f"   Mode:            {'🧪 DRY RUN' if dry_run else '📤 LIVE'}")
    print()

    # Connect to SMTP
    server = None
    if not dry_run:
        try:
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30)
            server.starttls()
            server.login(gmail_address, gmail_password)
            print("✅ Connected to Gmail SMTP\n")
        except Exception as e:
            print(f"❌ Failed to connect to Gmail: {e}")
            sys.exit(1)

    for i, draft in enumerate(to_send):
        email_num = i + 1
        print(f"[{email_num}/{len(to_send)}] {'📧' if not dry_run else '👀'} "
              f"{draft['to_name']} <{draft['to_email']}> "
              f"({draft['company']})")

        if dry_run:
            print(f"         Subject: {draft['subject']}")
            print(f"         Body preview: {draft['body'][:100]}...")
            mark_sent(sent_log, draft["to_email"], status="dry_run")
        else:
            try:
                msg = create_message(draft, gmail_address)
                server.send_message(msg)
                mark_sent(sent_log, draft["to_email"], status="sent")
                print(f"         ✅ Sent successfully")
            except Exception as e:
                mark_sent(sent_log, draft["to_email"], status=f"failed: {e}")
                print(f"         ❌ Failed: {e}")

        # Rate limiting (skip delay after last email)
        if i < len(to_send) - 1:
            delay = random.uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS)
            print(f"         ⏳ Waiting {delay:.0f}s before next email...")
            if not dry_run:
                time.sleep(delay)

        print()

    # Cleanup
    if server:
        try:
            server.quit()
        except Exception:
            pass

    # Summary
    print("─" * 60)
    print(f"✅ Batch complete!")
    print(f"   Sent this run: {len(to_send)}")
    print(f"   Total sent:    {len(sent_log)}")
    if remaining > 0:
        mins = remaining * ((MIN_DELAY_SECONDS + MAX_DELAY_SECONDS) / 2) / 60
        print(f"   Remaining:     {remaining} "
              f"(~{remaining // batch_limit + 1} more runs needed)")
    print(f"   Log file:      {SENT_LOG_FILE}")


# ── CLI ─────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Send personalized outreach emails with rate limiting"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview emails without sending",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help=f"Number of emails to send this run (default: {DAILY_LIMIT})",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Clear the sent log and start fresh",
    )
    args = parser.parse_args()

    # Handle reset
    if args.reset:
        if os.path.exists(SENT_LOG_FILE):
            os.remove(SENT_LOG_FILE)
            print("🗑️  Sent log cleared.")
        else:
            print("ℹ️  No sent log found.")
        return

    # Override batch size
    batch_size = args.batch_size if args.batch_size else DAILY_LIMIT

    # Load drafts
    if not os.path.exists(EMAILS_FILE):
        print("❌ generated_emails.json not found. Run generate_emails.py first.")
        sys.exit(1)

    with open(EMAILS_FILE, "r") as f:
        drafts = json.load(f)

    print(f"📬 Outreach Email Sender")
    print(f"{'='*60}\n")

    send_batch(drafts, dry_run=args.dry_run, batch_limit=batch_size)


if __name__ == "__main__":
    main()
