# Founder Outreach Automation

This repository contains a set of Python scripts to automate sending personalized outreach emails to startup founders. It's designed to securely send emails through Gmail, handle rate-limiting, deduplicate contacts, and gracefully handle connection failures.

## 📁 Project Structure

- **`exports/`**: Drop any `.json` contact exports into this directory. The scripts will automatically scan and merge them.
- **`generate_emails.py`**: Scans the `exports/` directory, extracts valid contacts, removes duplicates, applies your customized email template, and generates `generated_emails.json`.
- **`send_emails.py`**: Reads the generated drafts and sends them via Gmail SMTP. It includes random delays to avoid spam filters, attaches your resume, and keeps a permanent record in `sent_log.json` so you never double-email anyone.
- **`sent_log.json`**: An automatically generated log of every email address that has already been contacted (or failed).
- **`Sumanth_Resume.pdf`**: The resume attachment that is sent with every email.

## 🚀 Setup

### 1. Gmail App Password
To use the Gmail SMTP server, you need to generate an App Password:
1. Ensure 2-Step Verification is enabled on your Google Account.
2. Go to your [Google Account App Passwords page](https://myaccount.google.com/apppasswords).
3. Generate a new App Password.

### 2. Environment Variables
Export your credentials in your terminal session before running the sending script:
```bash
export GMAIL_ADDRESS="your_email@gmail.com"
export GMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"
```

## 🛠 Usage

### Step 1: Add your contacts
Download your founder contact lists and place the `.json` files directly inside the `exports/` folder. The scripts will read all JSON files found in this directory.

### Step 2: Generate Drafts
Run the generation script. This will aggregate all contacts in `exports/`, fallback to alternative emails if a primary business email is missing, deduplicate, and output the drafts to `generated_emails.json`.

```bash
python3 generate_emails.py
```

### Step 3: Send Emails
Run the sender script. It automatically reads `generated_emails.json` and skips anyone already marked as successfully sent in `sent_log.json`.

**Preview emails without sending:**
```bash
python3 send_emails.py --dry-run
```

**Send a specific batch of emails:**
*(It is highly recommended to send in small batches to avoid triggering Gmail rate-limits. e.g., 20-30 per run).*
```bash
python3 send_emails.py --batch-size 20
```

**Clear your send history (DANGER):**
If you want to start completely fresh and delete your send history.
```bash
python3 send_emails.py --reset
```

## ⚙️ Features
- **Smart Fallbacks**: If a contact is missing a formal `CURRENT_BUSINESS_EMAIL`, the script automatically falls back to pulling the first email from the raw `EMAILS` list.
- **Auto-Retry Logic**: If Gmail drops the connection mid-send (or a network timeout occurs), the script logs a failure. On your next run, it will automatically attempt to resend to that contact.
- **Anti-Spam Delays**: Includes a randomized 45 to 120-second delay between sends to mimic human behavior and keep your sender score high.
- **Deduplication**: Strictly prevents you from generating drafts or sending emails to the same address across multiple different export files.
