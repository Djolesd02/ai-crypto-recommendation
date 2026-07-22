# AI Crypto Recommendation

Local Python scanner that finds low-cap / memecoin opportunities (Solana + EVM),
scores them, filters scams via RugCheck, and publishes the top 10 to a static site.

> Not investment advice. Crypto is high-risk. You can lose everything.

## How it works
- `scanner/` runs locally every 15 minutes, writes `data.json`, and PUTs it to
  the `data` branch on GitHub.
- `site/` is a static page deployed on Vercel that reads `data.json` from the
  `data` branch and refreshes every 15 minutes.

## One-time setup

### 1. Create the `data` branch (holds data.json, separate from code)
```bash
git checkout --orphan data
git rm -rf .
echo '{"generated_at":0,"count":0,"coins":[]}' > data.json
git add data.json
git commit -m "chore: init data branch"
git push -u origin data
git checkout main
```

### 2. GitHub token
Create a fine-grained Personal Access Token with **Contents: Read and write**
on the `ai-crypto-recommendation` repo. Then:
```bash
cp .env.example .env
# edit .env and paste the token into GITHUB_TOKEN
```

### 3. Python environment
```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # Windows PowerShell
pip install -r requirements.txt
```

### 4. Deploy the site on Vercel
- Import the repo at vercel.com, deploy from the `main` branch.
- No build step; it serves the `site/` folder (see `vercel.json`).

## Run the scanner
```bash
.\.venv\Scripts\Activate.ps1
python -m scanner.main
```
Leave it running; it publishes fresh data every 15 minutes. When your computer
is off, the site shows the last published data with a "stale" indicator.

## Run tests
```bash
python -m pytest -v
```

## Tuning
Edit `scanner/config.py` — weights, filter thresholds, refresh interval, chains.
