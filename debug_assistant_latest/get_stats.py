import sqlite3
import os

db_path = os.path.expanduser("~/KubeLLM/token_metrics.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute('''
    SELECT model,
        COUNT(*) as total_runs,
        SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successes,
        SUM(cost) as model_cost
    FROM metrics
    GROUP BY model
     ''')
success_stats = cursor.fetchall()
conn.close()

print("Model Success Stats (after this run):")
for model, total_runs, successes, model_cost in success_stats:
    rate = (successes / total_runs * 100) if total_runs > 0 else 0
    print(f"  {model}: {successes} successes ({rate:.1f}% rate over {total_runs} runs)")
    print(f" cost: ${model_cost}")

