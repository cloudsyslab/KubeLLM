# File: metrics_db.py
# This module handles SQLite operations for metrics logging.
# Import this in your main script: from metrics_db import store_metrics_entry, calculate_totals

import sqlite3
import os
from datetime import datetime

def calculate_cost(model_name: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost based on model pricing."""
    # Pricing dict for LLM models (NEED TO VERIFY)
    MODEL_PRICES = {
        'gpt-5': {'input_per_1k': 0.00125, 'output_per_1k': 0.01},
        'gpt-5-mini': {'input_per_1k': 0.00025, 'output_per_1k': 0.002},
        'gpt-5-nano': {'input_per_1k': 0.00005, 'output_per_1k': 0.0004},
        'gpt-4.1': {'input_per_1k': 0.003, 'output_per_1k': 0.012},
        'gpt-4o': {'input_per_1k': 0.005, 'output_per_1k': 0.02},
        'gpt-4o-mini': {'input_per_1k': 0.0006, 'output_per_1k': 0.0024},
        # Add more as needed; fallback to 0 for unknown
    }
    prices = MODEL_PRICES.get(model_name, {'input_per_1k': 0, 'output_per_1k': 0})
    if prices['input_per_1k'] == 0 and prices['output_per_1k'] == 0:
        print(f"Warning: Unknown model '{model_name}' - cost set to $0.00")
    input_cost = (input_tokens / 1000.0) * prices['input_per_1k']
    output_cost = (output_tokens / 1000.0) * prices['output_per_1k']
    return round(input_cost + output_cost, 4)

def store_metrics_entry(db_path, test_case, model, input_tokens, output_tokens, total_tokens, success, cost):
    """Create table if needed and insert a metrics entry. Reusable across scripts."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)  # Ensure dir exists
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create table if not exists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            test_case TEXT NOT NULL,
            model TEXT,
            input_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            total_tokens INTEGER DEFAULT 0,
            success INTEGER DEFAULT 0,
            cost REAL DEFAULT 0.0
        )
    ''')

    # Insert the entry
    timestamp = datetime.now().isoformat()
    cursor.execute('''
        INSERT INTO metrics (timestamp, test_case, model, input_tokens, output_tokens, total_tokens, success, cost)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (timestamp, test_case, model, input_tokens, output_tokens, total_tokens, int(success), cost))

    conn.commit()
    conn.close()

def get_model_statistics(db_path):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)  # Ensure dir exists
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT model,
            COUNT(*) as total_runs,
            SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successes
        FROM metrics
        GROUP BY model
         ''')
    success_stats = cursor.fetchall()
    conn.close()
    return success_stats




def calculate_totals(db_path):
    """Calculate grand totals for tokens and costs across all test cases."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Grand totals
    cursor.execute('SELECT SUM(total_tokens) FROM metrics')
    grand_total_tokens = cursor.fetchone()[0] or 0
    
    cursor.execute('SELECT SUM(cost) FROM metrics')
    grand_total_cost = cursor.fetchone()[0] or 0.0
    
    # Per test case (tokens and costs)
    cursor.execute('SELECT test_case, SUM(total_tokens), SUM(cost) FROM metrics GROUP BY test_case')
    per_test_data = cursor.fetchall()
    per_test = {row[0]: {'tokens': row[1] or 0, 'cost': row[2] or 0.0} for row in per_test_data}
    
    # Total entries
    cursor.execute('SELECT COUNT(*) FROM metrics')
    total_entries = cursor.fetchone()[0] or 0
    
    conn.close()
    
    return {
        "grand_total_tokens": grand_total_tokens,
        "grand_total_cost": grand_total_cost,
        "per_test_case": per_test,
        "total_entries": total_entries
    }
