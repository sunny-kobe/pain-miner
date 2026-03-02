"""Gemini-powered deep analysis of top-scored posts."""

import json


ANALYSIS_PROMPT = """Analyze these community posts about "{topic}" and extract user pain points.

For each distinct pain point (merge similar ones):
1. description: one-sentence summary
2. category: one of [missing_feature, pricing, workflow_friction, integration_need, quality_issue, learning_curve]
3. emotional_intensity: 1-5 (5 = extreme frustration)
4. payment_signal: true/false
5. payment_quote: exact quote if payment_signal is true, else null
6. current_workaround: how users solve it now (null if unknown)
7. unique_users: count of distinct users mentioning this
8. representative_quotes: array of max 3 quotes (include source URL)
9. source_urls: array of all source URLs

Rules:
- One person complaining repeatedly ≠ a pattern. Count UNIQUE users only.
- "I wish X existed" is stronger signal than "X is annoying"
- Workarounds involving 3+ tools or manual steps = high-value pain point
- Merge posts describing the same core frustration into one pain point
- Ignore meta-complaints about platforms themselves unless directly relevant

Output ONLY a JSON array of pain point objects. No other text.

Posts data:
{posts_json}"""


def analyze_posts(posts, topic, cfg):
    """Run Gemini analysis on a list of posts. Returns list of pain points."""
    try:
        from google import genai
    except ImportError:
        print("  [Gemini] google-genai not installed. Run: pip install google-genai")
        return []

    api_key = cfg["gemini"].get("api_key", "")
    if not api_key:
        print("  [Gemini] No API key. Set GEMINI_API_KEY env var.")
        return []

    client = genai.Client(api_key=api_key)
    model_name = cfg["gemini"].get("model", "gemini-2.0-flash")

    # Prepare posts data — only send essential fields to save tokens
    posts_data = []
    for p in posts:
        posts_data.append({
            "url": p.get("url", ""),
            "title": p.get("title", ""),
            "body": p.get("body", "")[:2000],  # Truncate long posts
            "author": p.get("author", ""),
            "points": p.get("points", 0),
            "platform": p.get("platform", ""),
            "community": p.get("community", ""),
            "pain_score": p.get("pain_score", 0),
            "demand_score": p.get("demand_score", 0),
        })

    # Split into batches if too many posts (Gemini context limit)
    batch_size = 25
    all_pain_points = []

    for i in range(0, len(posts_data), batch_size):
        batch = posts_data[i:i + batch_size]
        prompt = ANALYSIS_PROMPT.format(
            topic=topic,
            posts_json=json.dumps(batch, ensure_ascii=False, indent=2)
        )

        print(f"  [Gemini] Analyzing batch {i // batch_size + 1} ({len(batch)} posts)...")

        try:
            response = client.models.generate_content(model=model_name, contents=prompt)
            text = response.text.strip()

            # Strip markdown code fences if present
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

            pain_points = json.loads(text)
            if isinstance(pain_points, list):
                all_pain_points.extend(pain_points)
                print(f"  [Gemini] Found {len(pain_points)} pain points in batch")
            else:
                print(f"  [Gemini] Unexpected response format: {type(pain_points)}")

        except json.JSONDecodeError as e:
            print(f"  [Gemini] JSON parse error: {e}")
            print(f"  [Gemini] Raw response: {text[:500]}")
        except Exception as e:
            print(f"  [Gemini] API error: {e}")

    # Deduplicate pain points using Jaccard word-level similarity
    unique_points = _deduplicate_pain_points(all_pain_points)

    # Detect cross-platform signals
    _add_cross_platform_signals(unique_points)

    # Sort: cross-platform first, then unique_users, then emotional_intensity
    unique_points.sort(
        key=lambda x: (
            x.get("platform_count", 1),
            x.get("unique_users", 0),
            x.get("emotional_intensity", 0),
        ),
        reverse=True
    )

    return unique_points


def _jaccard_similarity(text_a, text_b):
    """Compute Jaccard similarity between two texts at word level."""
    words_a = set(text_a.lower().split())
    words_b = set(text_b.lower().split())
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


def _deduplicate_pain_points(pain_points, threshold=0.5):
    """Merge pain points with Jaccard similarity above threshold."""
    if not pain_points:
        return []

    clusters = []  # Each cluster is a list of pain points to merge

    for pp in pain_points:
        desc = pp.get("description", "")
        merged = False
        for cluster in clusters:
            representative = cluster[0]
            if _jaccard_similarity(desc, representative.get("description", "")) >= threshold:
                cluster.append(pp)
                merged = True
                break
        if not merged:
            clusters.append([pp])

    # Merge each cluster into a single pain point
    merged_points = []
    for cluster in clusters:
        if len(cluster) == 1:
            merged_points.append(cluster[0])
            continue

        # Use the first as base, merge data from the rest
        base = dict(cluster[0])
        all_urls = list(base.get("source_urls", []))
        all_quotes = list(base.get("representative_quotes", []))
        max_users = base.get("unique_users", 0)
        max_intensity = base.get("emotional_intensity", 0)
        has_payment = base.get("payment_signal", False)

        for other in cluster[1:]:
            all_urls.extend(other.get("source_urls", []))
            all_quotes.extend(other.get("representative_quotes", []))
            max_users = max(max_users, other.get("unique_users", 0))
            max_intensity = max(max_intensity, other.get("emotional_intensity", 0))
            if other.get("payment_signal"):
                has_payment = True
                if not base.get("payment_quote") and other.get("payment_quote"):
                    base["payment_quote"] = other["payment_quote"]

        base["source_urls"] = list(dict.fromkeys(all_urls))  # dedupe preserving order
        base["representative_quotes"] = all_quotes[:5]
        base["unique_users"] = max_users
        base["emotional_intensity"] = max_intensity
        base["payment_signal"] = has_payment
        merged_points.append(base)

    return merged_points


def _extract_platforms(source_urls):
    """Extract platform names from source URLs."""
    platforms = set()
    for url in source_urls:
        url_lower = url.lower()
        if "news.ycombinator.com" in url_lower or "hn_" in url_lower:
            platforms.add("hn")
        elif "reddit.com" in url_lower:
            platforms.add("reddit")
        elif "producthunt.com" in url_lower:
            platforms.add("producthunt")
        elif "twitter.com" in url_lower or "x.com" in url_lower:
            platforms.add("twitter")
        elif "g2.com" in url_lower:
            platforms.add("g2")
        elif "capterra.com" in url_lower:
            platforms.add("capterra")
    return platforms


def _add_cross_platform_signals(pain_points):
    """Add platform_count and cross_platform_signal to each pain point."""
    for pp in pain_points:
        urls = pp.get("source_urls", [])
        platforms = _extract_platforms(urls)
        pp["platforms"] = sorted(platforms) if platforms else []
        pp["platform_count"] = len(platforms) if platforms else 1
        if pp["platform_count"] >= 3:
            pp["cross_platform_signal"] = "strong"
        elif pp["platform_count"] == 2:
            pp["cross_platform_signal"] = "moderate"
        else:
            pp["cross_platform_signal"] = "single"
