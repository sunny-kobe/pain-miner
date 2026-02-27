"""Generate Markdown reports from analysis results."""

import json
from datetime import datetime
from pathlib import Path


def generate_report(topic, posts, pain_points, run_meta, cfg):
    """Generate a Markdown report and save to output dir."""
    out_dir = Path(cfg["output"]["dir"])
    out_dir.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now().strftime("%Y-%m-%d")
    slug = topic.lower().replace(" ", "-")[:40]
    filename = f"{date_str}-{slug}.md"
    filepath = out_dir / filename

    total_posts = len(posts)
    analyzed_posts = run_meta.get("analyzed_count", sum(1 for p in posts if p.get("analyzed")))
    hn_posts = sum(1 for p in posts if p.get("platform") == "hn")
    reddit_posts = sum(1 for p in posts if p.get("platform") == "reddit")
    ph_posts = sum(1 for p in posts if p.get("platform") == "producthunt")
    x_posts = sum(1 for p in posts if p.get("platform") == "twitter")

    lines = []
    lines.append(f"# Pain Point Research: {topic}")
    lines.append(f"> Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Tool: pain-miner\n")

    # Search transparency
    lines.append("## Search Transparency\n")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Total posts collected | {total_posts} |")
    lines.append(f"| HN posts | {hn_posts} |")
    lines.append(f"| Reddit posts | {reddit_posts} |")
    if ph_posts:
        lines.append(f"| Product Hunt posts | {ph_posts} |")
    if x_posts:
        lines.append(f"| X/Twitter posts | {x_posts} |")
    lines.append(f"| Posts sent to Gemini | {analyzed_posts} |")
    lines.append(f"| Pain points identified | {len(pain_points)} |")
    lines.append(f"| Data source level | **Primary** — all from original posts with URLs |")
    lines.append("")

    if not pain_points:
        lines.append("## Results\n")
        lines.append("No pain points identified by Gemini analysis.\n")
        lines.append("### Top Scored Posts (Rule-Based)\n")
        for i, p in enumerate(posts[:20], 1):
            lines.append(f"**{i}. [{p.get('title', 'Untitled')[:80]}]({p.get('url', '')})**")
            lines.append(f"- Platform: {p.get('platform')} | Points: {p.get('points', 0)} | "
                        f"Pain: {p.get('pain_score', 0)} | Demand: {p.get('demand_score', 0)} | "
                        f"Score: {p.get('relevance_score', 0)}")
            body_preview = p.get("body", "")[:200].replace("\n", " ")
            if body_preview:
                lines.append(f"- > {body_preview}...")
            lines.append("")
    else:
        # High confidence pain points
        high = [pp for pp in pain_points
                if pp.get("unique_users", 0) >= 3 or pp.get("emotional_intensity", 0) >= 4]
        medium = [pp for pp in pain_points
                  if pp not in high and (pp.get("unique_users", 0) >= 2 or pp.get("payment_signal"))]
        low = [pp for pp in pain_points if pp not in high and pp not in medium]

        if high:
            lines.append("## High Confidence Pain Points\n")
            for i, pp in enumerate(high, 1):
                _format_pain_point(lines, i, pp)

        if medium:
            lines.append("## Medium Confidence\n")
            for i, pp in enumerate(medium, 1):
                _format_pain_point(lines, i, pp)

        if low:
            lines.append("## Low Confidence / Emerging Signals\n")
            for i, pp in enumerate(low, 1):
                _format_pain_point(lines, i, pp)

    # Top stories / high-engagement posts (filtered by topic relevance)
    stories = [p for p in posts
               if p.get("num_comments", 0) > 10 and p.get("topic_relevance", 1.0) >= 0.4]
    stories.sort(key=lambda x: x.get("points", 0), reverse=True)
    if stories[:10]:
        lines.append("## High-Engagement Discussion Hubs\n")
        lines.append("These posts have the most discussion — worth reading manually:\n")
        for s in stories[:10]:
            lines.append(f"- [{s.get('title', 'Untitled')[:80]}]({s.get('url', '')}) "
                        f"— {s.get('points', 0)}↑ {s.get('num_comments', 0)}💬 "
                        f"({s.get('platform')})")
        lines.append("")

    content = "\n".join(lines)
    filepath.write_text(content, encoding="utf-8")
    return str(filepath)


def _format_pain_point(lines, index, pp):
    lines.append(f"### {index}. {pp.get('description', 'Unknown')}\n")
    lines.append(f"- **Category**: {pp.get('category', 'unknown')}")
    lines.append(f"- **Emotional intensity**: {pp.get('emotional_intensity', '?')}/5")
    lines.append(f"- **Unique users**: {pp.get('unique_users', '?')}")
    lines.append(f"- **Payment signal**: {'Yes' if pp.get('payment_signal') else 'No'}")
    if pp.get("payment_quote"):
        lines.append(f'  - > "{pp["payment_quote"]}"')
    if pp.get("current_workaround"):
        lines.append(f"- **Current workaround**: {pp['current_workaround']}")

    quotes = pp.get("representative_quotes", [])
    if quotes:
        lines.append("- **Quotes**:")
        for q in quotes[:3]:
            if isinstance(q, dict):
                lines.append(f'  - > "{q.get("text", q)}"')
            else:
                lines.append(f'  - > "{q}"')

    urls = pp.get("source_urls", [])
    if urls:
        lines.append("- **Sources**: " + ", ".join(f"[link]({u})" for u in urls[:5]))

    lines.append("")
