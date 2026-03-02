# pain-miner

**Find what to build next.** Mine real user frustrations from Hacker News, Reddit, and Product Hunt — before your competitors do.

**找到下一个值得做的产品。** 从 HN、Reddit、Product Hunt 挖掘真实用户痛点 —— 在竞争对手之前。

[English](#features) | [中文](#功能特性)

---

pain-miner scans thousands of community discussions to surface genuine pain points, unmet needs, and product opportunities. No surveys, no guessing — just real people complaining about real problems.

pain-miner 扫描数千条社区讨论，挖掘真实痛点、未满足需求和产品机会。不靠问卷，不靠猜测 —— 只看真人在真实场景下的抱怨。

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

---

# 中文文档

## 为什么用 pain-miner？

| 传统做法 | pain-miner |
|---|---|
| 手动翻阅几百个帖子 | 自动搜索 4 个平台 |
| 凭直觉判断哪些是痛点 | 规则评分 + LLM 智能分析 |
| 只看一个平台，容易偏颇 | 跨平台信号检测 |
| 无法验证痛点是否普遍 | 每个痛点附带原始链接 |
| 几小时的调研 | 几分钟出结果 |

## 功能特性

- **多平台搜索** — Hacker News（Algolia API）、Reddit（.json 端点，无需 API key）、Product Hunt（GraphQL）、X/Twitter（通过 Grok 导入）
- **智能评分** — 痛点关键词检测、需求信号、互动指标、主题相关性过滤
- **跨平台信号检测** — 在多个平台重复出现的痛点会被标记并优先排序
- **Jaccard 智能去重** — 跨批次合并相似痛点，保留所有来源链接和引用
- **Gemini 深度分析** — 可选的 AI 分析，提取结构化痛点（情绪强度、付费意愿、现有替代方案）
- **置信度分级报告** — Markdown 输出，按 High/Medium/Low 分级，附跨平台标记和原始讨论链接

## 快速开始

```bash
git clone https://github.com/sunny-kobe/pain-miner.git
cd pain-miner
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

搜索 HN + Reddit **不需要任何 API key**。如需 AI 分析，添加 Gemini key：

```bash
echo "GEMINI_API_KEY=你的key" > .env
```

## 使用方法

```bash
# 搜索 HN + Reddit（无需 API key）
python -m pain_miner search "开发者工具" --platforms hn,reddit

# 全平台搜索 + Gemini 分析
python -m pain_miner search "CI/CD" --platforms hn,reddit,producthunt

# 快速扫描，不用 LLM（仅规则评分）
python -m pain_miner search "API testing" --platforms hn,reddit --no-analyze

# 导入通过 Grok 收集的 X/Twitter 数据
python -m pain_miner import x_posts.json --topic "API testing"
```

## 适用人群

- **独立开发者** — 找到有真实用户抱怨支撑的产品创意
- **产品经理** — 发现功能缺口和竞争机会
- **创业者** — 在写代码之前验证问题是否真实存在
- **开发者** — 找到有真实需求的开源项目方向

## License

MIT
