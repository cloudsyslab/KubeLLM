---
name: publish-github
description: Prepare a side project for GitHub by polishing its product presentation, visual identity, documentation, and repository hygiene, then stage it privately. Use when the user wants to make a project clean and ready to publish; keep it private until they explicitly approve public visibility.
---

# Publish to GitHub

Turn a scrappy project into a coherent, usable, well-presented GitHub repository. Learn what the project actually does, make a focused set of improvements to its first-run experience and presentation, reconcile its docs, audit repository hygiene, and stage the result in a private GitHub repository. Finish by showing the user the concrete result and ask for explicit approval before making the repository public.

## Scope and authority

- The user's explicit `$publish-github` invocation authorizes local product and presentation polish, project-appropriate commits, and pushing the approved publication work to a confirmed private GitHub destination. Discover the owner from the configured GitHub account and the repository name from its remote or project metadata. Ask only when identity, ownership, or an important product choice cannot be established.
- Keep the GitHub repository private throughout preparation. If an existing destination is public, make it private before pushing publication changes when the authenticated account permits it. Explain any visibility consequence the user must know. Do not create a public mirror, enable public Pages, publish release assets/packages, or expose generated artifacts elsewhere.
- Public visibility is a separate user decision. At the end, show the repo URL, final presentation, validation, files/commits staged, and remaining issues. Ask the user to explicitly approve making that exact repository public. Do not infer approval from “looks good,” approval to stage privately, or approval of code changes. After approval, make only that repository public and verify the resulting visibility.
- Preserve existing history and unrelated user work. Do not force-push, rewrite history, delete branches/releases/tags, or alter unrelated repositories. If the destination or working-tree state makes a safe publication push unclear, prepare what is safe and report the blocker.
- Keep the work focused on making the existing project understandable, credible, usable, and maintainable. Make bounded fixes and first-run improvements. Bring new features, major redesigns, architectural changes, ownership changes, and other decisions that would change the product's promise back to the user before implementing them.

## Understand the project

Inspect repository instructions, status and history, source code, tests, build/install/run commands, existing docs and assets, licenses and attributions, CI, ignore rules, and current GitHub remotes/settings. Run the project as appropriate to understand the actual first-use path. Base public claims on code and observed behavior; preserve meaningful limitations and distinguish verified behavior from plans.

Choose improvements that solve visible problems in the actual project. Depending on what it needs, that can include:

- a clear name, visual direction, logo, app icon, favicon, social preview, or other project artwork;
- real screenshots, a short demo, a representative example, or an accurate before/after presentation;
- a README that explains the user problem, capabilities, requirements, setup, use, examples, troubleshooting, limitations, and contribution path;
- focused onboarding, interface, accessibility, error handling, and small usability fixes that make the first experience more polished;
- current documentation, examples, links, metadata, versioning, and repository indexes;
- an appropriate `.gitignore`, editor conventions, CI checks, contributor or security guidance, and cleanup of generated, duplicated, or misleading repository files.

Do not add every possible badge, policy, template, workflow, screenshot, or guide. Include an item when it improves this project's first impression, safe use, or maintenance.

## Design and implementation

- Inspect the live product before drawing conclusions about its visual quality. For web UI, use the repository's design system and the available sidebar browser workflow for rendered review. For native apps, inspect the real app or its established previews. Do not present mockups as screenshots of working software.
- Create visual assets that fit the product's real name and audience. When available, use `$imagegen` for original raster artwork; create vector or native assets with the project's own conventions when that produces a more useful logo or icon. Check assets at their actual sizes, include accessible descriptions where appropriate, and avoid unlicensed third-party artwork or confusing resemblance to existing brands.
- Keep screenshots and demos faithful to the checked-in product. Use synthetic examples only when clearly labeled. Remove personal data, credentials, private URLs, and machine-specific paths from media, logs, and sample files.
- Refresh documentation to match the actual implementation and this completed polish pass. Follow `$refresh-docs` principles: preserve approved requirements, remove truly obsolete material only after retaining durable decisions, fix incoming links, and label unknowns. This publication workflow includes a broad docs and repository-readiness review; a separate `$refresh-docs` run is optional when the user wants a docs-only pass.
- Preserve existing license and attribution terms. Never invent a license or make a third-party component appear original. If no license exists, explain that public source visibility does not grant reuse rights by itself. Resolve the user's separate choice to add a named license or publish without one before asking for public-visibility approval; a yes to making the repository public does not choose a license. If the user chooses a license, add its authoritative text and matching metadata, commit and push that change to the still-private repo, rerun relevant checks, and show the updated state before asking for public approval.

## Hygiene and private staging

Before any push, inspect the complete changed-file set and relevant history for secrets, credentials, personal data, local state, build outputs, large accidental files, and private or copyrighted material. Use available secret scanners and repository checks where present. A private GitHub repository is still an external upload: if secrets appear in the history, stop the push, explain the affected paths without repeating the values, and recommend revocation and history cleanup. Do not silently rewrite history or upload sensitive content because the destination is private.

Check that documented commands work, links and asset paths resolve, builds/tests that support the public claims pass, and generated outputs are intentional. Do not claim a screenshot, test, build, accessibility check, or feature works unless it was observed. Record unavailable checks and limitations.

If no GitHub repository exists and the account and name are clear, create it as private without auto-generating conflicting starter files, then add the appropriate remote and push the prepared work. For an existing repository, verify owner, destination, branch, and private visibility before pushing. Commit only publication work that belongs in this pass; keep unrelated local edits and user changes out of the push. Never bypass organization policy or authentication requirements.

## Public approval and finish

When the private staging is ready, report the private repository link, actual branch and commit state, notable product/brand/docs/hygiene changes, validation performed, unresolved decisions, and anything excluded. Resolve any remaining licensing or product decisions first. If that resolution changes the repository, validate, push it privately, and show the updated state. Then ask one direct question whose approval is explicit, for example: “May I make `owner/repository` public now?”

Only after a clear yes, change that repository's visibility to public and verify GitHub reports it as public. If the account cannot change visibility or a confirmation step is required, stop at that step and tell the user exactly what remains. Never publish packages, binaries, a website, or a GitHub release unless the user requested that distribution separately.

Finish with the repository URL and visibility, branch/commit pushed, validation results, and any important follow-up work.
