import sqlite3
import os
from metrics_db import calculate_totals

db_path = os.path.expanduser("~/KubeLLM/token_metrics.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute('''
    SELECT model,
        COUNT(*) as total_runs,
        SUM(CASE WHEN task_status = 1 THEN 1 ELSE 0 END) as successes,
        SUM(cost) as model_cost
    FROM metrics
    GROUP BY model
     ''')
success_stats = cursor.fetchall()
conn.close()

print("\nModel Success Stats (after this run):")
for model, total_runs, successes, model_cost in success_stats:
    rate = (successes / total_runs * 100) if total_runs > 0 else 0
    print(f"\t{model}: {successes} successes ({rate:.1f}% rate over {total_runs} runs)")
    print(f"\tcost: ${model_cost}")

total_metrics = calculate_totals(db_path)

print(f"\nGrant total:")
print(f"\truns: {total_metrics['total_entries']}")
print(f"\tsuccess: {total_metrics['total_successes']}")
print(f"\tverified success: {total_metrics['total_verified_successes']}")
print(f"\tcost: {total_metrics['grand_total_cost']}")


