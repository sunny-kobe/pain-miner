"""Load and merge config from YAML file + environment variables."""

import os
import yaml
from pathlib import Path


DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"
DEFAULT_ENV_PATH = Path(__file__).parent.parent / ".env"


def _load_dotenv(env_path=None):
    """Load .env file into os.environ (simple implementation, no dependency)."""
    path = Path(env_path) if env_path else DEFAULT_ENV_PATH
    if not path.exists():
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip("'\"")
            if key and key not in os.environ:  # Don't override existing env vars
                os.environ[key] = value


def load_config(config_path=None):
    """Load config from YAML, then override with env vars."""
    _load_dotenv()
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    if path.exists():
        with open(path) as f:
            cfg = yaml.safe_load(f) or {}
    else:
        cfg = {}

    # Ensure nested dicts exist
    cfg.setdefault("platforms", {})
    cfg["platforms"].setdefault("hn", {"enabled": True, "min_points": 2, "hits_per_query": 30})
    cfg["platforms"].setdefault("reddit", {})
    cfg["platforms"].setdefault("producthunt", {})
    cfg["platforms"].setdefault("twitter", {})
    cfg.setdefault("scoring", {})
    cfg.setdefault("gemini", {})
    cfg.setdefault("output", {"dir": "./output"})
    cfg.setdefault("search", {})

    r = cfg["platforms"]["reddit"]
    r.setdefault("user_agent", "pain-miner/1.0")
    r.setdefault("default_subreddits", ["SaaS", "startups", "Entrepreneur"])
    r.setdefault("sort", "top")
    r.setdefault("time_filter", "month")
    r.setdefault("limit", 100)
    r.setdefault("comment_threshold", 10)

    ph = cfg["platforms"]["producthunt"]
    ph["developer_token"] = os.environ.get("PRODUCTHUNT_TOKEN", ph.get("developer_token", ""))
    ph.setdefault("enabled", True)
    ph.setdefault("max_pages_per_topic", 3)

    tw = cfg["platforms"]["twitter"]
    tw["bearer_token"] = os.environ.get("X_BEARER_TOKEN", tw.get("bearer_token", ""))
    tw.setdefault("enabled", True)
    tw.setdefault("max_results_per_query", 50)

    g = cfg["gemini"]
    g["api_key"] = os.environ.get("GEMINI_API_KEY", g.get("api_key", ""))
    g.setdefault("model", "gemini-2.0-flash")
    g.setdefault("max_posts_to_analyze", 50)

    s = cfg["scoring"]
    s.setdefault("engagement_weight", 0.3)
    s.setdefault("pain_weight", 0.3)
    s.setdefault("demand_weight", 0.25)
    s.setdefault("cross_query_weight", 0.15)
    s.setdefault("min_score_for_analysis", 10)

    cfg["search"].setdefault("max_post_age_days", 180)
    cfg["search"].setdefault("query_delay_seconds", 0.3)

    return cfg
