# Pain Miner — Design Document

> Date: 2026-02-26

## Overview

CLI tool for systematic discovery of user pain points from HN and Reddit, with rule-based scoring and Gemini-powered deep analysis.

## Usage

```bash
pain-miner search "AI video tools" --platforms hn,reddit
pain-miner search "project management" --subreddits SaaS,startups --no-analyze
pain-miner analyze --topic "AI video tools"
pain-miner report --latest
```

## Architecture

```
pain_miner/
├── cli.py              — argparse CLI entry point
├── config.py           — YAML config loading + env var fallback
├── sources/
│   ├── hn.py           — HN Algolia API (free, no auth)
│   └── reddit.py       — Reddit PRAW
├── scoring.py          — Rule-based scoring (pain/demand/engagement)
├── analyzer.py         — Gemini API structured analysis
├── db.py               — SQLite persistence + dedup
└── reporter.py         — Markdown report generation
```

## Data Flow

```
CLI args + config.yaml
    │
    ▼
Sources (HN + Reddit) ──parallel──▶ raw posts + comments
    │
    ▼
Dedup (in-memory set → age filter → history table)
    │
    ▼
Rule Scoring (pain_words + demand_words + engagement)
    │
    ▼
SQLite storage
    │
    ▼
Gemini Analysis (top N only, structured JSON output)
    │
    ▼
Markdown Report → output/YYYY-MM-DD-{topic}.md
```

## Scoring System

Three-dimension rule-based scoring (no LLM cost):

- **engagement** (weight 0.3): points/upvotes from platform
- **pain_signal** (weight 0.3): count of pain keywords in text
- **demand_signal** (weight 0.25): count of demand keywords in text
- **cross_query** (weight 0.15): number of search queries that matched this post

Pain keywords: frustrat, hate, wish, terrible, awful, slow, expensive, broken, waste, painful, annoying, disappoint, unusable, buggy, workaround, hack, garbage, horrible, overpriced, scam, misleading

Demand keywords: pay for, would pay, need a tool, wish there was, someone should build, is there a, looking for, alternative to, shut up and take my money

Only posts scoring above `min_score_for_analysis` (default: 10) go to Gemini.

## Gemini Analysis

Model: gemini-2.0-flash (free tier sufficient for ≤50 posts per run)

Input: top N scored posts as JSON
Output: structured pain point classification with:
- description, category, emotional_intensity (1-5)
- payment_signal (bool + quote), current_workaround
- unique_users count, representative_quotes with URLs

## SQLite Schema

```sql
CREATE TABLE posts (
    id TEXT PRIMARY KEY,
    platform TEXT,           -- 'hn' or 'reddit'
    url TEXT,
    title TEXT,
    body TEXT,
    author TEXT,
    community TEXT,          -- subreddit or 'hn'
    points INTEGER DEFAULT 0,
    num_comments INTEGER DEFAULT 0,
    created_at TEXT,
    fetched_at TEXT,
    pain_score REAL DEFAULT 0,
    demand_score REAL DEFAULT 0,
    relevance_score REAL DEFAULT 0,
    matched_queries TEXT,    -- JSON array
    analyzed INTEGER DEFAULT 0,
    analysis_result TEXT     -- JSON from Gemini
);

CREATE TABLE history (
    id TEXT PRIMARY KEY,
    platform TEXT,
    processed_at TEXT
);

CREATE TABLE runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT,
    platforms TEXT,
    started_at TEXT,
    completed_at TEXT,
    posts_fetched INTEGER,
    posts_analyzed INTEGER,
    report_path TEXT
);
```

## Dedup Strategy (from Reddit_Scrapper)

1. In-memory set during fetch → skip seen IDs
2. Age filter → skip posts older than max_days (default 180)
3. History table → skip previously processed IDs

## Config (config.yaml)

```yaml
platforms:
  hn:
    enabled: true
    min_points: 2
    hits_per_query: 30
  reddit:
    enabled: true
    client_id: ""
    client_secret: ""
    user_agent: "pain-miner/1.0"
    default_subreddits: ["SaaS", "startups", "Entrepreneur", "webdev"]
    sort: "top"
    time_filter: "month"
    limit: 100

scoring:
  engagement_weight: 0.3
  pain_weight: 0.3
  demand_weight: 0.25
  cross_query_weight: 0.15
  min_score_for_analysis: 10

gemini:
  model: "gemini-2.0-flash"
  max_posts_to_analyze: 50

output:
  dir: "./output"
```

## Dependencies

- praw (Reddit API)
- google-generativeai (Gemini)
- pyyaml (config)
- Standard library only for HN, SQLite, argparse
