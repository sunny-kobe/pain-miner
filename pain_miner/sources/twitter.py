"""X (Twitter) API v2 source — requires API key (Basic/$200/mo or pay-per-use)."""

import json
import re
import time
import urllib.request
import urllib.parse


X_SEARCH_URL = "https://api.x.com/2/tweets/search/recent"

# Search query templates — {topic} gets replaced
QUERY_TEMPLATES = [
    '"{topic}" (frustrating OR terrible OR hate OR broken)',
    '"{topic}" ("wish there was" OR "someone should build" OR "need a tool")',
    '"{topic}" (expensive OR overpriced OR "would pay")',
    '"{topic}" (alternative OR workaround OR "looking for")',
]


def _search_tweets(query, bearer_token, max_results=50, timeout=15):
    """Search recent tweets using X API v2."""
    params = urllib.parse.urlencode({
        "query": f"{query} -is:retweet lang:en",
        "max_results": min(max_results, 100),
        "tweet.fields": "created_at,public_metrics,author_id,conversation_id",
    })
    url = f"{X_SEARCH_URL}?{params}"

    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {bearer_token}",
            "User-Agent": "pain-miner/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return {"errors": [{"message": f"HTTP {e.code}: {body[:200]}"}]}
    except Exception as e:
        return {"errors": [{"message": str(e)}]}


def fetch_tweets(topic, cfg):
    """Fetch tweets related to a topic using X API v2 recent search.

    Requires at least Basic tier ($200/mo) or pay-per-use for search access.
    Free tier has NO search capability.
    """
    x_cfg = cfg["platforms"].get("twitter", {})
    bearer_token = x_cfg.get("bearer_token", "")
    if not bearer_token:
        print("  [X] No bearer token. Set X_BEARER_TOKEN env var.")
        return []

    delay = cfg["search"].get("query_delay_seconds", 1.0)  # X rate limits are stricter
    max_results = x_cfg.get("max_results_per_query", 50)

    queries = [t.format(topic=topic) for t in QUERY_TEMPLATES]
    all_tweets = {}

    for q in queries:
        result = _search_tweets(q, bearer_token, max_results=max_results)

        if result.get("errors"):
            msgs = [e.get("message", "unknown") for e in result["errors"]]
            print(f"  [X] ✗ query failed → {'; '.join(msgs)[:100]}")
            continue

        tweets = result.get("data", [])
        meta = result.get("meta", {})
        total = meta.get("result_count", len(tweets))

        matched = 0
        for t in tweets:
            tid = t["id"]
            if tid in all_tweets:
                continue

            metrics = t.get("public_metrics", {})
            matched += 1
            all_tweets[tid] = {
                "id": f"x_{tid}",
                "platform": "twitter",
                "url": f"https://x.com/i/status/{tid}",
                "title": "",
                "body": t.get("text", ""),
                "author": t.get("author_id", ""),
                "community": "twitter",
                "points": metrics.get("like_count", 0) + metrics.get("retweet_count", 0),
                "num_comments": metrics.get("reply_count", 0),
                "created_at": t.get("created_at", ""),
                "topic": topic,
                "matched_queries": [q],
            }

        print(f"  [X] ✓ '{q[:60]}...' → {total} results, {matched} new")
        time.sleep(delay)

    return list(all_tweets.values())
