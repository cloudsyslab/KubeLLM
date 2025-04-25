import re
import sys
import os

if len(sys.argv) != 3:
    print(f"Usage: python {sys.argv[0]} <filename> <modelname>")
    sys.exit(1)

LOG_FILE_PATH = sys.argv[1]
model = sys.argv[2]

if not os.path.isfile(LOG_FILE_PATH):
    print(f"❌ File '{LOG_FILE_PATH}' does not exist.")
    sys.exit(1)

# Example costs (per 1Mtokens) - REPLACE WITH YOUR ACTUAL MODEL COSTS
if model == 'o3-mini':
    INPUT_COST_PER_1M_TOKENS = 1.10
    OUTPUT_COST_PER_1M_TOKENS = 4.40
elif model == 'gpt-4o':
    INPUT_COST_PER_1M_TOKENS = 2.50
    OUTPUT_COST_PER_1M_TOKENS = 10.0
elif model == 'llama3.3':
    INPUT_COST_PER_1M_TOKENS = 0
    OUTPUT_COST_PER_1M_TOKENS = 0
elif model == 'gemini-1.5-flash':
    INPUT_COST_PER_1M_TOKENS = 0.075
    OUTPUT_COST_PER_1M_TOKENS = 0.30
else:
    print ('unknown model')
    sys.exit(1)


# --- Regex Patterns to find lines and capture numbers ---
INPUT_TOKEN_RE = re.compile(r"Input tokens:\s*(\d+)")
OUTPUT_TOKEN_RE = re.compile(r"Output tokens:\s*(\d+)")

# --- Initialization ---
total_input_tokens = 0
total_output_tokens = 0
lines_processed = 0

# --- Processing ---
try:
    print(f"Processing {LOG_FILE_PATH}...")
    with open(LOG_FILE_PATH, 'r') as f:
        for line in f:
            lines_processed += 1
            # Check for input tokens
            match_in = INPUT_TOKEN_RE.search(line)
            if match_in:
                try:
                    total_input_tokens += int(match_in.group(1))
                except ValueError:
                    print(f"Warning: Found input token pattern but failed to parse number on line {lines_processed}: {line.strip()}")
                continue # Assumes a line won't contain both input and output counts

            # Check for output tokens if input wasn't found
            match_out = OUTPUT_TOKEN_RE.search(line)
            if match_out:
                try:
                    total_output_tokens += int(match_out.group(1))
                except ValueError:
                    print(f"Warning: Found output token pattern but failed to parse number on line {lines_processed}: {line.strip()}")

except FileNotFoundError:
    print(f"Error: File not found at '{LOG_FILE_PATH}'")
    sys.exit(1)
except Exception as e:
    print(f"An error occurred during processing: {e}")
    sys.exit(1)

# --- Calculation & Output ---
total_tokens = total_input_tokens + total_output_tokens
input_cost = (total_input_tokens / 1000000) * INPUT_COST_PER_1M_TOKENS
output_cost = (total_output_tokens / 1000000) * OUTPUT_COST_PER_1M_TOKENS
total_cost = input_cost + output_cost

print("\n--- Overall Token & Cost Summary ---")
print(f"Lines Processed:     {lines_processed}")
print(f"Total Input Tokens:  {total_input_tokens}")
print(f"Total Output Tokens: {total_output_tokens}")
print(f"Grand Total Tokens:  {total_tokens}")
print("--- Estimated Cost ---")
print(f"Input Cost (@ ${INPUT_COST_PER_1M_TOKENS:.6f}/1k):  ${input_cost:.6f}")
print(f"Output Cost (@ ${OUTPUT_COST_PER_1M_TOKENS:.6f}/1k): ${output_cost:.6f}")
print(f"Total Estimated Cost:       ${total_cost:.6f}")

