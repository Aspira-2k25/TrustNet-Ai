# Editorial revision — 20 October 2026

The user selected an editorial direction after reviewing the initial redesign. This revision supersedes its ivory/pine visual direction.

## Design decisions

- Newsreader for the wordmark, page titles and home tool headings; IBM Plex Sans for controls, body text and evidence. The expressive type carries identity without reducing data readability.
- Paper, ink and rust replace the previous green palette. Status colours retain their separate meanings.
- An asymmetric introduction and a ruled index replace the slogan-led hero and generic feature blocks. Each row leads to an actual image, website or message check.
- Shorter interface copy, fewer repeated taglines, a smaller workspace header and sharper panel edges reduce visual noise.
- Forms, scores, verdicts and backend APIs retain their existing behaviour. No detection or accuracy changes were made in this revision.

## Verified

Production build, lint, status presentation regression checks and whitespace checks passed. Sixty automated browser combinations passed: home, guest dashboard, new check, login and registration at 320/375/768/1024/1440/1920px, in light and dark themes. Each had a rendered heading, no horizontal overflow, no runner error and no reported axe WCAG-tag violation. The initial low-contrast summary label was corrected and the full matrix rerun.

These are synthetic browser checks, not actual-device or screen-reader certification. Populated backend flows and report fixtures were not rerun in this revision. Earlier report checks remain historical evidence; no new backend accuracy claim is made. The existing lazy PDF bundle-size warning remains.

Raw results: `runtime_state/ui-redesign/editorial-accessibility.json`. The production preview and temporary QA assets were removed after testing. Newsreader is self-hosted; its license is included in `frontend/public/newsreader-OFL.txt`.

Previews: `TrustNet-Editorial-Home.png`, `TrustNet-Editorial-Workspace.png`, `TrustNet-Editorial-Scan-Dark.png` in this folder. Earlier screenshots show the previous design.
