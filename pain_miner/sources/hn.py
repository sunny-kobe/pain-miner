"""HN Algolia API source — free, no auth required."""

import json
import html as html_lib
import re
import time
import urllib.request
import urllib.parse


# Signal word templates — {topic} gets replaced
COMMENT_QUERY_TEMPLATES = [
    "{topic} frustrating",
    "{topic} problem",
    "{topic} limitation",
    "{topic} workflow slow",
    "{topic} expensive",
    "{topic} inconsistent",
    "{topic} disappointing",
    "{topic} workaround",
    "wish {topic} could",
    "need {topic} tool",
    "{topic} alternative",
    "{topic} pain point",
]

STORY_QUERY_TEMPLATES = [
    "{topic}",
    "{topic} tool",
    "{topic} generation",
    "{topic} open source",
]


def _fetch(query, tags="comment", hits=30, points_min=0, timeout=10):
    params = urllib.parse.urlencode({
        "query": query,
        "tags": tags,
        "hitsPerPage": hits,
    })
    if points_min > 0:
        params += f"&numericFilters=points%3E{points_min}"

    url = f"https://hn.algolia.com/api/v1/search?{params}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "pain-miner/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"hits": [], "nbHits": 0, "error": str(e)}


def _clean_html(text):
    if not text:
        return ""
    text = html_lib.unescape(text)
    text = re.sub(r'<p>', '\n', text)
    text = re.sub(r'<[^>]+>', '', text)
    return text.strip()


def fetch_comments(topic, cfg):
    """Fetch HN comments matching topic with pain/demand signal queries."""
    hn_cfg = cfg["platforms"]["hn"]
    delay = cfg["search"].get("query_delay_seconds", 0.3)
    hits_per = hn_cfg.get("hits_per_query", 30)

    queries = [t.format(topic=topic) for t in COMMENT_QUERY_TEMPLATES]
    all_posts = {}

    for q in queries:
        data = _fetch(q, tags="comment", hits=hits_per)
        if data.get("error"):
            print(f"  [HN] ✗ '{q}' → {data['error']}")
            continue

        fetched = len(data.get("hits", []))
        total = data.get("nbHits", 0)
        print(f"  [HN] ✓ '{q}' → {total} total, fetched {fetched}")

        for h in data["hits"]:
            oid = h["objectID"]
            if oid not in all_posts:
                all_posts[oid] = {
                    "id": f"hn_{oid}",
                    "platform": "hn",
                    "url": f"https://news.ycombinator.com/item?id={oid}",
                    "title": h.get("story_title", ""),
                    "body": _clean_html(h.get("comment_text", "")),
                    "author": h.get("author", ""),
                    "community": "hn",
                    "points": h.get("points") or 0,
                    "num_comments": 0,
                    "created_at": h.get("created_at", ""),
                    "topic": topic,
                    "matched_queries": [],
                }
            all_posts[oid]["matched_queries"].append(q)

        time.sleep(delay)

    return list(all_posts.values())


def fetch_stories(topic, cfg):
    """Fetch HN stories (top-level posts) for topic."""
    hn_cfg = cfg["platforms"]["hn"]
    delay = cfg["search"].get("query_delay_seconds", 0.3)
    hits_per = hn_cfg.get("hits_per_query", 30)
    min_pts = hn_cfg.get("min_points", 2)

    queries = [t.format(topic=topic) for t in STORY_QUERY_TEMPLATES]
    all_stories = {}

    for q in queries:
        data = _fetch(q, tags="story", hits=hits_per, points_min=min_pts)
        if data.get("error"):
            print(f"  [HN stories] ✗ '{q}' → {data['error']}")
            continue

        fetched = len(data.get("hits", []))
        print(f"  [HN stories] ✓ '{q}' → {data.get('nbHits', 0)} total, fetched {fetched}")

        for h in data["hits"]:
            oid = h["objectID"]
            if oid not in all_stories:
                all_stories[oid] = {
                    "id": f"hn_{oid}",
                    "platform": "hn",
                    "url": f"https://news.ycombinator.com/item?id={oid}",
                    "title": h.get("title", ""),
                    "body": "",
                    "author": h.get("author", ""),
                    "community": "hn",
                    "points": h.get("points") or 0,
                    "num_comments": h.get("num_comments") or 0,
                    "created_at": h.get("created_at", ""),
                    "topic": topic,
                    "matched_queries": [],
                }
            all_stories[oid]["matched_queries"].append(q)

        time.sleep(delay)

    return list(all_stories.values())
