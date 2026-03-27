Perfect—this is where we turn it into something you can actually build from.

Below is a **full PRD + implementation skeleton** with:

* exact structure
* component breakdown
* content schema
* placeholders where you need to fill things in

No fluff—this is build-ready.

---

# 🧠 PRD — “MINH LE // INTERACTIVE DOSSIER” (v1.0)

## 1. 🎯 Product Definition

**Type:**
Interactive personal dossier (single-page application)

**Goal:**
Communicate:

* systems-level capability
* institutional credibility
* real-world impact

**Non-goals:**

* traditional resume site
* blog
* social feed

---

# 2. 🧩 INFORMATION ARCHITECTURE

```
ROOT
├── Hero / Identity Layer
├── Operational Profile
├── Experience Systems (core)
├── Systems Built (projects + research)
├── Artifact System (global + per-module)
└── Contact / Outbound
```

---

# 3. 🏠 HERO / IDENTITY LAYER

## Purpose

Immediate positioning + tone setting

## Component: `HeroSystem.tsx`

### Content Schema

```ts
{
  name: "Minh Le",
  title: "AI Systems | Cybersecurity | Infrastructure",
  tagline: "Designing and deploying systems across AI, cyber operations, and defense-backed environments",
  
  quick_links: [
    { label: "Resume", action: "download_pdf" },
    { label: "Contact", action: "scroll_contact" }
  ],

  socials: [
    { type: "linkedin", url: "" },
    { type: "instagram", url: "" }
  ]
}
```

### UI Behavior

* subtle text fade-in (no typing gimmick unless VERY clean)
* static, fast render
* no heavy animation

### TODO (you fill)

* [ ] Final tagline (this matters a lot)
* [ ] Social links

---

# 4. 🧬 OPERATIONAL PROFILE

## Purpose

Context layer (how you operate, not what you’ve done)

## Component: `OperationalProfile.tsx`

### Content Schema

```ts
{
  summary: "", // 2–3 lines max

  domains: [
    "AI Systems",
    "Cybersecurity",
    "Infrastructure"
  ],

  operating_style: [
    "Systems-level thinking",
    "Works in constrained / high-stakes environments",
    "Bridges research and production systems"
  ],

  military_context: {
    role: "ROTC / Military Intelligence Cadet",
    note: "", // how you phrase this matters
    clearance: "" // OPTIONAL — phrase carefully
  }
}
```

### UI Behavior

* clean text block
* subtle section divider
* no animation

### TODO

* [ ] Write 2–3 line summary (THIS IS CRITICAL)
* [ ] Decide how to phrase clearance (or omit)

---

# 5. 🔥 EXPERIENCE SYSTEMS (CORE)

## Purpose

Primary content engine (replaces resume)

## Component: `ExperienceMatrix.tsx`

Renders multiple:

```tsx
<ExperienceModule />
```

---

## Component: `ExperienceModule.tsx`

### Content Schema

```ts
{
  id: "mda",

  title: "Cybersecurity Engineering Intern",
  organization: "Missile Defense Agency",
  timeframe: "June 2025 – August 2025",

  accent_color: "orange", // used minimally

  summary: "", // 1–2 lines

  key_outcomes: [
    "Reduced ATO readiness time by ~90%",
    "Mapped 616 controls to NIST + DCSA",
    "Led 30+ consultations with defense contractors"
  ],

  systems_built: [
    "Host-based threat detection dashboard in Splunk",
    "Risk mitigation framework for THAAD eMASS"
  ],

  tech_stack: ["Splunk", "NIST", "Caldera", "ATT&CK"],

  affiliations: [
    { name: "MDA", logo: "" },
    { name: "MITRE", logo: "" }
  ],

  artifacts: [
    {
      type: "image",
      title: "Certification of Honor",
      file: "image_10.jpg",
      description: ""
    },
    {
      type: "image",
      title: "THAAD environment",
      file: "image_11.jpg"
    }
  ],

  validation: {
    quote: "Minh’s work ethic is truly remarkable...",
    source: "COL Holcombe, PEO",
    full_doc: "holcombe_letter.pdf"
  }
}
```

---

### UI Behavior

#### Default (collapsed)

* title + org + timeframe
* 1-line summary
* subtle accent border

#### Hover

* slight elevation
* accent color appears

#### Click

* expands into full module:

  * outcomes
  * systems built
  * tech stack
  * affiliations (logos appear)
  * artifacts list
  * quote block

