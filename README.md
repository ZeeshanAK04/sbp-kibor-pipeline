# SBP KIBOR Rates — Automated PDF Pipeline

An automated Python pipeline that runs on **GitHub Actions** (no server or local machine needs to stay on), monitors the State Bank of Pakistan (SBP) website for the daily KIBOR (Karachi Interbank Offered Rate) PDF, and emails it to a stakeholder list as soon as it's published.

## How it actually runs — no host required

This pipeline does **not** run on your computer or any server you maintain. It runs entirely on **GitHub-hosted Actions runners** — ephemeral virtual machines that GitHub provisions automatically on a schedule, execute the script, then destroy. Your laptop can be off; it doesn't matter.

- **Trigger**: GitHub's own scheduler fires the workflow via cron (`.github/workflows/sbp_pipeline.yml`)
- **Execution**: `main.py` runs on a fresh Ubuntu VM, polls SBP, and exits
- **Secrets**: SMTP credentials are stored as encrypted **GitHub Actions Secrets**, never committed to the repo, injected as env vars only for the duration of each run
- **State**: nothing persists between runs by default — each run starts from a clean VM (see *Known Limitations* below for why this matters)

## Features

- **JSON API integration** — hits SBP's structured API directly (`get-economic-data-by-cat?slug=kibor-rates`) rather than scraping HTML, since the page itself is client-side rendered
- **HTML scrape fallback** — attempts date-pattern matching on the rendered page first; falls back to the API if that fails
- **Polling within a single run** — once triggered, retries every 10 minutes until the PDF is found or a cutoff time is reached, rather than checking only once
- **Exponential backoff** — on network/timeout errors when hitting SBP
- **PDF validation (soft)** — checks the downloaded PDF's first page for today's date; logs a warning but still sends if not found (SBP's internal date formatting isn't fully consistent)
- **In-memory only** — the PDF is downloaded into memory (`io.BytesIO`) and never written to disk; nothing is retained after the run ends

## Known Limitations

Being upfront about gaps rather than describing features that don't exist:

- **No duplicate-send protection.** There's no `state.json` or equivalent tracking what's already been emailed. Safety currently depends entirely on the scheduled cron firing once per day. If the workflow is triggered twice in the same day (e.g. a manual run after a successful scheduled run), it **will** send a duplicate email.
- **No persistent logs.** Logging goes to stdout only, visible in each run's GitHub Actions console — there's no rotating log file, since there's no persistent disk between runs.
- **No PDF archive.** Since files are handled in memory, there's no historical record of downloaded PDFs kept anywhere.
- **Schedule timing is provisional.** The current cron (`37 10 * * 1-5`, i.e. 3:37 PM PKT) and the 7 PM PKT cutoff (`CUTOFF_HOUR` in `main.py`) were carried over from an earlier version of this pipeline built for a different SBP report (Weighted Average Customer Exchange Rates), which published on a different schedule. KIBOR's actual publish window has not yet been confirmed — see `sniffer.py` below.

## Prerequisites

