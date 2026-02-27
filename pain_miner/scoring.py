"""Rule-based scoring — no LLM cost, fast."""

import math
import re


PAIN_WORDS = [
    "frustrat", "hate", "wish", "terrible", "awful", "slow", "expensive",
    "inconsisten", "artifact", "broken", "waste", "painful", "annoying",
    "disappoint", "useless", "garbage", "horrible", "unusable", "buggy",
    "overpriced", "scam", "misleading", "workaround", "hack", "tedious",
    "clunky", "unreliable", "laggy", "crash", "glitch",
]

DEMAND_WORDS = [
    "pay for", "would pay", "need a tool", "wish there was",
    "someone should build", "is there a", "looking for",
    "alternative to", "shut up and take my money", "i'd pay",
    "take my money", "does anyone know", "am i the only one",
]


def _extract_topic_keywords(topic):
    """Extract core keywords AND phrases from the topic for relevance matching.

    "AI video tools" → keywords=["ai", "video", "tool"], phrases=["ai video", "video tool"]
    Phrase matches are much stronger signals than individual word matches.
    """
    stop_words = {
        "a", "an", "the", "and", "or", "for", "of", "to", "in", "on", "with",
        "is", "are", "was", "were", "be", "been", "being", "that", "this",
        "it", "its", "my", "your", "our", "their", "what", "how", "why",
    }
    raw_words = re.findall(r"[a-z0-9]+", topic.lower())
    words = [w for w in raw_words if w not in stop_words and len(w) >= 2]

    # Generate bigram phrases (consecutive word pairs)
    phrases = []
    for i in range(len(words) - 1):
        phrases.append(f"{words[i]} {words[i+1]}")

    # Also add simple plural/stem variants of words
    stems = set()
    for w in words:
        stems.add(w)
        if w.endswith("s") and len(w) > 3:
            stems.add(w[:-1])
        else:
            stems.add(w + "s")  # Also match plural form

    return {"words": words, "stems": stems, "phrases": phrases}


def _topic_relevance(text, topic_info):
    """Return a relevance multiplier (0.0 - 1.0).

    Phrase matches (e.g. "ai video") are strong signals.
    Individual word matches alone are weak — many off-topic posts
    contain generic words like "ai" or "video" in isolation.
    """
    if not topic_info:
        return 1.0

    phrases = topic_info["phrases"]
    stems = topic_info["stems"]

    # Check phrase matches first (strong signal)
    phrase_matches = sum(1 for p in phrases if p in text)
    if phrase_matches >= 1:
        # At least one bigram matched — likely on-topic
        return min(1.0, 0.6 + 0.2 * phrase_matches)

    # No phrase matches — check individual word matches (weak signal)
    word_matches = sum(1 for s in stems if s in text)
    total_words = len(topic_info["words"])

    if word_matches == 0:
        return 0.0  # Completely off-topic
    elif word_matches == 1 and total_words > 1:
        return 0.1  # Single generic word match — almost certainly off-topic
    elif word_matches >= total_words:
        # All words present but not as phrases — moderately relevant
        return 0.4
    else:
        return 0.15  # Partial word match, no phrases


def score_post(post, cfg, topic_info=None):
    """Compute pain_score, demand_score, relevance_score for a post."""
    weights = cfg["scoring"]

    text = (post.get("title", "") + " " + post.get("body", "")).lower()
    points = post.get("points", 0)
    n_queries = len(post.get("matched_queries", []))

    # Count signal words
    pain_count = sum(1 for w in PAIN_WORDS if w in text)
    demand_count = sum(1 for w in DEMAND_WORDS if w in text)

    # Normalize engagement: log scale, cap at 5
    engagement = min(math.log1p(points), 5) if points > 0 else 0

    # Text length bonus (longer = more detailed complaint, cap at 2)
    length_bonus = min(len(text) / 500, 2)

    # Topic relevance multiplier — penalize off-topic posts heavily
    topic_mult = _topic_relevance(text, topic_info) if topic_info else 1.0

    # Pain/demand signals dominate; engagement is secondary
    raw_score = (
        weights.get("pain_weight", 0.3) * pain_count * 8 +
        weights.get("demand_weight", 0.25) * demand_count * 15 +
        weights.get("cross_query_weight", 0.15) * n_queries * 4 +
        weights.get("engagement_weight", 0.3) * engagement * 2 +
        length_bonus
    )

    relevance = raw_score * topic_mult

    return {
        "pain_score": pain_count,
        "demand_score": demand_count,
        "relevance_score": round(relevance, 2),
        "topic_relevance": round(topic_mult, 2),
    }


def score_posts(posts, cfg, topic=""):
    """Score all posts, return them sorted by relevance."""
    topic_info = _extract_topic_keywords(topic) if topic else None
    for p in posts:
        scores = score_post(p, cfg, topic_info=topic_info)
        p.update(scores)

    posts.sort(key=lambda x: x["relevance_score"], reverse=True)
    return posts
