# Market Brief

A daily portfolio brief posted to Discord before the US market opens.

Each run:

1. Reads your holdings from a Yahoo Finance portfolio export
2. Pulls fresh prices, previous closes and company-specific headlines from Yahoo
3. Has Gemini write a short summary of what moved and why
4. Compares your sector mix with the S&P 500 and suggests stocks to research
5. Renders the holdings and sector tables as one image, since Discord can't display Markdown tables
6. Posts one Markdown message with the image attached to a Discord channel through a webhook

Example post (the text, with a table image attached below it):

```
## 📈 Morning Brief · Tue Nov 24
> $8,521.95 · 🔴 -$265.06 (-3.02%) last session · 🟢 +$17.96 (+0.21%) total

Semis led a sharp tech selloff while defense and retail held up.
- NVDA -8.8% at a 13% weight is the main drag...

### ⚖️ Balance
- Tech at 44% vs 38% market while XLK fell 16.8% in a month...

### 💡 Ideas to research
- JPM · Fills the financials gap; largest US bank with diversified revenue.
```

The image has a **Holdings** table (price, day %, weight bar, gain since purchase) and a
**Sector Balance** table (your weight vs the market, an over/under bar, and the sector ETF's 1-month move).

---

## Setup

### Requirements

- Python 3.10+
- A Discord server and channel you control
- A free Gemini API key

### 1. Get the project and install dependencies

**Linux / macOS**
```bash
git clone <your-repo-url> market_brief
cd market_brief
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows (PowerShell)**
```powershell
git clone <your-repo-url> market_brief
cd market_brief
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass   # only if activation is blocked
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If script execution can't be enabled, skip activation and call the venv's Python directly:
`.venv\Scripts\python market_brief.py`.

### 2. Create a Discord webhook

1. In your server, open the channel's settings and go to **Integrations → Webhooks → New Webhook**.
2. Name it (e.g. "Market Brief Bot") and click **Copy Webhook URL**.

Treat the URL like a password. Anyone who has it can post to your channel.

### 3. Get a Gemini API key

1. Go to [aistudio.google.com/apikey](https://aistudio.google.com/apikey) and sign in with a personal Google account.
2. Click **Create API key**.
3. In AI Studio, check which Flash / Flash-Lite models are currently on the free tier. Model names change over time.

> Free-tier prompts may be used by Google to improve its products. The script sends Gemini
> only percent changes, portfolio weights and headlines, never dollar amounts or share counts.

### 4. Configure `.env`

```bash
cp .env.example .env
```

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `GEMINI_API_KEY` | yes | — | Gemini API key |
| `DISCORD_WEBHOOK` | yes | — | Discord webhook URL |
| `GEMINI_MODELS` | no | `gemini-3.5-flash-lite,gemini-3.1-flash-lite` | Models to try, in order. The rest are fallbacks |
| `HOLDINGS_FILE` | no | `portfolio.csv` | Portfolio export file name |
| `BENCHMARK` | no | `SPY` | Fund whose sector mix counts as "the market" |
| `RECOMMENDATIONS` | no | `1` | Set to `0` to turn off sector balance and ideas |
| `SUGGESTIONS` | no | `stocks` | Kind of ideas to suggest: `stocks`, `etfs` or `mixed` |

### 5. Add your portfolio

1. In Yahoo Finance, open your portfolio and choose **Export**.
2. Save the file in the project folder as `portfolio.csv`.

The parser reads only the `Symbol`, `Purchase Price` and `Quantity` columns. Other columns are ignored,
because their prices are frozen at export time. Lots of the same ticker are combined, with a weighted cost
basis. Rows with no quantity (watchlist-only symbols) are skipped. Comma- and tab-separated files both work.

**Re-export after every buy, sell or stock split.** Yahoo portfolio lots are entered by hand and don't always
adjust for splits, so check share counts against your brokerage after a split.

---

## Usage

```bash
python market_brief.py --dry-run   # print the text and save brief_card.png, post nothing
python market_brief.py             # build and post to Discord
```

Always try `--dry-run` first after changing anything.

### Schedule it (Linux server)

Run every weekday at 9:00 AM Eastern, 30 minutes before the open:

```bash
crontab -e
```

```
CRON_TZ=America/New_York
0 9 * * 1-5 cd /path/to/market_brief && .venv/bin/python market_brief.py >> brief.log 2>&1
```

`CRON_TZ` keeps the run at 9:00 Eastern through daylight-saving changes. Check `brief.log` if a brief
doesn't arrive.

> The script doesn't skip market holidays yet. On those days it posts the most recent session's data.

---

## Project structure

```
market_brief/
├── market_brief.py      # entry point: runs everything in order
├── config.py            # loads .env settings
├── portfolio.py         # parses the Yahoo portfolio export
├── market.py            # all Yahoo Finance calls: prices, headlines, sectors, momentum
├── ai.py                # Gemini calls: retries, model fallback, JSON mode
├── brief.py             # the daily "what moved and why" summary
├── recommendations.py   # sector balance vs market, ideas to research
├── render.py            # draws the holdings and sector tables as a PNG
├── notify.py            # composes the Discord message and uploads the image
├── requirements.txt
├── .env.example
└── .gitignore           # keeps .env and portfolio.csv out of git
```

### How the pieces work

- **Prices** come from Yahoo's quote fields (`regularMarketPrice` / `regularMarketPreviousClose`). These
  are split-aware. Daily history is used only as a fallback, because it can have gaps around corporate actions.
- **Headlines** are filtered to ones that mention the ticker or the company name (looked up from Yahoo),
  because Yahoo's per-ticker news often includes unrelated stories.
- **Sectors**: each stock gets its Yahoo sector. ETFs and funds are looked through to their underlying
  sector mix. The benchmark's sector mix is pulled live.
- **Sentiment** uses each SPDR sector ETF's 5-day and 1-month change (XLK, XLV, XLF, …).
- **Gemini** calls retry busy and rate-limit errors (5s, 15s, 45s), then move to the next model in
  `GEMINI_MODELS`. If every model fails, later calls in the same run skip straight to the fallback,
  and the brief still posts with the raw numbers.
- **Suggestions** are checked against Yahoo: tickers that don't exist, that you already own, or that aren't
  the configured type (e.g. an ETF when `SUGGESTIONS=stocks`) are dropped.
- **The table image** is drawn with matplotlib on a dark theme and saved as `brief_card.png` on each run.
  If rendering fails, the text still posts.

---

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `API key not valid` | Wrong or placeholder key in `.env`. The file always overrides terminal variables |
| `503 UNAVAILABLE` in the log | Gemini's free tier is busy. The script retries automatically. Linking billing (Google AI Pro includes monthly credits) moves you to the paid tier, which gets priority |
| `model not found` | Update `GEMINI_MODELS` to names AI Studio currently lists |
| `No price data from Yahoo: XYZ` | Run `python -c "import yfinance as yf; print(yf.Ticker('XYZ').history(period='5d'))"`. If it's empty, run `pip install -U yfinance` |
| Wrong daily % right after a split | Re-export the portfolio and confirm share counts match your brokerage |
| `running scripts is disabled` (Windows) | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`, or call `.venv\Scripts\python` directly |
| Nothing posts from cron | Check `brief.log`, and confirm the cron line uses the venv's Python and `cd`s into the project |

---

*This is a personal tool. The summaries and ideas are AI-generated from limited data and are not financial advice.*
