"""pain-miner CLI — discover user pain points from HN, Reddit, Product Hunt, and X."""

import argparse
import hashlib
import json
import sys

from . import config as config_mod
from . import db
from . import scoring
from . import analyzer
from . import reporter
from .sources import hn, reddit
from .sources import producthunt as ph
from .sources import twitter as x


def cmd_search(args, cfg):
    """Search platforms for pain points about a topic."""
    topic = args.topic
    platforms = [p.strip() for p in args.platforms.split(",")]
    no_analyze = args.no_analyze
    subreddits = [s.strip() for s in args.subreddits.split(",")] if args.subreddits else None

    print(f"\n{'=' * 60}")
    print(f"  pain-miner search: \"{topic}\"")
    print(f"  platforms: {', '.join(platforms)}")
    print(f"{'=' * 60}\n")

    db.init_db()
    all_posts = []

    # Phase 1: Fetch
    if "hn" in platforms and cfg["platforms"]["hn"].get("enabled", True):
        print("📡 Fetching HN comments...")
        comments = hn.fetch_comments(topic, cfg)
        print(f"   {len(comments)} unique comments\n")

        print("📡 Fetching HN stories...")
        stories = hn.fetch_stories(topic, cfg)
        print(f"   {len(stories)} unique stories\n")

        all_posts.extend(comments)
        all_posts.extend(stories)

    if "reddit" in platforms and cfg["platforms"]["reddit"].get("enabled", True):
        print("📡 Fetching Reddit posts...")
        posts = reddit.fetch_posts(topic, cfg, subreddits=subreddits)
        print(f"   {len(posts)} unique posts\n")
        all_posts.extend(posts)

    if "producthunt" in platforms and cfg["platforms"].get("producthunt", {}).get("enabled", True):
        print("📡 Fetching Product Hunt posts...")
        ph_posts = ph.fetch_posts(topic, cfg)
        print(f"   {len(ph_posts)} unique posts\n")
        all_posts.extend(ph_posts)

    if "twitter" in platforms and cfg["platforms"].get("twitter", {}).get("enabled", True):
        print("📡 Fetching X/Twitter posts...")
        tweets = x.fetch_tweets(topic, cfg)
        print(f"   {len(tweets)} unique tweets\n")
        all_posts.extend(tweets)

    if not all_posts:
        print("No posts found. Check your query or platform config.")
        return

    # Phase 2: Dedup against history
    new_posts = []
    for p in all_posts:
        if not db.is_processed(p["id"], p["platform"]):
            new_posts.append(p)

    print(f"📊 Collected {len(all_posts)} total, {len(new_posts)} new (after dedup)\n")

    # Phase 3: Score
    print("🧮 Scoring posts...")
    scored = scoring.score_posts(new_posts, cfg, topic=topic)

    min_score = cfg["scoring"].get("min_score_for_analysis", 10)
    above_threshold = sum(1 for p in scored if p["relevance_score"] >= min_score)
    print(f"   {above_threshold} posts above analysis threshold ({min_score})\n")

    # Phase 4: Persist
    db.insert_posts(scored)
    db.mark_history([p["id"] for p in scored], "mixed")

    # Phase 5: Analyze with Gemini (optional)
    pain_points = []
    analyzed_count = 0
    if not no_analyze:
        max_analyze = cfg["gemini"].get("max_posts_to_analyze", 50)
        to_analyze = [p for p in scored if p["relevance_score"] >= min_score][:max_analyze]

        if to_analyze and cfg["gemini"].get("api_key"):
            print(f"🤖 Running Gemini analysis on top {len(to_analyze)} posts...")
            pain_points = analyzer.analyze_posts(to_analyze, topic, cfg)
            analyzed_count = len(to_analyze)

            # Mark as analyzed in DB
            db.mark_analyzed(
                [p["id"] for p in to_analyze],
                [None] * len(to_analyze)  # Individual results stored in pain_points
            )
            print(f"   {len(pain_points)} pain points identified\n")
        elif not cfg["gemini"].get("api_key"):
            print("⚠️  No GEMINI_API_KEY set. Skipping analysis. Use --no-analyze to suppress this.\n")
        else:
            print("ℹ️  No posts above threshold for analysis.\n")

    # Phase 6: Generate report
    print("📝 Generating report...")
    report_path = reporter.generate_report(
        topic=topic,
        posts=scored,
        pain_points=pain_points,
        run_meta={"platforms": platforms, "analyzed_count": analyzed_count},
        cfg=cfg,
    )
    print(f"   Saved to: {report_path}\n")

    # Save run
    db.save_run(topic, ",".join(platforms), len(scored), analyzed_count, report_path)

    # Print summary
    print(f"{'=' * 60}")
    print(f"  Done! {len(scored)} posts scored, {analyzed_count} analyzed")
    print(f"  {len(pain_points)} pain points found")
    print(f"  Report: {report_path}")
    print(f"{'=' * 60}")


