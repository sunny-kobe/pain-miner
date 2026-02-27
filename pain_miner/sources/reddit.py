"""Reddit source via PRAW."""

import time


QUERY_TEMPLATES = [
    '"{topic}" ("I wish" OR "is there a tool" OR "frustrating")',
    '"{topic}" ("I\'d pay for" OR "someone should build" OR "workaround")',
    '"{topic}" (complaint OR problem OR "waste of time")',
    '"{topic}" (alternative OR "looking for" OR disappointing)',
]


def _get_reddit(cfg):
    """Create PRAW Reddit instance from config."""
    try:
        import praw
    except ImportError:
        print("  [Reddit] praw not installed. Run: pip install praw")
        return None

    r_cfg = cfg["platforms"]["reddit"]
    if not r_cfg.get("client_id") or not r_cfg.get("client_secret"):
        print("  [Reddit] No API credentials. Set REDDIT_CLIENT_ID/REDDIT_CLIENT_SECRET env vars.")
        return None

    return praw.Reddit(
        client_id=r_cfg["client_id"],
        client_secret=r_cfg["client_secret"],
        user_agent=r_cfg.get("user_agent", "pain-miner/1.0"),
    )


def fetch_posts(topic, cfg, subreddits=None):
    """Search Reddit for pain-signal posts about a topic."""
    reddit = _get_reddit(cfg)
    if not reddit:
        return []

    r_cfg = cfg["platforms"]["reddit"]
    subs = subreddits or r_cfg.get("default_subreddits", ["SaaS", "startups"])
    sub_str = "+".join(subs)
    sort = r_cfg.get("sort", "top")
    time_filter = r_cfg.get("time_filter", "month")
    limit = r_cfg.get("limit", 100)
    delay = cfg["search"].get("query_delay_seconds", 0.3)

    queries = [t.format(topic=topic) for t in QUERY_TEMPLATES]
    all_posts = {}
    seen_ids = set()

    subreddit = reddit.subreddit(sub_str)

    for q in queries:
        try:
            results = subreddit.search(q, sort=sort, time_filter=time_filter, limit=limit)
            count = 0
            for post in results:
                if post.id in seen_ids:
                    continue
                seen_ids.add(post.id)

                body = post.selftext or ""
                # Also grab top comments for richer signal
                top_comments = []
                try:
                    post.comment_sort = "top"
                    post.comments.replace_more(limit=0)
                    for comment in post.comments[:5]:
                        top_comments.append(comment.body)
                except Exception:
                    pass

                full_body = body
                if top_comments:
                    full_body += "\n\n--- TOP COMMENTS ---\n" + "\n---\n".join(top_comments)

                all_posts[post.id] = {
                    "id": f"reddit_{post.id}",
                    "platform": "reddit",
                    "url": f"https://reddit.com{post.permalink}",
                    "title": post.title,
                    "body": full_body,
                    "author": str(post.author) if post.author else "[deleted]",
                    "community": post.subreddit.display_name,
                    "points": post.score,
                    "num_comments": post.num_comments,
                    "created_at": str(post.created_utc),
                    "topic": topic,
                    "matched_queries": [],
                }
                count += 1

            all_posts_for_query = {k: v for k, v in all_posts.items()
                                   if k in seen_ids}
            # Tag matched queries
            for pid in seen_ids:
                if pid in all_posts:
                    all_posts[pid]["matched_queries"].append(q)

            print(f"  [Reddit] ✓ '{q[:60]}...' → {count} new posts")

        except Exception as e:
            print(f"  [Reddit] ✗ '{q[:60]}...' → {e}")

        time.sleep(delay)

    return list(all_posts.values())
