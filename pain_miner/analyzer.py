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

    # Deduplicate pain points by description similarity (simple approach)
    seen_descriptions = set()
    unique_points = []
    for pp in all_pain_points:
        desc_key = pp.get("description", "").lower()[:50]
        if desc_key not in seen_descriptions:
            seen_descriptions.add(desc_key)
            unique_points.append(pp)

    # Sort by unique_users desc, then emotional_intensity desc
    unique_points.sort(
        key=lambda x: (x.get("unique_users", 0), x.get("emotional_intensity", 0)),
        reverse=True
    )

    return unique_points
