# Motion implementation and fidelity

Motion is part of the design behavior. Preserve the observed trigger, sequence, timing, easing, loop, input response, and responsive layout where the target can support them. Choose implementation only after inspecting the source motion and its bundled assets. Apply capture and implementation inside the agreed build pass; this reference also supplies acceptance criteria for collaborative review without authorizing new work.

## Capture evidence

For a reference component, record:

- what moves and whether it is video, CSS/Web Animations, SVG/Lottie/Rive, canvas/WebGL, or a third-party embed (label uncertain source types as an inference);
- what starts or changes it: autoplay, hover, scroll, tab, hotspot, pointer, touch, or user input;
- an action sequence, expected delay, and visible checkpoints, including when the effect settles or loops;
- viewport, device/pointer mode, and any mobile transformation;
- keyboard/focus behavior and what changes with `prefers-reduced-motion`;
- archive and live results, including unrecorded network calls, missing assets, blank frames, timing variation, or cookie gates.

Use WACZ replay to preserve and exercise the original delivered client. Use screenshots and short recordings to show important frames and timing. A screenshot is one moment, a recording shows a sampled run, and a WACZ is an archive of observed page resources and responses; none claims an unseen backend state. Mark each result separately.

## Motion acceptance gate

For a motion-bearing reference, capture an unedited live-browser recording and preserve the delivered page as WACZ. Open that WACZ and repeat the original animation, timing, or trigger before labeling the behavior replay-tested. The storyboard/preview must let the reviewer play the source recording and open the corresponding replay. A still-only preview, a SingleFile snapshot, or an extracted media file does not pass as a recreation of the whole component. If an original archive or effect cannot be captured or replayed, show the best live evidence and mark the 1:1 motion result incomplete with the exact missing response, embed, control, or runtime behavior. Keep local package checks and the ReplayWeb receipt separate from replay behavior and visual comparison; invalid hashes/signatures or verifier disagreements remain unresolved rather than being reported as cryptographically verified.

## Build the closest supported behavior

Select the least complex tool that can reproduce the observed effect without changing it:

| Observed behavior | Suitable starting point |
| --- | --- |
| Small hover, focus, loading, or reveal transition | CSS or Web Animations API |
| React component transitions, gestures, drag, or layout changes | Motion for React |
| Sequenced timelines, coordinated scroll storytelling, pinned scenes | GSAP / ScrollTrigger |
| Existing authored vector/character animation | The supplied Rive or Lottie runtime |
| Camera, shader, particle, or realtime 3D scene | Three.js / React Three Fiber or the project's established WebGL stack |
| Photographic/3D loop supplied as media | The same video/image sequence with observed crop, timing, and overlays |

These are starting points, not interchangeable substitutes. Preserve the original media/artifact where available. Avoid rebuilding a proven effect from scratch when the delivered asset and its behavior can be used. Keep third-party analytics, trackers, and unrelated page scripts out of product code.

## Compare, then describe gaps

Implement the selected state and its context together: scale, crop, overlay, typography, spatial alignment, and transition. Compare at the same viewport and near the same elapsed time as the source. Test each key control and at least one mobile state. Use reduced motion to replace only continuous or nonessential movement with a calm state; keep essential state changes and information accessible. Confirm that pointer-only effects have keyboard/touch equivalents.

If a backend response, inaccessible media, performance limit, device API, or browser boundary prevents 1:1 behavior, preserve all other observable behavior and identify the exact difference. Show the strongest faithful approximation in the design room and label it. Bring back a material scope or quality tradeoff instead of silently substituting static content.