- **Python 3.9+** (for local testing only — the live pipeline runs on GitHub's runners, which use 3.11)
- A Gmail account with an **App Password** (or any SMTP server)
- A GitHub repository with **Actions enabled** and **write permissions** granted (Settings → Actions → General → Workflow permissions → "Read and write")

## Local Setup (for testing before pushing)

### 1. Install dependencies
```bash
pip install -r requirements.txt
```
Installs: `requests`, `beautifulsoup4`, `pytz`, `python-dotenv`, `pdfplumber`

### 2. Create a `.env` file in the repo root
```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASSWORD=your16charapppassword
EMAIL_FROM=you@gmail.com
EMAIL_TO=recipient@example.com
ADMIN_EMAIL=you@gmail.com
```
`.env` is gitignored — it should never be committed. `EMAIL_TO` accepts a comma-separated list for multiple recipients. `ADMIN_EMAIL` is optional; if omitted, failure alerts go to the first `EMAIL_TO` address.

**Gmail App Password setup:**
1. Enable 2-Step Verification: https://myaccount.google.com/security
2. Generate an App Password: https://myaccount.google.com/apppasswords
3. Use the 16-character result as `SMTP_PASSWORD` — not your regular Gmail password

### 3. Load the `.env` and run a no-email test

**Windows PowerShell:**
```powershell
Get-Content .env | ForEach-Object {
    if ($_ -and $_ -notmatch '^\s*#') {
        $parts = $_ -split '=', 2
        [System.Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim(), 'Process')
    }
}
python test_pipeline.py
```

**Linux / Mac:**
```bash
export $(grep -v '^#' .env | xargs)
python test_pipeline.py
```

`test_pipeline.py` fetches and validates against the live SBP API but sends **no email** — safe to run repeatedly. To test the actual email send, run `python main.py` instead (this will send a real email if a matching PDF is found — use a test recipient first).

## Deploying to GitHub Actions

### 1. Push to your repo
```bash
git add .
git commit -m "Deploy KIBOR pipeline"
git push
```
Confirm `.env` is **not** in the commit (`git status` before committing).

### 2. Set repository secrets
**Settings → Secrets and variables → Actions → New repository secret**, add each of:
`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_FROM`, `EMAIL_TO`, `ADMIN_EMAIL`

### 3. Enable write permissions (needed for the sniffer workflow's commit-back step)
**Settings → Actions → General → Workflow permissions → "Read and write permissions"**

### 4. Trigger manually to confirm it works
**Actions tab → SBP Exchange Rate Daily Pipeline → Run workflow**

(Workflow's internal `name:` field still says "SBP Exchange Rate Daily Pipeline" — cosmetic leftover from the original FX-rate version, safe to rename in the `.yml` file whenever convenient.)

## Determining the real publish window — `sniffer.py`

Since KIBOR's actual SBP publish time isn't confirmed yet, a separate lightweight workflow (`.github/workflows/kibor_sniffer.yml`) runs `sniffer.py` every 15 minutes, 8 AM–7 PM PKT, weekdays. It checks (without downloading or emailing anything) whether today's file has appeared, and on first sighting each day, commits a timestamped row to `sighting_log.csv` in the repo — the only way to persist a finding across ephemeral runs.

Once several days of data accumulate in `sighting_log.csv`, use it to:
- Move the main pipeline's cron trigger earlier than the earliest observed publish time (with buffer)
- Tighten `CUTOFF_HOUR` in `main.py` from its current placeholder value down to something realistic

## Project Structure

```
automation/
├── main.py                          # Main pipeline (polls, downloads, emails)
├── sniffer.py                       # Diagnostic: logs first-seen publish time
├── test_pipeline.py                 # Manual fetch/validate test (no email sent)
├── test_email_only.py               # Manual email-send test using a known-good PDF
├── requirements.txt                 # Python dependencies
├── run.bat                          # Windows local-run wrapper (loads .env)
├── .gitignore                       # Excludes .env, __pycache__, etc.
├── .github/workflows/
│   ├── sbp_pipeline.yml             # Main scheduled pipeline
│   └── kibor_sniffer.yml            # Publish-time discovery workflow
└── sighting_log.csv                 # Auto-created by sniffer.py once a match is found
```

## Troubleshooting

| Problem | Likely Cause / Fix |
|---|---|
| `Missing required environment variables` | One of the 6 required vars isn't set — check GitHub Secrets (for Actions runs) or your local `.env` |
| `SMTP authentication failed` | Using a regular Gmail password instead of an App Password, or the App Password was revoked |
| "Not published yet" in logs | Normal during the day — actual KIBOR publish time isn't confirmed yet (see sniffer section above) |
| Workflow doesn't fire on schedule | GitHub disables scheduled workflows after 60 days of repo inactivity — push any commit to reactivate |
| Sniffer's `git push` step fails | Workflow permissions not set to "Read and write" — see setup step 3 above |
| Duplicate emails on the same day | Known limitation — no dedupe mechanism currently exists (see *Known Limitations*) |
| Connection error / timeout | SBP's server being slow — exponential backoff should handle transient cases automatically |

## License

MIT — Use freely.