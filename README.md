# SBP Weighted Average Customer Exchange Rates — Automated PDF Pipeline

An automated Python pipeline that monitors the State Bank of Pakistan (SBP) website daily, downloads the "Weighted Average Customer Exchange Rates" PDF as soon as it's published, validates it, and emails it to stakeholders.

## Features

- **JSON API integration** — Uses SBP's structured API (not fragile HTML scraping)
- **Polling mode** — Automatically retries every 10 minutes during the SBP publication window (4:00–8:00 PM PKT) until the PDF is successfully emailed
- **State management** — Tracks emailed dates in `state.json` to prevent duplicate emails
- **Exponential backoff** — Handles SBP server timeouts and transient failures gracefully
- **PDF validation** — Verifies the downloaded PDF contains today's date on page 1
- **Email retry** — Retries failed email sends up to 3 times before moving to next poll cycle
- **Rotating logs** — All events logged to `logs/sbp_pipeline.log` (5 MB × 5 backups)
- **Audit trail** — Keeps last 30 email records in `state.json` + retains downloaded PDFs

## Prerequisites

- **Python 3.9+** (uses `zoneinfo` for timezone handling)
- A Gmail account with **App Password** (or any SMTP server)

## Quick Start

### 1. Clone / Download

```bash
cd /path/to/automation_1
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs only 2 packages:
- `requests` — HTTP client
- `pdfplumber` — PDF text extraction

### 3. Configure Environment Variables

Copy the example config and fill in your credentials:

```bash
# Linux / Mac
cp config.env.example .env
nano .env

# Windows
copy config.env.example .env
notepad .env
```

**Required variables:**

| Variable | Example | Description |
|----------|---------|-------------|
| `SMTP_HOST` | `smtp.gmail.com` | SMTP server |
| `SMTP_PORT` | `587` | Port (587=TLS, 465=SSL) |
| `SMTP_USER` | `you@gmail.com` | Login username |
| `SMTP_PASSWORD` | `abcd efgh ijkl mnop` | App Password |
| `EMAIL_FROM` | `you@gmail.com` | Sender address |
| `EMAIL_TO` | `a@x.com,b@x.com` | Comma-separated recipients |

**Gmail App Password Setup:**
1. Enable 2-Step Verification: https://myaccount.google.com/security
2. Generate App Password: https://myaccount.google.com/apppasswords
3. Use the 16-character password as `SMTP_PASSWORD`

### 4. Load Environment & Run

```bash
# Linux / Mac — load .env and run
export $(grep -v '^#' .env | xargs)
python main.py

# Windows PowerShell — load .env and run
Get-Content .env | ForEach-Object {
    if ($_ -and $_ -notmatch '^\s*#') {
        $parts = $_ -split '=', 2
        [System.Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim(), 'Process')
    }
}
python main.py
```

## How It Works

### Pipeline Flow

```
Scheduler triggers main.py
  → Weekend? → Exit
  → Already emailed today? → Exit silently
  → Within poll window (4:00–8:00 PM)?
      YES → POLLING MODE (loop every 10 min until success)
      NO  → SINGLE CHECK MODE (one attempt, then exit)
  → Fetch SBP JSON API (with exponential backoff)
  → Find today's entry by date field
  → Download PDF (stream + backoff)
  → Validate PDF content (check date on page 1)
  → Send email with PDF attachment (retry up to 3×)
  → Update state.json (ONLY after confirmed delivery)