def cmd_analyze(args, cfg):
    """Run Gemini analysis on previously collected posts."""
    topic = args.topic
    db.init_db()

    min_score = cfg["scoring"].get("min_score_for_analysis", 10)
    max_analyze = cfg["gemini"].get("max_posts_to_analyze", 50)

    posts = db.get_top_posts(topic, limit=max_analyze, min_score=min_score)
    if not posts:
        print(f"No unanalyzed posts found for topic '{topic}'. Run search first.")
        return

    print(f"🤖 Analyzing {len(posts)} posts for topic '{topic}'...")
    pain_points = analyzer.analyze_posts(posts, topic, cfg)

    db.mark_analyzed([p["id"] for p in posts], [None] * len(posts))

    report_path = reporter.generate_report(
        topic=topic,
        posts=db.get_all_posts(topic),
        pain_points=pain_points,
        run_meta={},
        cfg=cfg,
    )

    print(f"\n📝 Report: {report_path}")
    print(f"   {len(pain_points)} pain points identified")


def cmd_report(args, cfg):
    """Show the latest report."""
    db.init_db()
    run = db.get_latest_run(topic=args.topic)
    if not run:
        print("No runs found. Run a search first.")
        return

    path = run.get("report_path", "")
    if path:
        try:
            with open(path) as f:
                print(f.read())
        except FileNotFoundError:
            print(f"Report file not found: {path}")
    else:
        print("No report path recorded for latest run.")


