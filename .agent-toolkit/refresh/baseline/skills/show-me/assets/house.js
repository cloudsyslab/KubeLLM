// show-me house behaviors, inlined into every layout by the artifact helper.
// Hooks: [data-theme-toggle] [data-predict] [data-steps] [data-toc] [data-spy]
// [data-copy-page] [data-hero] [data-nav-toggle]. Build on their events
// ("predict:reveal", "steps:change", "theme:change") instead of rewriting them.
(() => {
  const store = {
    get(key) { try { return localStorage.getItem(key); } catch { return null; } },
    set(key, value) { try { localStorage.setItem(key, value); } catch {} },
  };
  const root = document.documentElement;

  // Theme: dark unless the viewer chose light.
  if (store.get("show-me-theme") === "light") root.dataset.theme = "light";
  const toggles = [...document.querySelectorAll("[data-theme-toggle]")];
  const paintToggles = () => {
    const light = root.dataset.theme === "light";
    for (const button of toggles) {
      button.textContent = light ? "Dark" : "Light";
      button.setAttribute("aria-label", light ? "Switch to dark theme" : "Switch to light theme");
    }
  };
  paintToggles();
  for (const button of toggles) {
    button.addEventListener("click", () => {
      if (root.dataset.theme === "light") delete root.dataset.theme; else root.dataset.theme = "light";
      store.set("show-me-theme", root.dataset.theme ?? "dark");
      paintToggles();
      document.dispatchEvent(new CustomEvent("theme:change", { detail: { theme: root.dataset.theme ?? "dark" } }));
    });
  }

  // Predict, then reveal.
  for (const block of document.querySelectorAll("[data-predict]")) {
    const choices = [...block.querySelectorAll("[data-choice]")];
    const guess = block.querySelector("[data-guess]");
    const reveal = block.querySelector("[data-reveal]");
    const answer = block.querySelector("[data-answer]");
    const locked = block.dataset.unlocks ? [...document.querySelectorAll(block.dataset.unlocks)] : [];
    let picked = null;
    if (answer) answer.hidden = true;
    for (const element of locked) { element.classList.add("is-locked"); element.inert = true; }
    const ready = () => { if (reveal) reveal.disabled = !(picked || guess?.value.trim()); };
    for (const choice of choices) {
      choice.setAttribute("aria-pressed", "false");
      choice.addEventListener("click", () => {
        if (block.dataset.revealed) return;
        picked = choice;
        for (const other of choices) other.setAttribute("aria-pressed", String(other === choice));
        ready();
      });
    }
    guess?.addEventListener("input", () => { if (!block.dataset.revealed) ready(); });
    const open = (skipped) => {
      if (block.dataset.revealed) return;
      block.dataset.revealed = skipped ? "skipped" : "guessed";
      if (answer) answer.hidden = false;
      block.querySelector(".predict-actions")?.setAttribute("hidden", "");
      for (const choice of choices) {
        if (choice.hasAttribute("data-correct")) choice.classList.add("is-right");
        else if (choice === picked) choice.classList.add("is-wrong");
      }
      for (const element of locked) { element.classList.remove("is-locked"); element.inert = false; }
      block.dispatchEvent(new CustomEvent("predict:reveal", {
        bubbles: true,
        detail: { choice: picked?.dataset.choice ?? null, guess: guess?.value ?? "", skipped },
      }));
    };
    reveal?.addEventListener("click", () => open(false));
    block.querySelector("[data-skip]")?.addEventListener("click", () => open(true));
    ready();
  }

  // Step-through.
  for (const steps of document.querySelectorAll("[data-steps]")) {
    const items = [...steps.querySelectorAll("[data-step]")];
    const prev = steps.querySelector("[data-step-prev]");
    const next = steps.querySelector("[data-step-next]");
    const count = steps.querySelector("[data-step-count]");
    let index = 0;
    const show = (target, announce = true) => {
      index = Math.max(0, Math.min(items.length - 1, target));
      items.forEach((item, position) => { item.hidden = position !== index; });
      if (prev) prev.disabled = index === 0;
      if (next) next.disabled = index === items.length - 1;
      if (count) count.textContent = `${index + 1} / ${items.length}`;
      if (announce) steps.dispatchEvent(new CustomEvent("steps:change", { bubbles: true, detail: { index, step: items[index] } }));
    };
    prev?.addEventListener("click", () => show(index - 1));
    next?.addEventListener("click", () => show(index + 1));
    steps.addEventListener("keydown", (event) => {
      if (event.key === "ArrowRight") show(index + 1);
      if (event.key === "ArrowLeft") show(index - 1);
    });
    show(0, false);
    // Announce the first step after every module script on the page has run.
    requestAnimationFrame(() => show(0));
  }

  // "On this page": list the h2 headings inside the selector named by data-toc.
  const slug = (text) => text.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "section";
  for (const toc of document.querySelectorAll("[data-toc]")) {
    const scope = document.querySelector(toc.dataset.toc || "main");
    if (!scope) continue;
    for (const heading of scope.querySelectorAll("h2")) {
      if (!heading.id) heading.id = slug(heading.textContent);
      const link = document.createElement("a");
      link.href = `#${heading.id}`;
      link.textContent = heading.textContent;
      toc.append(link);
    }
  }

  // Scroll tracking: mark the nav and toc links for the section in view.
  const spyLinks = [...document.querySelectorAll("[data-spy] a[href^='#'], [data-toc] a[href^='#']")];
  const targets = [...new Set(spyLinks.map((link) => decodeURIComponent(link.getAttribute("href").slice(1))))]
    .map((id) => document.getElementById(id)).filter(Boolean)
    .sort((a, b) => (a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING ? -1 : 1));
  if (targets.length) {
    let current = null;
    const update = () => {
      const line = innerHeight * 0.3;
      let id = targets[0].id;
      for (const target of targets) if (target.getBoundingClientRect().top <= line) id = target.id;
      if (innerHeight + scrollY >= document.documentElement.scrollHeight - 2) id = targets[targets.length - 1].id;
      if (id === current) return;
      current = id;
      for (const link of spyLinks) {
        const on = link.getAttribute("href") === `#${id}`;
        link.classList.toggle("is-active", on);
        if (on) link.setAttribute("aria-current", "true"); else link.removeAttribute("aria-current");
      }
    };
    addEventListener("scroll", update, { passive: true });
    addEventListener("resize", update, { passive: true });
    update();
  }

  // Copy page: the readable text of the main content, as light Markdown.
  const asMarkdown = (scope) => {
    const lines = [];
    for (const node of scope.querySelectorAll("h1, h2, h3, p, li, pre, blockquote")) {
      if (node.closest("[hidden], .predict, nav, button")) continue;
      const text = node.innerText.trim();
      if (!text) continue;
      const tag = node.tagName;
      if (tag === "H1") lines.push(`# ${text}`);
      else if (tag === "H2") lines.push(`## ${text}`);
      else if (tag === "H3") lines.push(`### ${text}`);
      else if (tag === "LI") lines.push(`- ${text}`);
      else if (tag === "PRE") lines.push("```\n" + text + "\n```");
      else if (tag === "BLOCKQUOTE") lines.push(`> ${text}`);
      else if (!node.closest("li")) lines.push(text);
    }
    return lines.join("\n\n");
  };
  for (const button of document.querySelectorAll("[data-copy-page]")) {
    const label = button.textContent;
    button.addEventListener("click", async () => {
      const text = asMarkdown(document.querySelector(button.dataset.copyPage || "main") || document.body);
      let copied = false;
      try { await navigator.clipboard.writeText(text); copied = true; } catch {
        const area = Object.assign(document.createElement("textarea"), { value: text });
        area.style.position = "fixed"; area.style.opacity = "0";
        document.body.append(area); area.select();
        try { copied = document.execCommand("copy"); } catch {}
        area.remove();
      }
      button.textContent = copied ? "Copied" : "Copy failed";
      setTimeout(() => { button.textContent = label; }, 1600);
    });
  }

  // Hero art: a soft gradient field seeded by the page, so each artifact gets its own.
  const seedOf = (text) => { let hash = 2166136261; for (const char of text) { hash ^= char.codePointAt(0); hash = Math.imul(hash, 16777619); } return hash >>> 0; };
  const random = (seed) => () => {
    seed = (seed + 0x6d2b79f5) >>> 0;
    let t = seed;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  for (const art of document.querySelectorAll("[data-hero]")) {
    const next = random(seedOf(art.dataset.hero || document.title));
    const blob = (token) => {
      const width = 38 + next() * 34, height = 50 + next() * 45, x = next() * 100, y = next() * 100, strength = 62 + next() * 30;
      return `radial-gradient(${width.toFixed(1)}% ${height.toFixed(1)}% at ${x.toFixed(1)}% ${y.toFixed(1)}%, color-mix(in oklab, var(${token}) ${strength.toFixed(0)}%, transparent), transparent 72%)`;
    };
    const angle = Math.round(next() * 360);
    const light = `radial-gradient(${(30 + next() * 20).toFixed(1)}% ${(40 + next() * 25).toFixed(1)}% at ${(20 + next() * 60).toFixed(1)}% ${(15 + next() * 40).toFixed(1)}%, rgb(255 255 255 / 0.32), transparent 70%)`;
    const base = `linear-gradient(${angle}deg, color-mix(in oklab, var(--art-2) 70%, var(--surface)), color-mix(in oklab, var(--art-1) 75%, var(--surface)) 55%, color-mix(in oklab, var(--art-3) 60%, var(--surface)))`;
    art.style.background = [light, blob("--art-1"), blob("--art-3"), blob("--art-2"), base].join(", ");
  }

  // Territory: draw the map's branch tree from the sidebar nav named by data-territory.
  for (const figure of document.querySelectorAll("[data-territory]")) {
    const nav = document.querySelector(figure.dataset.territory);
    if (!nav) continue;
    const rootNode = document.createElement("div");
    rootNode.className = "tree-root";
    rootNode.innerHTML = `<span class="label">Topic</span><b></b>`;
    rootNode.querySelector("b").textContent = document.querySelector("h1")?.textContent ?? document.title;
    const list = document.createElement("ol");
    list.className = "tree-branches";
    let parent = null;
    for (const link of nav.querySelectorAll("a[href^='#']")) {
      const item = document.createElement("li");
      const node = document.createElement("a");
      node.className = "node";
      node.href = link.getAttribute("href");
      const status = link.querySelector(".status");
      if (status) node.append(status.cloneNode(true));
      if (status?.classList.contains("here")) node.classList.add("is-here");
      node.append(document.createTextNode([...link.childNodes].filter((child) => child.nodeType === Node.TEXT_NODE).map((child) => child.textContent).join("").trim()));
      item.append(node);
      if (link.classList.contains("sub") && parent) {
        let children = parent.querySelector(":scope > ol");
        if (!children) { children = document.createElement("ol"); parent.append(children); }
        children.append(item);
      } else {
        list.append(item);
        parent = item;
      }
    }
    const tree = document.createElement("div");
    tree.className = "tree";
    tree.append(rootNode, list);
    figure.prepend(tree);
  }

  // Phone navigation: the sidebar folds into a toggle.
  for (const toggle of document.querySelectorAll("[data-nav-toggle]")) {
    const sidebar = toggle.closest(".sidebar");
    toggle.setAttribute("aria-expanded", "false");
    toggle.addEventListener("click", () => {
      const open = !sidebar.classList.contains("is-open");
      sidebar.classList.toggle("is-open", open);
      toggle.setAttribute("aria-expanded", String(open));
    });
    sidebar.addEventListener("click", (event) => {
      if (event.target.closest("a") && sidebar.classList.contains("is-open")) toggle.click();
    });
  }
})();
