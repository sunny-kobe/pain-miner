# pain-miner

**Find what to build next.** Mine real user frustrations from Hacker News, Reddit, and Product Hunt — before your competitors do.

pain-miner scans thousands of community discussions to surface genuine pain points, unmet needs, and product opportunities. No surveys, no guessing — just real people complaining about real problems.

```
$ python -m pain_miner search "API testing" --platforms hn,reddit,producthunt

📡 Fetching HN comments...     311 unique comments
📡 Fetching HN stories...      106 unique stories
📡 Fetching Reddit posts...      3 unique posts
📡 Fetching Product Hunt...     19 unique posts
🧮 Scoring posts...             14 above threshold
🤖 Running Gemini analysis...    5 pain points found

Report: output/2026-03-02-api-testing.md
```

## Why pain-miner?

| Traditional approach | pain-miner |
|---|---|
| Read hundreds of threads manually | Searches 4 platforms in parallel |
| Gut feeling about what's painful | Rule-based scoring + LLM analysis |
| Single-source bias | Cross-platform signal detection |
| No way to verify patterns | Every pain point links to source URLs |
| Hours of research | Minutes to actionable insights |

## Features

- **Multi-platform search** — Hacker News (Algolia API), Reddit (.json endpoint, no API key needed), Product Hunt (GraphQL), X/Twitter (via Grok import)
- **Smart scoring** — Pain word detection, demand signals, engagement metrics, topic relevance filtering
- **Cross-platform signal detection** — Pain points appearing on multiple platforms are flagged and prioritized
- **Jaccard deduplication** — Intelligently merges similar pain points across batches, preserving all source URLs and quotes
- **Gemini-powered analysis** — Optional deep analysis using Google Gemini to extract structured pain points with emotional intensity, payment signals, and workarounds
- **Confidence-ranked reports** — Markdown output with High/Medium/Low confidence tiers, cross-platform badges, and direct links to original discussions

## Quick Start

```bash
git clone https://github.com/sunny-kobe/pain-miner.git
cd pain-miner
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

**Zero API keys needed** for HN + Reddit search. Add a Gemini key for AI-powered analysis:

```bash
echo "GEMINI_API_KEY=your_key_here" > .env
```

## Usage

```bash
# Search HN + Reddit (no API keys needed)
python -m pain_miner search "developer tools" --platforms hn,reddit

# Full pipeline: HN + Reddit + Product Hunt + Gemini analysis
python -m pain_miner search "CI/CD" --platforms hn,reddit,producthunt

# Quick scan without LLM analysis (rule-based scoring only)
python -m pain_miner search "API testing" --platforms hn,reddit --no-analyze

# Import X/Twitter data collected via Grok
python -m pain_miner import x_posts.json --topic "API testing"

# Re-analyze previously collected posts
python -m pain_miner analyze --topic "API testing"
```

## How It Works

```
Search queries (4 pain-signal templates per platform)
        │
        ▼
┌──────────────────────────────────────────┐
│  Fetch: HN Algolia + Reddit .json + PH  │
└──────────────┬───────────────────────────┘
               ▼
┌──────────────────────────────────────────┐
│  Dedup: SQLite tracks processed posts    │
└──────────────┬───────────────────────────┘
               ▼
┌──────────────────────────────────────────┐
│  Score: pain words + demand signals +    │
│         engagement + topic relevance     │
└──────────────┬───────────────────────────┘
               ▼
┌──────────────────────────────────────────┐
│  Analyze: Gemini extracts structured     │
│           pain points from top posts     │
└──────────────┬───────────────────────────┘
               ▼
┌──────────────────────────────────────────┐
│  Aggregate: Jaccard dedup + cross-       │
│             platform signal detection    │
└──────────────┬───────────────────────────┘
               ▼
┌──────────────────────────────────────────┐
│  Report: Markdown with confidence tiers  │
└──────────────────────────────────────────┘
```

## Sample Output

```markdown
## Search Transparency
| Metric | Value |
|--------|-------|
| Total posts collected | 439 |
| HN posts | 417 |
| Reddit posts | 3 |
| Product Hunt posts | 19 |
| Cross-platform pain points | 1 |

## High Confidence Pain Points

### 1. API testing tools lack Git-based collaboration workflows
- **Category**: workflow_friction
- **Emotional intensity**: 4/5
- **Payment signal**: No
- **Cross-platform**: ⚡ Moderate (hn, reddit)
- **Sources**: [link](https://reddit.com/...), [link](https://news.ycombinator.com/...)

### 2. Postman pricing too expensive for early-stage teams
- **Category**: pricing
- **Emotional intensity**: 5/5
- **Payment signal**: Yes — "can't justify $20/month per developer"
```

## Data Sources

| Source | Auth Required | Status |
|--------|:---:|:---:|
| Hacker News | None | ✅ |
| Reddit | None | ✅ |
| Product Hunt | API token | ✅ |
| X/Twitter | Grok (manual) | ✅ via import |

## Configuration

Edit `config.yaml` to customize subreddits, scoring weights, Gemini model, etc. API keys go in `.env`:

```bash
GEMINI_API_KEY=your_gemini_key        # Required for AI analysis
PRODUCTHUNT_TOKEN=your_ph_token       # Optional, for Product Hunt
```

## Use Cases

- **Indie hackers** — Find validated product ideas backed by real user complaints
- **Product managers** — Discover feature gaps and competitive opportunities
- **Founders** — Validate problem-solution fit before writing code
- **Developers** — Find open-source project ideas with real demand

## License

MIT
