"""SQLite persistence: posts, history (dedup), runs."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "pain_miner.db"


def _conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = _conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS posts (
            id TEXT PRIMARY KEY,
            platform TEXT,
            url TEXT,
            title TEXT,
            body TEXT,
            author TEXT,
            community TEXT,
            points INTEGER DEFAULT 0,
            num_comments INTEGER DEFAULT 0,
            created_at TEXT,
            fetched_at TEXT,
            topic TEXT,
            pain_score REAL DEFAULT 0,
            demand_score REAL DEFAULT 0,
            relevance_score REAL DEFAULT 0,
            matched_queries TEXT DEFAULT '[]',
            analyzed INTEGER DEFAULT 0,
            analysis_result TEXT
        );

        CREATE TABLE IF NOT EXISTS history (
            id TEXT,
            platform TEXT,
            processed_at TEXT,
            PRIMARY KEY (id, platform)
        );

        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT,
            platforms TEXT,
            started_at TEXT,
            completed_at TEXT,
            posts_fetched INTEGER DEFAULT 0,
            posts_analyzed INTEGER DEFAULT 0,
            report_path TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_posts_topic ON posts(topic);
        CREATE INDEX IF NOT EXISTS idx_posts_relevance ON posts(relevance_score);
        CREATE INDEX IF NOT EXISTS idx_posts_platform ON posts(platform);
    """)
    conn.commit()
    conn.close()


def is_processed(post_id, platform):
    conn = _conn()
    row = conn.execute(
        "SELECT 1 FROM history WHERE id=? AND platform=?",
        (post_id, platform)
    ).fetchone()
    conn.close()
    return row is not None


def insert_posts(posts):
    """Insert list of post dicts. Skip duplicates via INSERT OR IGNORE."""
    if not posts:
        return 0
    conn = _conn()
    inserted = 0
    for p in posts:
        try:
            conn.execute("""
                INSERT OR IGNORE INTO posts
                (id, platform, url, title, body, author, community,
                 points, num_comments, created_at, fetched_at, topic,
                 pain_score, demand_score, relevance_score, matched_queries)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                p["id"], p["platform"], p["url"], p.get("title", ""),
                p.get("body", ""), p.get("author", ""), p.get("community", ""),
                p.get("points", 0), p.get("num_comments", 0),
                p.get("created_at", ""), datetime.utcnow().isoformat(),
                p.get("topic", ""), p.get("pain_score", 0),
                p.get("demand_score", 0), p.get("relevance_score", 0),
                json.dumps(p.get("matched_queries", []))
            ))
            inserted += conn.total_changes  # approximate
        except sqlite3.IntegrityError:
            pass
    conn.commit()
    conn.close()
    return inserted


def update_scores(post_id, pain_score, demand_score, relevance_score, matched_queries):
    conn = _conn()
    conn.execute("""
        UPDATE posts SET pain_score=?, demand_score=?, relevance_score=?,
                         matched_queries=?
        WHERE id=?
    """, (pain_score, demand_score, relevance_score,
          json.dumps(matched_queries), post_id))
    conn.commit()
    conn.close()


def mark_history(post_ids, platform):
    conn = _conn()
    now = datetime.utcnow().isoformat()
    conn.executemany(
        "INSERT OR IGNORE INTO history (id, platform, processed_at) VALUES (?, ?, ?)",
        [(pid, platform, now) for pid in post_ids]
    )
    conn.commit()
    conn.close()


def get_top_posts(topic, limit=50, min_score=0):
    """Get top-scored posts for a topic, not yet analyzed."""
    conn = _conn()
    rows = conn.execute("""
        SELECT * FROM posts
        WHERE topic=? AND analyzed=0 AND relevance_score >= ?
        ORDER BY relevance_score DESC
        LIMIT ?
    """, (topic, min_score, limit)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_posts(topic):
    conn = _conn()
    rows = conn.execute("""
        SELECT * FROM posts WHERE topic=?
        ORDER BY relevance_score DESC
    """, (topic,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_analyzed(post_ids, analysis_results):
    """Mark posts as analyzed, store Gemini results."""
    conn = _conn()
    for pid, result in zip(post_ids, analysis_results):
        conn.execute("""
            UPDATE posts SET analyzed=1, analysis_result=? WHERE id=?
        """, (json.dumps(result, ensure_ascii=False) if result else None, pid))
    conn.commit()
    conn.close()


def save_run(topic, platforms, posts_fetched, posts_analyzed, report_path):
    conn = _conn()
    now = datetime.utcnow().isoformat()
    conn.execute("""
        INSERT INTO runs (topic, platforms, started_at, completed_at,
                          posts_fetched, posts_analyzed, report_path)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (topic, platforms, now, now, posts_fetched, posts_analyzed, report_path))
    conn.commit()
    conn.close()


def get_latest_run(topic=None):
    conn = _conn()
    if topic:
        row = conn.execute(
            "SELECT * FROM runs WHERE topic=? ORDER BY id DESC LIMIT 1",
            (topic,)
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT * FROM runs ORDER BY id DESC LIMIT 1"
        ).fetchone()
    conn.close()
    return dict(row) if row else None
