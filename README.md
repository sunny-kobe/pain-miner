# pain-miner

Discover user pain points and unmet needs from Hacker News and Reddit.

pain-miner is a CLI tool that searches community discussions for posts expressing frustration, feature requests, or unmet needs around specific topics. It combines rule-based scoring with optional LLM analysis (Gemini) to surface actionable product opportunities.

## Features

- **HN Algolia API** — Search Hacker News comments and stories
- **Reddit (PRAW)** — Search Reddit posts and comments across subreddits
- **Rule-based scoring** — Pain words, demand signals, engagement metrics, topic relevance filtering
- **Gemini analysis** — Optional deep analysis using Google's Gemini 2.0 Flash
- **SQLite dedup** — Track processed posts across runs, avoid re-analyzing
- **Markdown reports** — Structured output with confidence-ranked pain points and source URLs

## Install

```bash
git clone https://github.com/sunny-kobe/pain-miner.git
cd pain-miner
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Copy and edit the config:

```bash
cp config.yaml config.yaml  # edit as needed
```

Set API keys via environment variables or `.env` file:

```bash
# .env
GEMINI_API_KEY=your_gemini_key
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
```

## Usage

```bash
# Search HN only (no API keys needed)
python -m pain_miner search "AI video tools" --platforms hn

# Search HN + Reddit
python -m pain_miner search "AI video tools" --platforms hn,reddit

# Skip Gemini analysis (rule-based scoring only)
python -m pain_miner search "AI video tools" --platforms hn --no-analyze

# Re-analyze previously collected posts
python -m pain_miner analyze --topic "AI video tools"

# View latest report
python -m pain_miner report --topic "AI video tools"
```

## How It Works

1. **Fetch** — Query HN Algolia API and/or Reddit PRAW with pain-signal search templates
2. **Dedup** — Skip posts already processed in previous runs (SQLite)
3. **Score** — Rule-based scoring: pain words + demand signals + topic relevance + engagement
4. **Analyze** — Send top-scored posts to Gemini for structured pain point extraction
5. **Report** — Generate Markdown report with confidence-ranked pain points and source URLs

## Output

Reports are saved to `output/` as Markdown files:

- **High/Medium/Low Confidence Pain Points** — with category, emotional intensity, payment signals, quotes, source URLs
- **High-Engagement Discussion Hubs** — most-discussed on-topic threads worth reading manually

## License

MIT
