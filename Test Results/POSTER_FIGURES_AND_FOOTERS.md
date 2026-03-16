# Poster: Results / Graphs and Key Findings

Use the data files in this folder to build the figures. Below: what to plot and **Key Findings** footer text for each.

---

## Figure 1 — Success Rate (Bar Graph)

**Title:** Success rate before and after verification agent  
**Y-axis:** Success rate (0–1 or 0–100%)  
**X-axis:** Model combination  
**Bars:** Two bars per model: “Before verification” (debug self-report), “After verification” (verification result).

**Data file:** `poster_success_by_model.csv`  
- `success_before_verification` → bar “Before verification”  
- `success_after_verification` → bar “After verification”  
- `model_combination` → X-axis labels  

**Key Findings (footer):**  
*Debug agent self-reported success rate (before verification) is higher than the rate confirmed by the verification agent (after verification). Verification reduces false positives; the only combination with data (Nano + GPT-5-mini) shows a drop from ~46% self-reported to ~26% verified.*

---

## Figure 2 — Cost (Bar Graph)

**Title:** Cost before and after verification agent  
**Y-axis:** Cost (e.g. total or average per run)  
**X-axis:** Model combination  
**Bars:** Two bars per model: “Before verification” (debug only), “After verification” (debug + verification).

**Data file:** `poster_cost_by_model.csv`  
- `cost_before_verification_total` or `avg_cost_per_run_before` → “Before verification”  
- `cost_after_verification_total` or `avg_cost_per_run_after` → “After verification”  
- `model_combination` → X-axis labels  

**Key Findings (footer):**  
*Adding the verification agent increases cost per run (debug-only vs debug+verification). For the Nano + GPT-5-mini combination, total cost with verification is about 3.7× the debug-only cost; verification adds both value and token cost.*

---

## Figure 3 — Average task completion time (Text)

**Content (write in text on the poster):**  
Use the numbers in `poster_time_summary.txt`:

- **Without verification (debug agent only):** 106.4 seconds (~1.8 min) per run.  
- **With verification (debug + verification):** 166.2 seconds (~2.8 min) per run.  
- Verification adds about 60 seconds per run on average.

**Key Findings (footer):**  
*Including the verification agent increases average task completion time by roughly 56% (~60 s per run), reflecting the extra step of verification after the debug agent.*

---

## Data coverage note

- **Model combinations:** Only “Nano (debug) + GPT-5-mini (verification)” has data (Config 1 & 3; they share the same debug/verification models in the DB).  
- **Gemini (Config 2):** No data in this export (API/quota issues); use N/A or “No data” in the bar graphs and mention in the caption or Key Findings.
