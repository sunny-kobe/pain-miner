"""Product Hunt GraphQL API source — free, requires developer token."""

import json
import re
import time
import urllib.request
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse


PH_GRAPHQL_URL = "https://api.producthunt.com/v2/api/graphql"

# Topics to search when looking for a given subject
# PH has no keyword search — we fetch by topic + date, then filter client-side
TOPIC_SLUGS = {
    "ai": ["artificial-intelligence", "ai", "machine-learning"],
    "video": ["video", "video-editing", "video-streaming"],
    "design": ["design-tools", "web-design", "graphic-design"],
    "developer": ["developer-tools", "open-source", "github"],
    "nocode": ["no-code", "low-code"],
    "saas": ["saas", "productivity", "software-engineering"],
    "marketing": ["marketing", "seo", "social-media-marketing"],
}

# GraphQL query to fetch posts by topic
POSTS_QUERY = """
query($topic: String!, $cursor: String, $postedAfter: DateTime) {
  posts(
    topic: $topic
    after: $cursor
    postedAfter: $postedAfter
    order: VOTES
    first: 20
  ) {
    edges {
      node {
        id
        name
        tagline
        description
        url
        votesCount
        commentsCount
        createdAt
        website
        topics {
          edges {
            node {
              name
              slug
            }
          }
        }
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""

# GraphQL query to fetch comments for a specific post
COMMENTS_QUERY = """
query($postId: ID!, $cursor: String) {
  post(id: $postId) {
    comments(first: 10, after: $cursor, order: VOTES) {
      edges {
        node {
          id
          body
          votesCount
          createdAt
        }
      }
    }
  }
}
"""


def _clean_url(url):
    """Strip utm_* tracking parameters from a URL."""
    parsed = urlparse(url)
    params = parse_qs(parsed.query, keep_blank_values=True)
    cleaned = {k: v for k, v in params.items() if not k.startswith("utm_")}
    new_query = urlencode(cleaned, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


def _graphql_request(query, variables, token, timeout=15):
    """Execute a GraphQL request against Product Hunt API."""
    payload = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    req = urllib.request.Request(
        PH_GRAPHQL_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "pain-miner/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"errors": [{"message": str(e)}]}


def _guess_topic_slugs(topic):
    """Map a free-text topic to PH topic slugs.

    "AI video tools" → ["artificial-intelligence", "ai", "video", "video-editing"]
    """
    words = set(re.findall(r"[a-z]+", topic.lower()))
    slugs = set()

    for key, topic_list in TOPIC_SLUGS.items():
        if key in words:
            slugs.update(topic_list)

    # Always include general tech topics if nothing matched
    if not slugs:
        slugs.update(["tech", "artificial-intelligence", "developer-tools"])

    return list(slugs)


def _matches_topic(post_data, topic_keywords):
    """Check if a PH post is relevant to the search topic (client-side filter)."""
    text = (
        post_data.get("name", "") + " " +
        post_data.get("tagline", "") + " " +
        post_data.get("description", "")
    ).lower()

    # Check if any topic keyword appears
    return any(kw in text for kw in topic_keywords)


def fetch_posts(topic, cfg):
    """Fetch Product Hunt posts related to a topic.

    Since PH has no keyword search, we:
    1. Map the topic to PH topic slugs
    2. Fetch recent posts from those topics
    3. Filter client-side by keyword matching
    """
    ph_cfg = cfg["platforms"].get("producthunt", {})
    token = ph_cfg.get("developer_token", "")
    if not token:
        print("  [PH] No developer token. Set PRODUCTHUNT_TOKEN env var.")
        return []

    delay = cfg["search"].get("query_delay_seconds", 0.3)
    max_pages = ph_cfg.get("max_pages_per_topic", 3)
    days_back = cfg["search"].get("max_post_age_days", 180)

    # Calculate date cutoff
    from datetime import datetime, timedelta
    posted_after = (datetime.utcnow() - timedelta(days=days_back)).isoformat() + "Z"

    # Topic keywords for client-side filtering
    topic_keywords = [w.lower() for w in re.findall(r"[a-z]+", topic.lower()) if len(w) >= 2]

    # Map topic to PH slugs
    slugs = _guess_topic_slugs(topic)
    print(f"  [PH] Searching topic slugs: {', '.join(slugs)}")

    all_posts = {}

    for slug in slugs:
        cursor = None
        for page in range(max_pages):
            variables = {"topic": slug, "postedAfter": posted_after}
            if cursor:
                variables["cursor"] = cursor

            result = _graphql_request(POSTS_QUERY, variables, token)

            if result.get("errors"):
                msgs = [e.get("message", "unknown") for e in result["errors"]]
                print(f"  [PH] ✗ topic '{slug}' page {page+1} → {'; '.join(msgs)}")
                break

            posts_data = result.get("data", {}).get("posts", {})
            edges = posts_data.get("edges", [])

            if not edges:
                break

            matched = 0
            for edge in edges:
                node = edge["node"]
                ph_id = node["id"]

                if ph_id in all_posts:
                    continue

                # Client-side keyword filter
                if not _matches_topic(node, topic_keywords):
                    continue

                matched += 1
                topic_names = [
                    t["node"]["name"]
                    for t in node.get("topics", {}).get("edges", [])
                ]

                all_posts[ph_id] = {
                    "id": f"ph_{ph_id}",
                    "platform": "producthunt",
                    "url": _clean_url(node.get("url", "")),
                    "title": node.get("name", ""),
                    "body": (node.get("tagline", "") + "\n" + node.get("description", "")).strip(),
                    "author": "",  # PH redacted maker names
                    "community": ", ".join(topic_names[:3]),
                    "points": node.get("votesCount", 0),
                    "num_comments": node.get("commentsCount", 0),
                    "created_at": node.get("createdAt", ""),
                    "topic": topic,
                    "matched_queries": [slug],
                    "website": node.get("website", ""),
                }

            print(f"  [PH] ✓ topic '{slug}' page {page+1} → {len(edges)} posts, {matched} matched")

            page_info = posts_data.get("pageInfo", {})
            if not page_info.get("hasNextPage"):
                break
            cursor = page_info.get("endCursor")

            time.sleep(delay)

        time.sleep(delay)

    posts_list = list(all_posts.values())

    # Enrich high-engagement posts with top comments (pain signals hide in comments)
    min_comments = ph_cfg.get("min_comments_to_fetch", 10)
    enriched = 0
    for post in posts_list:
        if post["num_comments"] >= min_comments:
            comment_text = fetch_comments_for_post(post["id"], token)
            if comment_text:
                post["body"] += "\n\n--- User Comments ---\n" + comment_text
                enriched += 1
            time.sleep(delay)

    if enriched:
        print(f"  [PH] Enriched {enriched} posts with top comments")

    return posts_list


def fetch_comments_for_post(post_id, token, max_comments=10):
    """Fetch top comments for a specific PH post. Returns comment bodies joined."""
    # Strip the ph_ prefix if present
    raw_id = post_id.replace("ph_", "")

    result = _graphql_request(COMMENTS_QUERY, {"postId": raw_id}, token)

    if result.get("errors"):
        return ""

    comments = result.get("data", {}).get("post", {}).get("comments", {}).get("edges", [])
    bodies = [c["node"].get("body", "") for c in comments[:max_comments]]
    return "\n".join(bodies)