def cmd_import(args, cfg):
    """Import posts from a JSON file (e.g. Grok export) into the pipeline."""
    topic = args.topic
    platform = args.platform
    no_analyze = args.no_analyze

    try:
        with open(args.file, encoding="utf-8") as f:
            raw = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error reading {args.file}: {e}")
        return

    if not isinstance(raw, list):
        print("Expected a JSON array of post objects.")
        return

    print(f"\n{'=' * 60}")
    print(f"  pain-miner import: {args.file}")
    print(f"  topic: \"{topic}\" | platform: {platform}")
    print(f"  {len(raw)} posts in file")
    print(f"{'=' * 60}\n")

    db.init_db()

    # Normalize posts
    posts = []
    for i, item in enumerate(raw):
        post_id = item.get("id") or item.get("url") or f"import_{i}"
        # Generate stable ID from URL if available
        if not item.get("id") and item.get("url"):
            post_id = f"{platform}_{hashlib.md5(item['url'].encode()).hexdigest()[:12]}"

        posts.append({
            "id": post_id,
            "platform": platform,
            "url": item.get("url", ""),
            "title": item.get("title", item.get("body", "")[:80]),
            "body": item.get("body", ""),
            "author": item.get("author", ""),
            "community": item.get("community", ""),
            "points": item.get("points", item.get("likes", 0)),
            "num_comments": item.get("num_comments", item.get("replies", 0)),
            "created_at": item.get("created_at", item.get("date", "")),
            "topic": topic,
            "matched_queries": ["import"],
        })

    # Dedup
    new_posts = [p for p in posts if not db.is_processed(p["id"], p["platform"])]
    print(f"📊 {len(posts)} total, {len(new_posts)} new (after dedup)\n")

    if not new_posts:
        print("All posts already processed. Nothing to do.")
        return

    # Score
    print("🧮 Scoring posts...")
    scored = scoring.score_posts(new_posts, cfg, topic=topic)

    min_score = cfg["scoring"].get("min_score_for_analysis", 10)
    above_threshold = sum(1 for p in scored if p["relevance_score"] >= min_score)
    print(f"   {above_threshold} posts above analysis threshold ({min_score})\n")

    # Persist
    db.insert_posts(scored)
    db.mark_history([p["id"] for p in scored], platform)

    # Analyze
    pain_points = []
    analyzed_count = 0
    if not no_analyze:
        max_analyze = cfg["gemini"].get("max_posts_to_analyze", 50)
        to_analyze = [p for p in scored if p["relevance_score"] >= min_score][:max_analyze]

        if to_analyze and cfg["gemini"].get("api_key"):
            print(f"🤖 Running Gemini analysis on {len(to_analyze)} posts...")
            pain_points = analyzer.analyze_posts(to_analyze, topic, cfg)
            analyzed_count = len(to_analyze)
            db.mark_analyzed(
                [p["id"] for p in to_analyze],
                [None] * len(to_analyze)
            )
            print(f"   {len(pain_points)} pain points identified\n")
        elif not cfg["gemini"].get("api_key"):
            print("⚠️  No GEMINI_API_KEY set. Skipping analysis.\n")

    # Report
    print("📝 Generating report...")
    report_path = reporter.generate_report(
        topic=topic,
        posts=scored,
        pain_points=pain_points,
        run_meta={"platforms": [platform], "analyzed_count": analyzed_count},
        cfg=cfg,
    )
    print(f"   Saved to: {report_path}\n")

    db.save_run(topic, platform, len(scored), analyzed_count, report_path)

    print(f"{'=' * 60}")
    print(f"  Done! {len(scored)} posts imported, {analyzed_count} analyzed")
    print(f"  {len(pain_points)} pain points found")
    print(f"  Report: {report_path}")
    print(f"{'=' * 60}")


def main():
    parser = argparse.ArgumentParser(
        prog="pain-miner",
        description="Discover user pain points from HN and Reddit"
    )
    parser.add_argument("--config", default=None, help="Path to config.yaml")

    sub = parser.add_subparsers(dest="command")

    # search
    p_search = sub.add_parser("search", help="Search platforms for pain points")
    p_search.add_argument("topic", help='Topic to search (e.g. "AI video tools")')
    p_search.add_argument("--platforms", default="hn,producthunt", help="Comma-separated: hn,reddit,producthunt,twitter")
    p_search.add_argument("--subreddits", default=None, help="Override default subreddits")
    p_search.add_argument("--no-analyze", action="store_true", help="Skip Gemini analysis")

    # analyze
    p_analyze = sub.add_parser("analyze", help="Run Gemini on collected posts")
    p_analyze.add_argument("--topic", required=True, help="Topic to analyze")

    # report
    p_report = sub.add_parser("report", help="Show latest report")
    p_report.add_argument("--topic", default=None, help="Filter by topic")

    # import
    p_import = sub.add_parser("import", help="Import posts from JSON file (e.g. Grok export)")
    p_import.add_argument("file", help="Path to JSON file with posts array")
    p_import.add_argument("--topic", required=True, help="Topic for scoring and analysis")
    p_import.add_argument("--platform", default="x", help="Platform label (default: x)")
    p_import.add_argument("--no-analyze", action="store_true", help="Skip Gemini analysis")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    cfg = config_mod.load_config(args.config)

    if args.command == "search":
        cmd_search(args, cfg)
    elif args.command == "analyze":
        cmd_analyze(args, cfg)
    elif args.command == "report":
        cmd_report(args, cfg)
    elif args.command == "import":
        cmd_import(args, cfg)


if __name__ == "__main__":
    main()
