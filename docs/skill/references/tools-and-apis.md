# Tools & APIs for Pain Point Discovery

## Quick Start 路径（推荐顺序）

不依赖任何 API 注册，立即可用：

```
1. pain-miner CLI (HN + Product Hunt) → 结构化数据，本地运行
2. HN Algolia API → 无需 key，直接 HTTP 请求
3. G2/Capterra WebSearch → site: 搜索差评
4. Reddit .json 端点 → 无需 API key 的结构化数据
5. Grok → 搜索 X/Twitter 帖子（补充渠道）
```

---

## Tier 0: pain-miner CLI（首选本地工具）

用户自己的项目，GitHub: [sunny-kobe/pain-miner](https://github.com/sunny-kobe/pain-miner)

### 状态（截至 2026-02）
- ✅ Hacker News — 可用（Algolia API）
- ✅ Product Hunt — 可用
- ⏳ Reddit — 代码就绪，需 API 审批（见下文 Reddit 部分）
- ⏳ X/Twitter — 代码就绪，需 API access

### 常用命令

```bash
cd ~/code/pain-miner

# HN 搜索
npx ts-node src/cli.ts search --platform hackernews --query "API documentation frustrating" --days 30

# Product Hunt 搜索
npx ts-node src/cli.ts search --platform producthunt --query "developer tools" --days 30

# 多平台搜索
npx ts-node src/cli.ts search --platform hackernews,producthunt --query "CI/CD slow" --days 60
```

### 输出格式
pain-miner 输出包含标题、链接、日期、得分（如 HN points），可直接用于 SKILL.md Step 4 分类。

---

## Tier 1: 免费 / 无需注册

### Hacker News — Algolia API

无需 API key，直接 HTTP 请求。

```bash
# 按相关性搜索
curl "http://hn.algolia.com/api/v1/search?query=frustrating+API&tags=story&hitsPerPage=50"

# 按时间搜索（最近 30 天）
curl "http://hn.algolia.com/api/v1/search_by_date?query=wish+there+was&tags=comment&numericFilters=created_at_i>$(date -d '30 days ago' +%s)"

# 高分帖子（>50 points）
curl "http://hn.algolia.com/api/v1/search?query=developer+tools&tags=story&numericFilters=points>50"
```

**返回字段**: `title`, `url`, `points`, `num_comments`, `created_at`, `author`

### Reddit — .json 端点（推荐替代方案）

> ⚠️ **Reddit API 现状（2025-11 起）**: 自助注册已停止，需预审批。个人项目多被拒。
> 推荐使用 .json 端点作为主要数据获取方式。

在任何 Reddit 页面 URL 末尾加 `.json` 即可获取结构化 JSON 数据：

```bash
# 搜索子版块
curl "https://www.reddit.com/r/webdev/search.json?q=frustrating+tool&sort=relevance&t=year&limit=100" \
  -H "User-Agent: pain-research/1.0"

# 获取热门帖子
curl "https://www.reddit.com/r/SaaS/hot.json?limit=50" \
  -H "User-Agent: pain-research/1.0"

# 获取帖子评论
curl "https://www.reddit.com/r/webdev/comments/POST_ID.json" \
  -H "User-Agent: pain-research/1.0"
```

**注意事项**:
- 必须设置 `User-Agent` header，否则会被 429
- 速率限制约 60 请求/分钟（比官方 API 松）
- 返回的 JSON 结构与官方 API 基本一致
- 无需注册、无需 OAuth、无需审批

**Python 示例**:
```python
import requests
import time

def search_reddit(subreddit, query, sort="relevance", time_filter="year", limit=100):
    url = f"https://www.reddit.com/r/{subreddit}/search.json"
    params = {"q": query, "sort": sort, "t": time_filter, "limit": limit, "restrict_sr": "on"}
    headers = {"User-Agent": "pain-research/1.0"}
    resp = requests.get(url, params=params, headers=headers)
    resp.raise_for_status()
    time.sleep(1.5)  # 尊重速率限制
    data = resp.json()
    posts = []
    for child in data.get("data", {}).get("children", []):
        p = child["data"]
        posts.append({
            "title": p["title"],
            "score": p["score"],
            "num_comments": p["num_comments"],
            "url": f"https://reddit.com{p['permalink']}",
            "created": p["created_utc"],
            "selftext": p.get("selftext", "")[:500]
        })
    return posts
```

### Reddit — PRAW（如已有 credential）

> 仅适用于已有 Reddit API credential 的情况。新注册基本不批。

```python
import praw

reddit = praw.Reddit(
    client_id="YOUR_ID",
    client_secret="YOUR_SECRET",
    user_agent="pain-research/1.0"
)

for submission in reddit.subreddit("webdev+SaaS+startups").search("frustrating OR broken OR wish", time_filter="month", limit=200):
    print(f"[{submission.score}] {submission.title} — {submission.num_comments} comments")
```

### Reddit — YARS（替代工具）

[YARS](https://github.com/praw-dev/yars) — Yet Another Reddit Scraper，不依赖官方 API。
适合批量抓取，但需注意 Reddit ToS 合规性。

---

## Tier 1.5: WebSearch 结构化查询（G2 / Capterra / App Store）

这些平台没有公开 API，但通过 WebSearch 的 `site:` 查询可以高效提取信息。

> **⚠️ Fallback 提示**: `site:` 查询在 WebSearch 中偶尔失效（返回 0 结果）。遇到时去掉 `site:` 前缀改用泛搜，如 `g2 "[产品]" cons review`。

### G2 差评挖掘

G2 拥有 200 万+ 软件评价，差评的 "Cons" 栏 = 结构化的产品需求文档。

```
# 查找某产品差评
site:g2.com "[产品名]" cons OR "missing feature" OR "wish it had"

# 查找某品类低评分产品
site:g2.com "[品类]" "2 out of 5" OR "3 out of 5"

# 查找迁移/替代需求
site:g2.com "[产品名]" "switched to" OR "migrated from" OR "looking for alternative"
```

### Capterra 差评挖掘

Capterra 用户偏中小企业，差评视角与 G2 互补。

```
# 查找某产品差评
site:capterra.com "[产品名]" cons OR "disappointed" OR "not worth"

# 按品类查找
site:capterra.com "[品类]" reviews "1 out of 5" OR "2 out of 5"
```

### Apify 批量抓取（付费，~$8/1K 条评价）

如需大规模结构化数据：
- [G2 Reviews Scraper](https://apify.com/curious_coder/g2-reviews-scraper)
- [Capterra Reviews Scraper](https://apify.com/curious_coder/capterra-reviews-scraper)
- 输出 JSON，含 rating, pros, cons, reviewer info

### Advanced G2 Scraper（开源）

GitHub 上有多个开源 G2 scraper，搜索 `g2 scraper python` 可找到。
注意 G2 反爬较严格，建议配合代理使用。

### App Store 评价

Apple 提供 RSS feed 获取应用评价：

```
# Apple App Store 评价 RSS（JSON 格式）
https://itunes.apple.com/rss/customerreviews/id={APP_ID}/sortBy=mostRecent/json

# 示例：获取 Notion 的最新评价
https://itunes.apple.com/rss/customerreviews/id=973134470/sortBy=mostRecent/json
```

通过 WebSearch 找到 App ID：
```
site:apps.apple.com "[产品名]"
```

### Chrome Web Store 评价

Chrome 插件评价对"做什么浏览器插件"特别有价值：

```
# WebSearch 查找插件
site:chromewebstore.google.com "[功能关键词]"

# 找差评
site:chromewebstore.google.com "[插件名]" reviews
```

Chrome Web Store 没有公开评价 API，但可以用 Puppeteer/Playwright 抓取评价页面。

---

## Tier 2: 需要 API Key / 付费

### X/Twitter

**现状**: 免费 tier 极其有限（写入为主），读取需要 Basic plan ($100/mo)。

**替代方案**:
1. **Grok**（推荐）: 直接在 Grok 界面搜索 X 帖子，免费且无限制
2. **pain-miner X 模块**: 代码就绪，但需要 API access
3. **Apify X Scraper**: ~$49/mo，无需官方 API

**Grok 搜索提示**:
```
搜索最近30天关于 [产品/领域] 的抱怨帖子，特别是：
1. 直接 @ 产品官方账号的投诉
2. 包含 "broken", "not working", "please add", "why can't" 的帖子
3. 寻找替代品的帖子（"alternative to", "switching from"）
请列出帖子内容、点赞数、转发数、日期。
```

### Product Hunt API

```graphql
# Product Hunt GraphQL API
# 需要 API key: https://www.producthunt.com/v2/oauth/applications

query {
  posts(order: VOTES, postedAfter: "2026-01-01T00:00:00Z", topic: "developer-tools") {
    edges {
      node {
        name
        tagline
        votesCount
        commentsCount
        comments(first: 20) {
          edges {
            node {
              body
            }
          }
        }
      }
    }
  }
}
```

> 注: pain-miner 已集成 Product Hunt，优先使用 CLI。

---

## LLM 分析 Prompt Template

当你收集了大量原始数据后，用以下 prompt 让 LLM 批量分析：

```
你是产品需求分析师。以下是从 [平台] 收集的用户帖子/评价。

任务：
1. 识别重复出现的痛点模式（≥3次出现才算模式）
2. 区分"抱怨"和"付费需求信号"
3. 对每个痛点评估：频率、强度、付费意愿
4. 标注可能的 vocal minority（同一用户反复抱怨）
5. 建议可构建的解决方案类型

格式要求：
- 每个痛点一个条目
- 引用原始帖子作为证据
- 明确标注置信度和数据不足之处

原始数据：
---
[粘贴数据]
```

---

## n8n 自动化工作流（参考）

适合长期持续监控：

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│ Schedule     │────▶│ Multi-source │────▶│ AI Classify │
│ (Daily/Week) │     │ Fetch        │     │ & Score     │
└─────────────┘     └──────────────┘     └──────┬──────┘
                                                 │
                    ┌──────────────┐     ┌───────▼──────┐
                    │ Notify       │◀────│ Filter       │
                    │ (Slack/Email)│     │ (Score > X)  │
                    └──────────────┘     └──────────────┘

数据源节点：
1. HTTP Request → HN Algolia API
2. HTTP Request → Reddit .json 端点
3. HTTP Request → Apple RSS 评价 feed
4. pain-miner CLI (Execute Command node)
```

---

## 成本参考

| 工具 | 成本 | 适用场景 |
|------|------|----------|
| pain-miner CLI | 免费 | HN + PH 搜索 |
| HN Algolia API | 免费 | HN 深度搜索 |
| Reddit .json | 免费 | Reddit 搜索（无需 API） |
| WebSearch (G2/Capterra) | 免费 | 竞品差评挖掘 |
| Apple RSS feed | 免费 | App Store 评价 |
| Grok | 免费 | X/Twitter 搜索 |
| Apify G2 Scraper | ~$8/1K 条 | 批量评价抓取 |
| X API Basic | $100/mo | X 深度分析（通常不需要） |
