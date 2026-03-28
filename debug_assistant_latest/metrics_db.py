# File: metrics_db.py
# This module handles SQLite operations for metrics logging.
# Import this in your main script: from metrics_db import store_metrics_entry, calculate_totals

import json
import sqlite3
import os
import time
import random
from datetime import datetime
from pathlib import Path

_MODEL_PRICING_PATH = Path(__file__).resolve().parent / "model_pricing.json"
_PRICING_CACHE: dict | None = None
_PRICING_LOADED_OK: bool = False


def _load_model_prices() -> dict:
    """Load model pricing from JSON next to this module; cache result."""
    global _PRICING_CACHE, _PRICING_LOADED_OK
    if _PRICING_CACHE is not None:
        return _PRICING_CACHE
    if not _MODEL_PRICING_PATH.is_file():
        print(
            f"Warning: Model pricing file not found at {_MODEL_PRICING_PATH} - costs set to $0.00"
        )
        _PRICING_CACHE = {}
        _PRICING_LOADED_OK = False
        return _PRICING_CACHE
    try:
        with open(_MODEL_PRICING_PATH, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            print(
                f"Warning: Invalid model pricing file at {_MODEL_PRICING_PATH} - costs set to $0.00"
            )
            _PRICING_CACHE = {}
            _PRICING_LOADED_OK = False
            return _PRICING_CACHE
        _PRICING_CACHE = data
        _PRICING_LOADED_OK = True
        return _PRICING_CACHE
    except (OSError, json.JSONDecodeError) as e:
        print(
            f"Warning: Could not load model pricing from {_MODEL_PRICING_PATH}: {e} - costs set to $0.00"
        )
        _PRICING_CACHE = {}
        _PRICING_LOADED_OK = False
        return _PRICING_CACHE

# Constants for retry logic
MAX_RETRIES = 5
BASE_DELAY_S = 0.1  # 100ms base delay
MAX_DELAY_S = 2.0   # Max 2s delay between retries
BUSY_TIMEOUT_MS = 30000  # 30 second busy timeout


def _get_connection(db_path: str) -> sqlite3.Connection:
    """
    Create a SQLite connection with settings optimized for concurrent access.

    - WAL mode allows concurrent readers while writing
    - Busy timeout waits instead of failing immediately on lock
    """
    conn = sqlite3.connect(db_path, timeout=BUSY_TIMEOUT_MS / 1000.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
    return conn


def _execute_with_retry(func, *args, **kwargs):
    """
    Execute a database operation with exponential backoff retry on lock errors.

    This handles the case where multiple processes contend for the database
    even with WAL mode and busy_timeout.
    """
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            return func(*args, **kwargs)
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) or "database is busy" in str(e):
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    # Exponential backoff with jitter
                    delay = min(BASE_DELAY_S * (2 ** attempt), MAX_DELAY_S)
                    jitter = random.uniform(0, delay * 0.5)
                    time.sleep(delay + jitter)
                    continue
            raise
    # If we exhausted retries, raise the last error
    raise last_error

def calculate_cost(model_name: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost based on model pricing from model_pricing.json next to this module."""
    prices_map = _load_model_prices()
    entry = prices_map.get(model_name)
    if entry is None:
        if _PRICING_LOADED_OK:
            print(f"Warning: Unknown model '{model_name}' - cost set to $0.00")
        return 0.0
    try:
        input_per_1k = float(entry["input_per_1k"])
        output_per_1k = float(entry["output_per_1k"])
    except (KeyError, TypeError, ValueError):
        print(f"Warning: Invalid pricing entry for model '{model_name}' - cost set to $0.00")
        return 0.0
    input_cost = (input_tokens / 1000.0) * input_per_1k
    output_cost = (output_tokens / 1000.0) * output_per_1k
    return round(input_cost + output_cost, 4)

def _store_metrics_entry_impl(db_path, metrics, task_status_verified):
    """Internal implementation of store_metrics_entry."""
    conn = _get_connection(db_path)
    try:
        cursor = conn.cursor()

        # Create table if not exists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                test_case TEXT NOT NULL,
                model TEXT,
                agent_type TEXT,
                input_tokens INTEGER DEFAULT 0,
                output_tokens INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                task_status INTEGER DEFAULT 0,
                task_status_verified  INTEGER DEFAULT 0,
                duration_s REAL DEFAULT 0.0,
                cost REAL DEFAULT 0.0
            )
        ''')

        # Insert the entry
        timestamp = datetime.now().isoformat()
        cursor.execute('''
            INSERT INTO metrics (timestamp, test_case, model, agent_type, input_tokens, output_tokens, total_tokens, task_status, task_status_verified, duration_s, cost)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (timestamp, metrics.get("test_case"), metrics.get("model"), metrics.get("agent_type"), metrics.get("input_tokens"), metrics.get("output_tokens"), metrics.get("total_tokens"), metrics.get("task_status"), task_status_verified, metrics.get("duration_s"), metrics.get("cost")))

        conn.commit()
    finally:
        conn.close()


def store_metrics_entry(db_path, metrics, task_status_verified):
    """
    Create table if needed and insert a metrics entry. Reusable across scripts.

    This function is safe for concurrent access from multiple processes.
    It uses WAL mode, busy timeout, and retry logic to handle contention.
    """
    # Ensure parent directory exists using Path API for consistency
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    _execute_with_retry(_store_metrics_entry_impl, db_path, metrics, task_status_verified)

def get_model_stats(db_path):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)  # Ensure dir exists
    conn = _get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT agent_type, model,
                COUNT(*) as total_runs,
                SUM(CASE WHEN task_status = 1 THEN 1 ELSE 0 END) as successes,
                SUM(CASE WHEN task_status_verified = 1 THEN 1 ELSE 0 END) as verified_successes,
                SUM(duration_s) as duration_s,
                SUM(cost) as cost
            FROM metrics
            GROUP BY agent_type, model
             ''')
        success_stats = cursor.fetchall()
    finally:
        conn.close()
    return success_stats

def calculate_totals(db_path):
    """Calculate grand totals for tokens and costs across all test cases."""
    conn = _get_connection(db_path)
    try:
        cursor = conn.cursor()

        # Grand totals
        cursor.execute('SELECT SUM(total_tokens) FROM metrics')
        grand_total_tokens = cursor.fetchone()[0] or 0

        cursor.execute('SELECT SUM(cost) FROM metrics WHERE agent_type = "debug"')
        debug_cost = cursor.fetchone()[0] or 0.0

        cursor.execute('SELECT SUM(duration_s) FROM metrics WHERE agent_type = "debug"')
        debug_duration_s = cursor.fetchone()[0] or 0.0

        cursor.execute('SELECT SUM(cost) FROM metrics WHERE agent_type = "verification"')
        verification_cost = cursor.fetchone()[0] or 0.0

        cursor.execute('SELECT SUM(duration_s) FROM metrics WHERE agent_type = "verification"')
        verification_duration_s = cursor.fetchone()[0] or 0.0

        # Per test case (tokens and costs)
        cursor.execute('SELECT test_case, SUM(total_tokens), SUM(cost) FROM metrics GROUP BY test_case')
        per_test_data = cursor.fetchall()
        per_test = {row[0]: {'tokens': row[1] or 0, 'cost': row[2] or 0.0} for row in per_test_data}

        # Total entries
        cursor.execute('SELECT COUNT(*) FROM metrics WHERE agent_type = "debug"')
        total_entries = cursor.fetchone()[0] or 0

        # Total success
        cursor.execute('SELECT COUNT(*) FROM metrics WHERE agent_type = "debug" AND task_status = 1')
        total_successes = cursor.fetchone()[0] or 0

        # Total verified success
        cursor.execute('SELECT COUNT(*) FROM metrics WHERE agent_type = "debug" AND task_status_verified = 1')
        total_verified_successes = cursor.fetchone()[0] or 0
    finally:
        conn.close()

    return {
        "grand_total_tokens": grand_total_tokens,
        "total_debug_cost": debug_cost,
        "total_verification_cost": verification_cost,
        "debug_duration": debug_duration_s,
        "verification_duration": verification_duration_s,
        "per_test_case": per_test,
        "total_entries": total_entries,
        "total_successes": total_successes,
        "total_verified_successes": total_verified_successes
    }
