(() => {
  "use strict";

  const state = {
    page: "overview",
    readiness: null,
    cases: [],
    selectedCases: new Set(),
    jobs: [],
    history: [],
    source: "all",
    query: "",
    selectedRuns: new Set(),
    publishPreview: null,
    pollTimer: null,
    searchTimer: null,
  };

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const el = (tag, className = "", text = null) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== null && text !== undefined) node.textContent = String(text);
    return node;
  };
  const button = (text, className, action) => {
    const node = el("button", className, text);
    node.type = "button";
    if (action) node.addEventListener("click", action);
    return node;
  };
  const statusTone = (value) => ({ READY: "ready", completed: "ready", pass: "ready", blocked: "blocked", BLOCKED: "blocked", failed: "error", error: "error", running: "running", queued: "running", stop_requested: "running", stopped: "stopped", interrupted: "incomplete", incomplete: "incomplete" }[value] || "");
  const statusText = (value) => ({ READY: "READY", BLOCKED: "BLOCKED", completed: "COMPLETE", running: "RUNNING", queued: "QUEUED", stop_requested: "STOP REQUESTED", stopped: "STOPPED", interrupted: "INTERRUPTED", failed: "FAILED", blocked: "BLOCKED", recorded: "RECORDED", incomplete: "INCOMPLETE", PASS: "PASS", FAIL: "FAIL", ERROR: "ERROR", TIMEOUT: "TIMEOUT", RUNNER_ERROR: "RUNNER ERROR", UNKNOWN: "UNKNOWN" }[value] || (value || "UNKNOWN").replaceAll("_", " ").toUpperCase());

  function toast(message, isError = false) {
    const box = $("#toast");
    box.textContent = message;
    box.classList.toggle("error", isError);
    box.hidden = false;
    clearTimeout(toast.timeout);
    toast.timeout = setTimeout(() => { box.hidden = true; }, 3800);
  }

  async function api(path, options = {}) {
    const response = await fetch(path, {
      credentials: "same-origin",
      ...options,
      headers: { ...(options.body ? { "Content-Type": "application/json" } : {}), ...(options.headers || {}) },
      body: options.body ? JSON.stringify(options.body) : options.body,
    });
    let data = {};
    try { data = await response.json(); } catch { /* Report the HTTP result below. */ }
    if (response.status === 401) {
      showLogin();
      throw new Error("Sign in to continue.");
    }
    if (!response.ok) throw new Error(data.detail || `Request failed (${response.status}).`);
    return data;
  }

  function showLogin(message = "") {
    $("#login-screen").hidden = false;
    $("#app-shell").hidden = true;
    const target = $("#login-message");
    if (target) target.textContent = message;
    const password = $("#password");
    if (password) password.focus({ preventScroll: true });
  }

  function showApp() {
    $("#login-screen").hidden = true;
    $("#app-shell").hidden = false;
  }

  function updateNavigation() {
    const page = location.hash.replace(/^#/, "") || "overview";
    const allowed = ["overview", "launch", "runs", "compare", "environment"];
    state.page = allowed.includes(page) ? page : "overview";
    $$(".page").forEach((node) => {
      const active = node.id === `page-${state.page}`;
      node.classList.toggle("active-page", active);
      node.hidden = !active;
    });
    $$("[data-page-link]").forEach((node) => node.classList.toggle("active", node.dataset.pageLink === state.page && node.classList.contains("nav-link")));
    const names = { overview: "Overview", launch: "New campaign", runs: "Run history", compare: "Compare", environment: "Environment" };
    $("#page-crumb").textContent = names[state.page];
    if (state.page === "launch") {
      loadCases();
      updateCampaignPreview();
    }
    if (state.page === "runs") loadHistory();
    if (state.page === "compare" && state.selectedRuns.size) loadComparison();
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function formatDate(raw, short = false) {
    if (!raw || typeof raw !== "string") return "—";
    const date = new Date(raw);
    if (Number.isNaN(date.getTime())) return raw.slice(0, 16);
    return new Intl.DateTimeFormat(undefined, short
      ? { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }
      : { year: "numeric", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }).format(date);
  }

  function formatPercent(value) {
    return typeof value === "number" && Number.isFinite(value) ? `${(value * 100).toFixed(1)}%` : "—";
  }

  function formatCost(value) {
    return typeof value === "number" && Number.isFinite(value) ? `$${value.toFixed(2)}` : "—";
  }

  function formatDuration(seconds) {
    if (typeof seconds !== "number" || !Number.isFinite(seconds)) return "—";
    if (seconds < 60) return `${seconds.toFixed(0)}s`;
    const mins = Math.floor(seconds / 60);
    const remain = Math.round(seconds % 60);
    if (mins < 60) return `${mins}m ${remain}s`;
    return `${Math.floor(mins / 60)}h ${mins % 60}m`;
  }

  function groundTruthOutcome(row) {
    if (row.ground_truth_passed === true) return "PASS";
    if (row.ground_truth_passed === false) return "FAIL";
    return row.ground_truth_configured === false ? "Not configured" : "Unavailable";
  }

  function tag(label, value) {
    return el("span", `status-tag ${statusTone(value)}`, label);
  }

  function sourceBadge(source) {
    return el("span", `source-badge ${source || ""}`, source || "unknown");
  }

  function metricCard(label, value, note, symbol = "·") {
    const card = el("article", "metric-card");
    const top = el("div", "metric-card-top");
    top.append(el("span", "", label), el("span", "metric-symbol", symbol));
    card.append(top, el("strong", "metric-value", value), el("span", "metric-note", note));
    return card;
  }

  async function loadOverview() {
    try {
      const [overview, latestJobs] = await Promise.all([api("/api/overview"), api("/api/jobs")]);
      state.jobs = latestJobs.jobs || overview.jobs || [];
      const summary = overview.headline || {};
      const metrics = $("#overview-metrics");
      metrics.replaceChildren(
        metricCard("Known Ground Truth outcomes", `${summary.ground_truth_passed || 0} / ${summary.ground_truth_known || 0}`, "Counts across the indexed run records", "✓"),
        metricCard("Structured run records", summary.runs || 0, `${summary.integrity_incomplete_runs || 0} with missing outcomes`, "↗"),
        metricCard("Runs with cost data", summary.cost_run_count || 0, "Inspect individual runs by condition", "$"),
        metricCard("Runs with timing", summary.duration_run_count || 0, "Inspect individual run durations", "◷"),
      );
      const readiness = overview.readiness || {};
      state.readiness = readiness.status === "READY" ? { status: "READY", generated_at: readiness.checked_at } : null;
      renderReadinessSummary(readiness.status, readiness.checked_at);
      const lastReadiness = state.jobs.find((job) => job.kind === "readiness" || job.kind === "prepare");
      if (lastReadiness?.result?.readiness) renderEnvironment(lastReadiness.result, readiness.status);
      updateSources(overview.sources || {});
      renderRecentRuns(overview.latest_runs || []);
      renderJobs(state.jobs.slice(0, 5));
      const localCount = (overview.sources || {}).local || 0;
      $("#nav-run-count").textContent = localCount ? String(localCount) : "";
      updateLaunchGate();
      schedulePolling();
    } catch (error) {
      toast(error.message, true);
    }
  }

  function renderReadinessSummary(status, checkedAt) {
    const banner = $("#overview-readiness");
    banner.classList.remove("is-ready", "is-blocked");
    const pulse = $(".readiness-pulse .status-dot", banner);
    pulse.className = `status-dot ${status === "READY" ? "dot-green" : status === "BLOCKED" ? "dot-red" : "dot-muted"}`;
    if (status === "READY") {
      banner.classList.add("is-ready");
      $("#overview-readiness-title").textContent = "Your selected lab is ready";
      $("#overview-readiness-text").textContent = `Last checked ${formatDate(checkedAt)}. Launches still pass through the canonical runner preflight.`;
    } else if (status === "BLOCKED") {
      banner.classList.add("is-blocked");
      $("#overview-readiness-title").textContent = "Some environment checks need attention";
      $("#overview-readiness-text").textContent = "Review the safe diagnostics or prepare the selected lane, then run preflight again.";
    } else {
      $("#overview-readiness-title").textContent = "Preflight has not run";
      $("#overview-readiness-text").textContent = "Check database, providers, RAG, and Kubernetes before your next run.";
    }
    $("#readiness-launch-note").classList.toggle("is-ready", status === "READY");
    $("#readiness-launch-note").replaceChildren(
      el("span", `status-dot ${status === "READY" ? "dot-green" : "dot-amber"}`),
      el("span", status === "READY" ? "Preflight passed. Case runs retain their own runner checks." : "A fresh preflight is required before a campaign can launch."),
    );
  }

  function updateSources(sources) {
    const node = $("#source-strip");
    node.replaceChildren(
      el("span", "", "History sources"),
      sourceBadge("canonical"), el("strong", "", sources.canonical || 0),
      el("span", "source-divider"), sourceBadge("exploratory"), el("strong", "", sources.exploratory || 0),
      el("span", "source-divider"), sourceBadge("local"), el("strong", "", sources.local || 0),
      el("span", "", "structured runs indexed"),
    );
  }

  function renderRecentRuns(records) {
    const host = $("#overview-runs");
    if (!records.length) {
      host.replaceChildren(el("div", "empty-table", "No structured benchmark runs found yet."));
      return;
    }
    const table = el("table");
    const head = el("thead");
    const header = el("tr");
    ["RUN", "SOURCE", "GROUND TRUTH", "COST", "STATUS"].forEach((title) => header.append(el("th", "", title)));
    head.append(header);
    const body = el("tbody");
    records.slice(0, 6).forEach((run) => {
      const row = el("tr");
      const identity = el("td");
      const open = button(run.run_id || "Recorded run", "run-title-button", () => openDetail(run.ref));
      identity.append(open);
      identity.append(el("small", "", `${run.technique || "Technique not recorded"} · ${formatDate(run.run_id, true)}`));
      const source = el("td"); source.append(sourceBadge(run.source));
      const gt = el("td", "metric-inline", run.ground_truth_known ? `${run.ground_truth_passed}/${run.ground_truth_known} · ${formatPercent(run.ground_truth_rate)}` : "Unavailable");
      row.append(identity, source, gt, el("td", "metric-inline", formatCost(run.total_cost)), el("td", "", "").appendChild(tag(statusText(run.status), run.status)).parentElement);
      body.append(row);
    });
    table.append(head, body);
    host.replaceChildren(table);
  }

  function renderJobs(records) {
    const list = $("#overview-jobs");
    list.replaceChildren();
    if (!records.length) {
      const empty = el("div", "job-list-empty");
      empty.append(el("span", "", "⌁"), el("strong", "", "No operator jobs yet."), el("br"), document.createTextNode("Your preflight checks and campaigns will appear here."));
      list.append(empty);
      return;
    }
    records.forEach((job) => {
      const item = el("div", "job-list-item");
      const dot = job.status === "completed" ? "dot-green" : ["failed", "blocked"].includes(job.status) ? "dot-red" : ["queued", "running", "stop_requested"].includes(job.status) ? "dot-amber" : "dot-muted";
      item.append(el("span", `status-dot ${dot}`));
      const text = el("div");
      const title = job.kind === "campaign" ? `Campaign · ${job.current_index || 0}/${job.total || 0}` : job.kind === "publish" ? "Publish results" : job.kind === "prepare" ? "Prepare environment" : "Readiness check";
      text.append(el("strong", "", title), el("small", "", job.current_label || statusText(job.status)));
      item.append(text, tag(statusText(job.status), job.status));
      if (job.kind === "campaign" && ["completed", "stopped", "failed", "interrupted"].includes(job.status)) {
        const actions = el("div", "job-list-actions");
        const report = el("a", "", "View safe report");
        report.href = `/api/jobs/${job.id}/report`;
        report.target = "_blank";
        report.rel = "noopener noreferrer";
        actions.append(report, button("Publish results", "", () => openPublishReview(job.id)));
        item.append(actions);
      }
      list.append(item);
    });
  }

  function activeJobs() {
    return state.jobs.filter((job) => ["queued", "running", "stop_requested"].includes(job.status));
  }

  function schedulePolling() {
    clearInterval(state.pollTimer);
    if (activeJobs().length) {
      state.pollTimer = setInterval(async () => {
        try {
          const data = await api("/api/jobs");
          state.jobs = data.jobs || [];
          renderJobs(state.jobs.slice(0, 5));
          renderJobBanner();
          renderLaunchJobProgress();
          if (state.page === "overview") renderJobs(state.jobs.slice(0, 5));
          if (state.page === "runs") await loadHistory();
          if (!activeJobs().length) {
            await loadOverview();
            schedulePolling();
          }
        } catch (error) {
          if (!error.message.includes("Sign in")) toast(error.message, true);
          clearInterval(state.pollTimer);
        }
      }, 1800);
    } else {
      $("#job-banner").hidden = true;
      renderLaunchJobProgress();
    }
  }

  function renderJobBanner() {
    const banner = $("#job-banner");
    const job = state.jobs.find((item) => ["queued", "running", "stop_requested"].includes(item.status));
    if (!job) {
      banner.hidden = true;
      return;
    }
    banner.hidden = false;
    const progress = job.total ? Math.min(100, Math.round(job.current_index / job.total * 100)) : 0;
    const row = el("div", "job-banner-row");
    row.append(el("span", `status-dot ${job.status === "stop_requested" ? "dot-amber" : "dot-green"}`));
    const copy = el("div", "job-banner-text");
    copy.append(el("strong", "", job.kind === "campaign" ? `Campaign in progress · ${job.current_index}/${job.total} attempts started` : job.kind === "publish" ? "Publishing the reviewed result files" : job.kind === "prepare" ? "Preparing and rechecking the selected environment" : "Checking environment readiness"));
    copy.append(el("small", "", job.current_label || "Worker continues if you close this browser."));
    row.append(copy);
    const actions = el("div", "job-banner-actions");
    actions.append(button("View job", "text-button", () => { location.hash = job.kind === "campaign" ? "runs" : "environment"; }));
    if (job.kind === "campaign" && job.status !== "stop_requested") {
      actions.append(button("Stop after this case", "text-button", () => requestStop(job.id)));
    }
    row.append(actions);
    const track = el("div", "job-progress-track");
    const value = el("progress", "job-progress-value");
    value.max = 100;
    value.value = progress;
    track.append(value);
    banner.replaceChildren(row, track);
  }

  function updateLaunchGate() { renderLaunchJobProgress(); }

  async function runReadiness(prepare = false) {
    const buttonNode = $(prepare ? "#prepare-environment" : "#run-readiness");
    const other = $(prepare ? "#environment-prepare-button" : "#environment-check-button");
    if (buttonNode) buttonNode.disabled = true;
    if (other) other.disabled = true;
    try {
      const job = await api(prepare ? "/api/prepare" : "/api/readiness", { method: "POST", body: {} });
      toast(prepare ? "Safe preparation started. Checks will run again when it finishes." : "Environment preflight started.");
      state.jobs.unshift(job);
      renderJobBanner();
      schedulePolling();
    } catch (error) {
      toast(error.message, true);
    } finally {
      if (buttonNode) buttonNode.disabled = false;
      if (other) other.disabled = false;
    }
  }

  async function requestStop(jobId) {
    try {
      await api(`/api/jobs/${jobId}/stop`, { method: "POST", body: {} });
      toast("Stop requested. The current case will finish and run teardown first.");
      const result = await api("/api/jobs");
      state.jobs = result.jobs || [];
      renderJobBanner();
      schedulePolling();
    } catch (error) { toast(error.message, true); }
  }

  async function loadCases() {
    if (state.cases.length) return;
    try {
      const data = await api("/api/cases");
      state.cases = data.cases || [];
      renderCases();
    } catch (error) {
      $("#case-catalog").replaceChildren(el("p", "muted", error.message));
    }
  }

  function renderCases() {
    const root = $("#case-catalog");
    const search = $("#case-search").value.trim().toLowerCase();
    root.replaceChildren();
    const visible = state.cases.filter((item) => item.id.toLowerCase().includes(search));
    if (!visible.length) {
      root.append(el("p", "muted", state.cases.length ? "No cases match that filter." : "The canonical runner has no available cases."));
      return;
    }
    visible.forEach((item) => {
      const label = el("label", `case-option${state.selectedCases.has(item.id) ? " selected" : ""}`);
      const input = el("input");
      input.type = "checkbox";
      input.value = item.id;
      input.checked = state.selectedCases.has(item.id);
      input.addEventListener("change", () => {
        if (input.checked) state.selectedCases.add(item.id); else state.selectedCases.delete(item.id);
        label.classList.toggle("selected", input.checked);
        updateCampaignPreview();
      });
      label.append(input, el("span", "", item.label));
      root.append(label);
    });
  }

  function selectedCases() { return [...state.selectedCases]; }
  function selectedTechniques() { return $$('input[name="technique"]:checked').map((node) => node.value); }
  function selectedModels() { return [...new Set($("#debug-models").value.split(/\r?\n/).map((value) => value.trim()).filter(Boolean))]; }

  function updateCampaignPreview() {
    const cases = selectedCases();
    const techniques = selectedTechniques();
    const models = selectedModels();
    const reps = Number.parseInt($("#repetitions").value, 10) || 1;
    const total = cases.length * techniques.length * Math.max(1, models.length) * reps;
    $("#attempt-count").textContent = String(total);
    const breakdown = $("#campaign-breakdown");
    const rows = [
      ["Selected cases", cases.length],
      ["Techniques", techniques.length],
      ["DebugAgent models", models.length || "Case defaults"],
      ["Repetitions", reps],
    ];
    breakdown.replaceChildren();
    if (!total) breakdown.append(el("span", "", "Select cases and techniques to see your plan."));
    rows.forEach(([label, value]) => {
      const row = el("div", "preview-row");
      row.append(el("span", "", label), el("strong", "", value));
      breakdown.append(row);
    });
    updateLaunchGate();
  }

  function campaignPayload() {
    return {
      cases: selectedCases(),
      techniques: selectedTechniques(),
      debug_models: selectedModels(),
      api_model: $("#api-model").value.trim(),
      verification_model: $("#verification-model").value.trim(),
      repetitions: Number.parseInt($("#repetitions").value, 10) || 1,
    };
  }

  function openCampaignReview(payload) {
    const dialog = $("#confirm-campaign");
    const models = payload.debug_models.length ? payload.debug_models.join(", ") : "each case's configured DebugAgent model";
    $("#campaign-confirm-text").textContent = `Run ${$("#attempt-count").textContent} serial attempts through the canonical runner.`;
    const summary = $("#campaign-confirm-summary");
    summary.replaceChildren();
    [["Cases", payload.cases.length], ["Techniques", payload.techniques.join(", ")], ["DebugAgent", models], ["Repetitions", payload.repetitions], ["API model", payload.api_model || "Configured"], ["Verification model", payload.verification_model || "Configured"]].forEach(([label, value]) => {
      const item = el("div");
      item.append(el("strong", "", label), document.createTextNode(String(value)));
      summary.append(item);
    });
    dialog.showModal();
  }

  async function startCampaign(payload) {
    try {
      const job = await api("/api/campaign", { method: "POST", body: payload });
      state.jobs.unshift(job);
      renderJobBanner();
      schedulePolling();
      toast("Campaign queued. It continues on the server if you close this browser.");
      location.hash = "overview";
    } catch (error) { toast(error.message, true); }
  }

  async function openPublishReview(jobId) {
    const dialog = $("#publish-dialog");
    state.publishPreview = null;
    $("#publish-summary").textContent = "Preparing the safe export preview…";
    $("#publish-facts").replaceChildren();
    $("#publish-model-list").replaceChildren();
    $("#publish-file-list").replaceChildren();
    $("#publish-file-count").textContent = "";
    $("#publish-exclusions").textContent = "";
    $("#publish-ack").checked = false;
    $("#confirm-publish").disabled = true;
    $("#confirm-publish").dataset.jobId = jobId;
    dialog.showModal();
    try {
      const preview = await api(`/api/publish/preview/${jobId}`, { method: "POST", body: {} });
      state.publishPreview = preview;
      $("#publish-summary").textContent = `This pack is ready for ${preview.branch} → ${preview.upstream}. The commit will contain only the files listed below.`;
      [
        ["Campaign", preview.campaign_status],
        ["Recorded attempts", `${preview.attempts_recorded} / ${preview.attempts_planned}`],
        ["Known Ground Truth", `${preview.ground_truth_passed} / ${preview.ground_truth_known}`],
        ["Verifier agreement", preview.verifier_comparable ? `${preview.verifier_agrees} / ${preview.verifier_comparable} comparable` : `Unavailable · ${preview.verifier_known} recorded`],
        ["Not exported", `${preview.attempts_excluded} unstructured · ${preview.attempts_unstarted} unstarted`],
      ].forEach(([label, value]) => {
        const fact = el("div");
        fact.append(el("strong", "", label), document.createTextNode(String(value)));
        $("#publish-facts").append(fact);
      });
      const models = preview.models || [];
      $("#publish-model-list").replaceChildren(...(models.length ? models.map((value) => el("span", "", value)) : [el("span", "", "No model identifiers found")]));
      const files = preview.files || [];
      $("#publish-file-count").textContent = `${files.length} files`;
      $("#publish-file-list").textContent = files.map((file) => `${file.path}  ·  SHA-256 ${file.sha256}`).join("\n");
      $("#publish-exclusions").textContent = "The export uses the repository allowlist: raw logs, progress traces, prompts, free text, endpoints, credentials, and private lane details are excluded. Missing outcomes remain unavailable. The archive is marked exploratory and won't enter canonical analysis by default.";
    } catch (error) {
      $("#publish-summary").textContent = error.message;
      $("#publish-exclusions").textContent = "No files have been published.";
    }
  }

  async function publishReviewedCampaign() {
    const preview = state.publishPreview;
    if (!preview || !$("#publish-ack").checked) return;
    const submit = $("#confirm-publish");
    submit.disabled = true;
    submit.textContent = "Starting…";
    try {
      const job = await api("/api/publish", {
        method: "POST",
        body: { job_id: submit.dataset.jobId, preview_token: preview.preview_token },
      });
      $("#publish-dialog").close();
      state.jobs.unshift(job);
      renderJobs(state.jobs.slice(0, 5));
      renderJobBanner();
      schedulePolling();
      toast("Publish job started. The listed files will be committed and pushed.");
    } catch (error) {
      toast(error.message, true);
      submit.disabled = false;
    } finally {
      submit.textContent = "Publish results";
    }
  }

  async function loadHistory(force = false) {
    const host = $("#history-table");
    host.setAttribute("aria-busy", "true");
    const query = new URLSearchParams({ source: state.source, q: state.query });
    if (force) query.set("refresh", "true");
    try {
      const data = await api(`/api/history?${query.toString()}`);
      state.history = data.runs || [];
      const summary = data.summary || {};
      const metrics = $("#history-metrics");
      metrics.replaceChildren(
        metricCard("Indexed runs", summary.runs || 0, `${(data.runs || []).length} shown below`, "↗"),
        metricCard("Known Ground Truth outcomes", `${summary.ground_truth_passed || 0} / ${summary.ground_truth_known || 0}`, "Counts across the filtered run records", "✓"),
        metricCard("Runs with cost data", summary.cost_run_count || 0, "Compare costs within matching conditions", "$"),
        metricCard("Missing evidence", summary.integrity_incomplete_runs || 0, "Run records with unknown or unattempted outcomes", "!"),
      );
      renderHistoryTable(data);
    } catch (error) {
      host.replaceChildren(el("div", "empty-table", error.message));
    } finally { host.removeAttribute("aria-busy"); }
  }

  function renderHistoryTable(data) {
    const host = $("#history-table");
    host.replaceChildren();
    if (!state.history.length) {
      host.append(el("div", "empty-table", "No structured results match this filter."));
      $("#history-truncated").hidden = true;
      renderSelectionBar(host);
      return;
    }
    const table = el("table", "history-table");
    const thead = el("thead");
    const header = el("tr");
    ["SELECT", "RUN / CONDITIONS", "SOURCE", "OUTCOME", "VERIFIER", "RECORDED COST", "STATUS"].forEach((label) => header.append(el("th", "", label)));
    thead.append(header);
    const tbody = el("tbody");
    state.history.forEach((run) => {
      const row = el("tr");
      const selectCell = el("td");
      const checkbox = el("input", "select-run");
      checkbox.type = "checkbox";
      checkbox.checked = state.selectedRuns.has(run.ref);
      checkbox.setAttribute("aria-label", `Select ${run.run_id} for comparison`);
      checkbox.addEventListener("change", () => {
        if (checkbox.checked) state.selectedRuns.add(run.ref); else state.selectedRuns.delete(run.ref);
        renderHistoryTable(data);
      });
      selectCell.append(checkbox);
      const identity = el("td");
      identity.append(button(run.run_id, "run-title-button", () => openDetail(run.ref)));
      identity.append(el("small", "", `${run.technique || "Technique not recorded"} · ${Object.values(run.models || {}).flat().join(" · ") || "models unrecorded"}`));
      const cases = el("div", "case-chips");
      (run.cases || []).slice(0, 4).forEach((name) => cases.append(el("span", "case-chip", name)));
      if ((run.cases || []).length > 4) cases.append(el("span", "case-chip", `+${run.cases.length - 4}`));
      identity.append(cases);
      const outcome = run.ground_truth_known ? el("span", "metric-inline", `${run.ground_truth_passed}/${run.ground_truth_known} · ${formatPercent(run.ground_truth_rate)}`) : el("span", "", "Unavailable");
      const verify = run.verification_comparable ? el("span", "metric-inline", `${run.verification_correct}/${run.verification_comparable}`) : el("span", "", "Unavailable");
      const cost = el("td", "metric-inline", formatCost(run.total_cost));
      const stateCell = el("td"); stateCell.append(tag(statusText(run.status), run.status));
      row.append(selectCell, identity, el("td", "", "").appendChild(sourceBadge(run.source)).parentElement, el("td", "", "").appendChild(outcome).parentElement, el("td", "", "").appendChild(verify).parentElement, cost, stateCell);
      tbody.append(row);
    });
    table.append(thead, tbody);
    host.append(table);
    renderSelectionBar(host);
    $("#history-truncated").hidden = !data.truncated;
    $("#history-truncated").textContent = data.truncated ? `Showing 500 of ${data.total_matches} matching structured runs. Filter to narrow the list.` : `${data.total_matches} structured run${data.total_matches === 1 ? "" : "s"} · missing Ground Truth and Verification results remain unavailable.`;
  }

  function renderSelectionBar(host) {
    if (!state.selectedRuns.size) return;
    const bar = el("div", "table-selection-bar");
    bar.append(el("strong", "", `${state.selectedRuns.size} run${state.selectedRuns.size === 1 ? "" : "s"} selected`));
    const actions = el("div", "selection-actions");
    actions.append(button("Clear", "text-button", () => { state.selectedRuns.clear(); renderHistoryTable({ total_matches: state.history.length }); }));
    const compare = button("Compare selected →", "button button-primary", () => {
      if (state.selectedRuns.size < 2 || state.selectedRuns.size > 8) { toast("Select between two and eight runs for comparison.", true); return; }
      location.hash = "compare";
    });
    actions.append(compare);
    bar.append(actions);
    host.append(bar);
  }

  async function openDetail(ref) {
    const box = $("#run-detail");
    box.hidden = false;
    box.replaceChildren(el("p", "muted", "Reading allowlisted run artifacts…"));
    try {
      const data = await api(`/api/history/${ref}`);
      renderDetail(data);
      box.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (error) {
      box.replaceChildren(el("p", "", error.message));
    }
  }

  function renderDetail(data) {
    const root = $("#run-detail");
    const run = data.run || {};
    root.replaceChildren();
    const heading = el("div", "detail-heading");
    const intro = el("div");
    intro.append(el("p", "eyebrow", `${run.source || "unknown"} source · ${run.archived ? "exploratory pack" : "structured run"}`), el("h2", "", run.run_id || "Recorded run"), el("p", "detail-meta", `${run.technique || "Technique unavailable"} · ${(run.cases || []).join(", ") || "No recorded case names"}`));
    heading.append(intro, button("×", "detail-close", () => { root.hidden = true; }));
    root.append(heading);
    const grid = el("div", "detail-grid");
    [["Ground Truth", run.ground_truth_known ? `${run.ground_truth_passed}/${run.ground_truth_known} · ${formatPercent(run.ground_truth_rate)}` : "Unavailable"], ["Verifier agreement", run.verification_comparable ? `${run.verification_correct}/${run.verification_comparable}` : "Unavailable"], ["Recorded cost", formatCost(run.total_cost)], ["Recorded duration", formatDuration(run.duration_s)]].forEach(([label, value]) => {
      const card = el("div", "detail-metric"); card.append(el("span", "", label), el("strong", "", value)); grid.append(card);
    });
    root.append(grid);
    if (data.cases?.length) {
      const table = el("table", "detail-table");
      const head = el("thead"); const hr = el("tr");
      ["CASE", "RUNNER", "GROUND TRUTH", "VERIFICATION", "TIME"].forEach((value) => hr.append(el("th", "", value)));
      head.append(hr);
      const body = el("tbody");
      data.cases.forEach((row) => {
        const tr = el("tr");
        tr.append(el("td", "", row.case), el("td", "", "").appendChild(tag(statusText(row.status), row.status)).parentElement, el("td", "", groundTruthOutcome(row)), el("td", "", row.verified === true ? "Verified" : row.verified === false ? "Not verified" : "Unavailable"), el("td", "", formatDuration(row.duration_s)));
        body.append(tr);
      });
      table.append(head, body);
      root.append(table);
    }
    const artifacts = (data.artifacts?.artifacts || []).filter((item) => item.data && Object.keys(item.data).length);
    if (artifacts.length) {
      const accordion = el("details", "artifact-accordion");
      const summary = el("summary", "", `Safe structured evidence · ${artifacts.length} artifacts`);
      const list = el("div", "artifact-list");
      artifacts.forEach((artifact) => {
        const card = el("details", "artifact-card");
        card.append(el("summary", "", artifact.kind));
        card.append(el("pre", "artifact-data", JSON.stringify(artifact.data, null, 2)));
        list.append(card);
      });
      accordion.append(summary, list);
      root.append(accordion);
    }
  }

  async function loadComparison() {
    const box = $("#comparison-results");
    const empty = $("#comparison-empty");
    const refs = [...state.selectedRuns];
    if (refs.length < 2) {
      empty.hidden = false;
      box.hidden = true;
      return;
    }
    empty.hidden = true;
    box.hidden = false;
    box.replaceChildren(el("p", "muted", "Comparing recorded run conditions…"));
    try {
      const data = await api("/api/compare", { method: "POST", body: { refs: refs.slice(0, 8) } });
      renderComparison(data);
    } catch (error) {
      box.replaceChildren(el("p", "", error.message));
    }
  }

  function renderComparison(data) {
    const root = $("#comparison-results");
    root.replaceChildren();
    const surface = el("article", "surface compare-card");
    surface.append(el("p", "compare-caution", data.caution));
    const cards = el("div", "comparison-runs");
    const maxCost = Math.max(1, ...data.runs.map((item) => item.run.total_cost || 0));
    const maxGt = Math.max(1, ...data.runs.map((item) => item.run.ground_truth_known || 0));
    data.runs.forEach(({ run, cases_in_common, cases_only_in_this_run }) => {
      const card = el("article", "comparison-run");
      card.append(el("span", "source-badge", run.source), el("h3", "", run.run_id || "Recorded run"), el("p", "run-meta", `${run.technique || "Technique unrecorded"} · ${Object.values(run.models || {}).flat().join(" · ") || "models unrecorded"}`));
      const bars = el("div", "comparison-bars");
      const gt = typeof run.ground_truth_rate === "number" ? `${formatPercent(run.ground_truth_rate)} · ${run.ground_truth_passed}/${run.ground_truth_known} known` : "Unavailable";
      bars.append(bar("Ground Truth success", gt, run.ground_truth_rate === null ? 0 : run.ground_truth_rate * 100));
      const verify = run.verification_comparable ? `${run.verification_correct}/${run.verification_comparable} comparable` : "Unavailable";
      const accuracy = run.verification_comparable ? run.verification_correct / run.verification_comparable * 100 : 0;
      bars.append(bar("Verifier agreement with Ground Truth", verify, accuracy, "verification"));
      bars.append(bar("Recorded cost", formatCost(run.total_cost), run.total_cost ? run.total_cost / maxCost * 100 : 0));
      bars.append(bar("Recorded cases", `${run.observed_cases} observed · ${run.planned_cases} planned`, run.observed_cases / maxGt * 100, "verification"));
      card.append(bars, el("p", "comparison-footnote", `${cases_in_common} cases shared · ${cases_only_in_this_run} only in this run · ${run.ground_truth_unavailable} outcome(s) unavailable.`));
      cards.append(card);
    });
    surface.append(cards);
    if (!data.aligned_case_sets) surface.append(el("p", "comparison-footnote", `The selected runs cover different cases. Common cases: ${(data.common_cases || []).join(", ") || "none"}.`));
    root.append(surface);
  }

  function bar(label, value, percent, modifier = "") {
    const outer = el("div", "comparison-bar-row");
    const heading = el("div", "bar-heading"); heading.append(el("span", "", label), el("strong", "", value));
    const track = el("div", "bar-track");
    const fill = el("progress", `bar-value ${modifier}`); fill.max = 100; fill.value = Math.max(0, Math.min(100, percent || 0));
    track.append(fill); outer.append(heading, track); return outer;
  }

  function renderEnvironment(result, launchStatus = null) {
    const report = result?.readiness || result;
    if (!report || !report.status) return;
    const status = report.status;
    const checkedAt = Date.parse(report.generated_at || "");
    const recent = Number.isFinite(checkedAt) && Date.now() - checkedAt >= 0 && Date.now() - checkedAt <= 20 * 60 * 1000;
    const fresh = status === "READY" && launchStatus === "READY" && recent;
    state.readiness = fresh ? { status: "READY", generated_at: report.generated_at } : status === "BLOCKED" && launchStatus === "BLOCKED" ? { status: "BLOCKED", generated_at: report.generated_at } : null;
    const current = launchStatus === status && (status !== "READY" || fresh);
    const pill = $("#environment-status-pill");
    pill.className = `status-tag ${statusTone(current ? status : "incomplete")}`;
    pill.textContent = current ? statusText(status) : "STALE CHECK";
    const checks = $("#environment-checks");
    checks.replaceChildren();
    (report.checks || []).forEach((check) => {
      const row = el("div", "environment-check");
      const dot = check.status === "pass" ? "dot-green" : check.status === "fail" ? "dot-red" : "dot-muted";
      row.append(el("span", `status-dot ${dot}`), el("span", "", check.label), el("small", "", check.status === "pass" ? "Passed" : check.status === "fail" ? check.blocking ? "BLOCKING" : "Needs attention" : "Skipped"));
      if (check.hint) row.append(el("span", "check-hint", check.hint));
      checks.append(row);
    });
    const repairs = result?.preparation || report.repairs || [];
    const box = $("#repair-results");
    if (repairs.length) {
      box.hidden = false;
      box.replaceChildren(el("strong", "", "Environment preparation"));
      repairs.forEach((repair) => {
        const line = el("div", "repair-row");
        line.append(el("span", "", repair.label || repair.name), tag(repair.status === "pass" ? "READY" : statusText(repair.status), repair.status));
        box.append(line);
      });
    } else {
      box.hidden = true;
    }
    $("#overview-readiness-title").textContent = fresh ? "Your selected lab is ready" : !current ? "Preflight needs a fresh check" : "Some environment checks need attention";
    $("#overview-readiness-text").textContent = fresh ? `Last checked ${formatDate(report.generated_at)}. Launches still pass through the canonical runner preflight.` : !current ? `The saved result does not match this app session or selected lane. Run preflight again before launching.` : "Review safe diagnostics or prepare the selected lane, then run preflight again.";
    $("#overview-readiness").classList.toggle("is-ready", fresh);
    $("#overview-readiness").classList.toggle("is-blocked", status === "BLOCKED" && current);
    updateLaunchGate();
  }

  function renderLaunchJobProgress() {
    const note = $("#readiness-launch-note");
    if (!note) return;
    const ready = state.readiness?.status === "READY";
    const tooLarge = Number.parseInt($("#attempt-count").textContent, 10) > 5000;
    note.classList.toggle("is-ready", ready && !tooLarge);
    note.classList.toggle("is-limit", tooLarge);
    note.replaceChildren(
      el("span", `status-dot ${tooLarge ? "dot-red" : ready ? "dot-green" : "dot-amber"}`),
      el("span", tooLarge ? "Reduce the campaign to 5,000 attempts or fewer." : ready ? "Preflight passed. Each case still gets canonical runner checks." : "A fresh preflight is required before a campaign can launch."),
    );
    const busy = state.jobs.some((job) => ["queued", "running", "stop_requested"].includes(job.status));
    $("#start-campaign").disabled = !ready || busy || tooLarge || !selectedCases().length || !selectedTechniques().length;
  }

  async function refreshJobs() {
    const data = await api("/api/jobs");
    state.jobs = data.jobs || [];
    renderJobs(state.jobs.slice(0, 5));
    renderJobBanner();
    renderLaunchJobProgress();
    schedulePolling();
  }

  function bindEvents() {
    window.addEventListener("hashchange", updateNavigation);
    $$("[data-page-link]").forEach((node) => node.addEventListener("click", (event) => {
      event.preventDefault();
      location.hash = node.dataset.pageLink;
    }));
    $("#sidebar-readiness").addEventListener("click", () => { location.hash = "environment"; });
    $("#run-readiness").addEventListener("click", () => runReadiness(false));
    $("#prepare-environment").addEventListener("click", () => runReadiness(true));
    $("#environment-check-button").addEventListener("click", () => runReadiness(false));
    $("#environment-prepare-button").addEventListener("click", () => runReadiness(true));
    $("#refresh-overview").addEventListener("click", loadOverview);
    $("#refresh-history").addEventListener("click", () => loadHistory(true));
    $("#case-search").addEventListener("input", renderCases);
    $("#select-visible-cases").addEventListener("click", () => {
      const search = $("#case-search").value.trim().toLowerCase();
      state.cases.filter((item) => item.id.toLowerCase().includes(search)).forEach((item) => state.selectedCases.add(item.id));
      renderCases();
      updateCampaignPreview();
    });
    $("#clear-cases").addEventListener("click", () => {
      state.selectedCases.clear();
      renderCases();
      updateCampaignPreview();
    });
    $$('input[name="technique"]').forEach((node) => node.addEventListener("change", updateCampaignPreview));
    ["#debug-models", "#api-model", "#verification-model", "#repetitions"].forEach((selector) => $(selector).addEventListener("input", updateCampaignPreview));
    $("#rep-minus").addEventListener("click", () => { const input = $("#repetitions"); input.value = String(Math.max(1, Number(input.value) - 1)); updateCampaignPreview(); });
    $("#rep-plus").addEventListener("click", () => { const input = $("#repetitions"); input.value = String(Math.min(500, Number(input.value) + 1)); updateCampaignPreview(); });
    $("#campaign-form").addEventListener("submit", (event) => {
      event.preventDefault();
      const payload = campaignPayload();
      if (!payload.cases.length || !payload.techniques.length) { toast("Choose at least one case and one technique.", true); return; }
      if (!state.readiness || state.readiness.status !== "READY") { toast("Run environment preflight before launching a campaign.", true); return; }
      openCampaignReview(payload);
    });
    $("#confirm-campaign").addEventListener("close", () => {
      if ($("#confirm-campaign").returnValue === "confirm") startCampaign(campaignPayload());
    });
    $("#publish-ack").addEventListener("change", () => {
      $("#confirm-publish").disabled = !state.publishPreview || !$("#publish-ack").checked;
    });
    $("#confirm-publish").addEventListener("click", publishReviewedCampaign);
    $("#cancel-publish").addEventListener("click", () => $("#publish-dialog").close());
    $("#history-search").addEventListener("input", () => {
      clearTimeout(state.searchTimer);
      state.searchTimer = setTimeout(() => { state.query = $("#history-search").value; loadHistory(); }, 220);
    });
    $$("[data-source]").forEach((node) => node.addEventListener("click", () => {
      state.source = node.dataset.source;
      $$("[data-source]").forEach((other) => other.classList.toggle("active", other === node));
      loadHistory();
    }));
    $("#logout-button").addEventListener("click", async () => {
      try { await api("/api/logout", { method: "POST", body: {} }); } catch { /* Clear local view even if the connection dropped. */ }
      clearInterval(state.pollTimer);
      showLogin("You have signed out.");
    });
    $("#login-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      const message = $("#login-message"); message.textContent = "";
      const submit = $("#login-form button[type=submit]"); submit.disabled = true;
      try {
        await api("/api/login", { method: "POST", body: { password: $("#password").value } });
        $("#password").value = "";
        showApp();
        await initializeApp();
      } catch (error) {
        message.textContent = error.message;
        $("#password").focus();
      } finally { submit.disabled = false; }
    });
  }

  async function initializeApp() {
    showApp();
    const current = new Intl.DateTimeFormat(undefined, { weekday: "short", month: "short", day: "numeric" }).format(new Date());
    $("#today-label").textContent = current.toUpperCase();
    bindEvents();
    updateNavigation();
    try {
      await refreshJobs();
      await loadOverview();
    } catch (error) { toast(error.message, true); }
  }

  async function boot() {
    try {
      const session = await api("/api/session");
      if (!session.configured) {
        showLogin("Initialize the private operator login with `make operator-ui-auth` on the server.");
      } else if (!session.authenticated) {
        showLogin();
      } else {
        await initializeApp();
      }
    } catch (error) { showLogin(error.message); }
  }

  bindEvents();
  boot();
})();