```

### Key Design Decisions

1. **API over HTML scraping**: SBP's page is JavaScript-rendered. We hit their JSON API directly.
2. **Date matching by API field**: SBP filenames vary wildly (`10-Jul-26-WA.pdf`, `30-Jun-26.pdf`, etc.). We match by the API's `date` field.
3. **State = success gate**: `state.json` is only written after a confirmed email send. Any failure means automatic retry.
4. **PDF validation is soft**: If the date isn't found on page 1 (unusual format), we log a warning but still send the email.

## Scheduling

### Linux / Mac — Cron

The recommended schedule runs the script at 4:00 PM PKT. The built-in polling loop handles the rest:

```cron
# Run at 4:00 PM PKT (Mon–Fri). The script's polling loop handles retries.
0 16 * * 1-5 cd /path/to/automation_1 && export $(grep -v '^\#' .env | xargs) && /usr/bin/python3 main.py >> /dev/null 2>&1
```

Edit crontab:
```bash
crontab -e
```

> **Note:** The script internally polls every 10 minutes until 8:00 PM PKT. You only need ONE cron entry.

### Windows — Task Scheduler

1. **Open Task Scheduler**: `Win + R` → `taskschd.msc`

2. **Create Basic Task**:
   - Name: `SBP Exchange Rate Pipeline`
   - Trigger: Daily at `4:00 PM`, repeat every day
   - Conditions: Uncheck "Start only if on AC power"

3. **Action**: Start a program
   - Program: `C:\path\to\python.exe`
   - Arguments: `main.py`
   - Start in: `C:\Users\Uzair Ahmed\OneDrive\Desktop\automation_1`

4. **Weekday-only** (optional): In the trigger settings, select "Weekly" and check only Mon–Fri.

5. **Environment Variables**: Create a `run.bat` wrapper:

```bat
@echo off
REM Load environment variables
for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
    echo %%A | findstr /r "^#" >nul || set "%%A=%%B"
)
python main.py
```

Set the Task Scheduler action to run `run.bat` instead.

### Alternative: Windows PowerShell Scheduled Job

```powershell
$trigger = New-JobTrigger -Daily -At "4:00 PM" -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday
$script = {
    Set-Location "C:\Users\Uzair Ahmed\OneDrive\Desktop\automation_1"
    Get-Content .env | ForEach-Object {
        if ($_ -and $_ -notmatch '^\s*#') {
            $parts = $_ -split '=', 2
            [System.Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim(), 'Process')
        }
    }
    python main.py
}
Register-ScheduledJob -Name "SBP_Exchange_Rate_Pipeline" -Trigger $trigger -ScriptBlock $script
```

## Project Structure

```
automation_1/
├── main.py              # Pipeline script (single entry point)
├── requirements.txt     # Python dependencies (2 packages)
├── config.env.example   # Environment variable template
├── .gitignore           # Excludes runtime artifacts
├── README.md            # This file
│
├── logs/                # Auto-created
│   └── sbp_pipeline.log # Rotating log (5MB × 5)
├── downloads/           # Auto-created
│   └── *.pdf            # Downloaded PDFs
└── state.json           # Auto-created (tracks last emailed date)
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `Missing required environment variables` | Set all 6 required env vars (see config.env.example) |
| `SMTP authentication failed` | Use a Gmail App Password, not your regular password |
| `Today's file not yet uploaded` | Normal — SBP publishes between 4:30–6:00 PM PKT |
| `Connection error / Timeout` | SBP site is slow — backoff handles this automatically |
| `PDF validation failed` | Warning only — email still sends. SBP may use unusual date format |
| `Poll window closed without success` | Check if SBP published today. May be a holiday. |
| Duplicate emails | Should never happen — `state.json` prevents this |

## Log Example

```
16:00:05 | INFO     | SBP EXCHANGE RATE PIPELINE — Run Started
16:00:05 | INFO     | Current PKT time: 2026-07-28 16:00:05 PKT | Target date: 2026-07-28 (Tuesday)
16:00:05 | INFO     | POLLING MODE: Within poll window (16:00 – 20:00 PKT).
16:00:05 | INFO     | ── Poll cycle #1 at 16:00:05 PKT ──
16:00:06 | INFO     | Fetching SBP exchange rate data from API...
16:00:08 | INFO     | Fetched 250 entries from SBP API. Latest entry date: 2026-07-27
16:00:08 | INFO     | Today's file (2026-07-28) not yet uploaded.
16:00:08 | INFO     | Waiting 10 minutes before next check...
16:10:08 | INFO     | ── Poll cycle #2 at 16:10:08 PKT ──
16:10:10 | INFO     | FOUND today's entry — title='weighted-average-...' | date=2026-07-28
16:10:12 | INFO     | Downloaded: weighted-average-...-28-july-2026.pdf (45.3 KB)
16:10:12 | INFO     | PDF VALIDATED — found date pattern '28-July-2026' on page 1.
16:10:14 | INFO     | EMAIL SENT SUCCESSFULLY (attempt 1/3) to stakeholder@example.com
16:10:14 | INFO     | STATE UPDATED: Marked 2026-07-28 as successfully emailed.
16:10:14 | INFO     | PIPELINE COMPLETE — PDF for 2026-07-28 emailed successfully.
```

## License

MIT — Use freely.
