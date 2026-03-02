"""Reddit source via .json endpoint — no API key required."""

import json
import time
import urllib.request
import urllib.parse


QUERY_TEMPLATES = [
    '"{topic}" ("I wish" OR "is there a tool" OR "frustrating")',
    '"{topic}" ("I\'d pay for" OR "someone should build" OR "workaround")',
    '"{topic}" (complaint OR problem OR "waste of time")',
    '"{topic}" (alternative OR "looking for" OR disappointing)',
]


def _fetch_json(url, params=None, user_agent="pain-miner/1.0", timeout=15):
    """Fetch JSON from a URL with retry on 429."""
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"

    max_retries = 3
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": user_agent})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < max_retries - 1:
                wait = 2 ** (attempt + 1)
                print(f"  [Reddit] Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            raise
        except Exception:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise
    return {}


def _fetch_comments(post_id, subreddit, user_agent="pain-miner/1.0", delay=1.5):
    """Fetch top 5 comments for a Reddit post via .json endpoint."""
    url = f"https://www.reddit.com/r/{subreddit}/comments/{post_id}.json"
    try:
        time.sleep(delay)
        data = _fetch_json(url, user_agent=user_agent)
        if not isinstance(data, list) or len(data) < 2:
            return []
        comments = []
        for child in data[1].get("data", {}).get("children", [])[:5]:
            if child.get("kind") != "t1":
                continue
            body = child.get("data", {}).get("body", "")
            if body and body != "[deleted]" and body != "[removed]":
                comments.append(body)
        return comments
    except Exception:
        return []


def fetch_posts(topic, cfg, subreddits=None):
    """Search Reddit for pain-signal posts about a topic via .json endpoint."""
    r_cfg = cfg["platforms"]["reddit"]
    subs = subreddits or r_cfg.get("default_subreddits", ["SaaS", "startups"])
    sub_str = "+".join(subs)
    sort = r_cfg.get("sort", "top")
    time_filter = r_cfg.get("time_filter", "month")
    limit = r_cfg.get("limit", 100)
    user_agent = r_cfg.get("user_agent", "pain-miner/1.0")
    comment_threshold = r_cfg.get("comment_threshold", 10)
    delay = max(cfg["search"].get("query_delay_seconds", 0.3), 1.5)

    queries = [t.format(topic=topic) for t in QUERY_TEMPLATES]
    all_posts = {}
    seen_ids = set()

    for q in queries:
        try:
            url = f"https://www.reddit.com/r/{sub_str}/search.json"
            params = {
                "q": q,
                "sort": sort,
                "t": time_filter,
                "limit": limit,
                "restrict_sr": "on",
            }
            data = _fetch_json(url, params=params, user_agent=user_agent)
            children = data.get("data", {}).get("children", [])

            count = 0
            for child in children:
                if child.get("kind") != "t3":
                    continue
                p = child["data"]
                post_id = p["id"]
                if post_id in seen_ids:
                    # Tag additional matched query
                    if post_id in all_posts:
                        all_posts[post_id]["matched_queries"].append(q)
                    continue
                seen_ids.add(post_id)

                body = p.get("selftext", "") or ""

                # Fetch top comments for high-engagement posts
                if p.get("num_comments", 0) >= comment_threshold:
                    subreddit = p.get("subreddit", sub_str.split("+")[0])
                    top_comments = _fetch_comments(post_id, subreddit,
                                                   user_agent=user_agent, delay=delay)
                    if top_comments:
                        body += "\n\n--- TOP COMMENTS ---\n" + "\n---\n".join(top_comments)

                all_posts[post_id] = {
                    "id": f"reddit_{post_id}",
                    "platform": "reddit",
                    "url": f"https://reddit.com{p['permalink']}",
                    "title": p.get("title", ""),
                    "body": body,
                    "author": p.get("author", "[deleted]"),
                    "community": p.get("subreddit", ""),
                    "points": p.get("score", 0),
                    "num_comments": p.get("num_comments", 0),
                    "created_at": str(p.get("created_utc", "")),
                    "topic": topic,
                    "matched_queries": [q],
                }
                count += 1

            print(f"  [Reddit] ✓ '{q[:60]}...' → {count} new posts")

        except Exception as e:
            print(f"  [Reddit] ✗ '{q[:60]}...' → {e}")

        time.sleep(delay)

    return list(all_posts.values())