---

### Subcomponent: `ArtifactReference.tsx`

#### Behavior

* shows:
  `Certification of Honor — image_10.jpg`

Hover:

* preview panel appears (right side)
* image fades in

Click:

* opens modal/drawer

---

### Subcomponent: `ValidationQuote.tsx`

#### Behavior

* shows excerpt
* shows source

Click:

* opens document viewer

---

### TODO (for EACH experience)

* [ ] Write 1-line summary (not generic)
* [ ] Refine outcomes into metrics
* [ ] Add artifacts (images/docs)
* [ ] Add 1 strong quote (optional but powerful)

---

# 6. 🧪 SYSTEMS BUILT (PROJECTS + RESEARCH)

## Component: `SystemsBuilt.tsx`

Renders:

```tsx
<SystemCard />
```

---

## Component: `SystemCard.tsx`

### Content Schema

```ts
{
  id: "kubellm",

  name: "KubeLLM",
  type: "Multi-agent AI system",

  summary: "",

  problem: "",
  solution: "",
  outcome: "",

  stack: ["Kubernetes", "Python", "Docker"],

  backing: [
    { name: "UTSA", logo: "" },
    { name: "DoE", logo: "" }
  ],

  artifacts: [
    { type: "image", title: "System diagram", file: "" }
  ]
}
```

---

### UI Behavior

* grid layout
* hover → highlight
* click → expand to:

  * problem / solution / outcome
  * diagram
  * stack
  * backing logos

---

### TODO

* [ ] Define problem clearly (no fluff)
* [ ] Add system diagram or visual
* [ ] Add backing institutions

---

# 7. 📂 ARTIFACT SYSTEM (GLOBAL LOGIC)

## Types

```ts
type Artifact =
  | { type: "image" }
  | { type: "document" }
  | { type: "quote" };
```

## Component: `ArtifactViewer.tsx`

### Modes

* preview (hover)
* modal (click)

---

### UI Rules

* dark background
* subtle grid overlay
* metadata:

  * source
  * date
  * context

---

### TODO

* [ ] Organize all assets:

  * images
  * certificates
  * rec letters
* [ ] Name them consistently

---

# 8. 🏢 LOGO SYSTEM

## Component: `AffiliationStrip.tsx`

### Rules

* grayscale default
* color on hover/expand
* small, aligned horizontally

---

### TODO

* [ ] Collect SVG logos (high quality)
* [ ] Normalize sizing

---

# 9. 📬 CONTACT / OUTBOUND

## Component: `ContactPanel.tsx`

### Content Schema

```ts
{
  email: "",
  linkedin: "",
  instagram: "",
  resume: "resume.pdf"
}
```

### UI

* minimal
* icons only + hover labels

---

### TODO

* [ ] finalize contact links
* [ ] upload resume PDF

---

# 10. 🎨 DESIGN SYSTEM

## Colors

```ts
base: black / charcoal
text: white / gray

accents:
- mda: orange/red
- mit_ll: blue
- utsa: muted green
- afterquery: violet/blue
```

## Typography

* headings: clean sans-serif
* system text: monospace (sparingly)

---

# 11. ⚙️ TECH STACK

## Required

* Next.js (App Router)
* Tailwind CSS
* Framer Motion

## Optional

* HeroUI (base components)
* Zustand (state if needed)

---

# 12. 🧱 FILE STRUCTURE

```
/app
/components
  /hero
  /profile
  /experience
  /systems
  /artifacts
  /ui
/data
  experiences.ts
  systems.ts
  artifacts.ts
/public
  /images
  /docs
```

---

# 13. 🚧 BUILD PHASES

## Phase 1 (ship fast)

* hero
* profile
* experience modules (no fancy animation)
* systems built
* artifact preview (basic)
* contact

## Phase 2

* improved artifact viewer
* quote/doc viewer
* accent color system
* logo polish

## Phase 3

* custom micro-animations per experience
* advanced interactions

---

# 14. 🔥 FINAL CHECKLIST

Before launch:

* [ ] Every experience has:

  * clear impact
  * at least 1 artifact
* [ ] No generic text anywhere
* [ ] No unused animations
* [ ] Logos are restrained
* [ ] Site loads fast (<2s)

---

# Next step

We now do one of two things:

### Option A (recommended)

👉 I help you **fill this out with your actual content**

* rewrite summaries
* extract best artifacts
* pick quotes
* structure each experience
