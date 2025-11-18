import sqlite3
import os
from metrics_db import calculate_totals, get_model_stats
from pathlib import Path

# Use relative path from script location
SCRIPT_DIR = Path(__file__).parent.absolute()
db_path = str(SCRIPT_DIR.parent / "token_metrics.db")
success_stats = get_model_stats(db_path)

print("\nModel Success Stats (after this run):")

last_agent_type = None  # Track the previously printed agent type
for agent_type, model, total_runs, successes, verified_successes, duration_s, cost in success_stats:
    if agent_type != last_agent_type:
        print(f"Agent Type: {agent_type}")
        last_agent_type = agent_type
    
    success_rate = (successes / total_runs * 100) if total_runs > 0 else 0
    verified_success_rate = (verified_successes / total_runs * 100) if total_runs > 0 else 0
    
    if agent_type != 'verification':
        print(f"\t{model}: {successes} claimed_successes ({success_rate:.1f}% rate over {total_runs} runs)")
        print(f"\t{model}: {verified_successes} verified_successes ({verified_success_rate:.1f}% rate over {total_runs} runs)")
    
    print(f"\t{model}: {duration_s:.2f} seconds")
    print(f"\t{model}: ${cost:.4f}")

total_metrics = calculate_totals(db_path)

print(f"\nGrand total:")
print(f"\truns: {total_metrics['total_entries']}")
print(f"\tclaimed success: {total_metrics['total_successes']}")
print(f"\tverified success: {total_metrics['total_verified_successes']}")
print(f"\tdebug duration: {total_metrics['debug_duration']:.2f} seconds")
print(f"\tverification duration: {total_metrics['verification_duration']:.2f} seconds")
print(f"\tdebug cost: ${total_metrics['total_debug_cost']:.4f}")
print(f"\tverification cost: ${total_metrics['total_verification_cost']:.4f}")


