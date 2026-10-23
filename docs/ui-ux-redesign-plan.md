# TrustNet UI/UX redesign: implementation plan

Date: 20 October 2026. Status: proposed design and delivery plan; no production UI changes made. Scope includes every existing page, scan workspace, report, shared state and export. The recommendation is a substantial layout and interaction redesign, not a recolor.

Visual direction board: [TrustNet design direction](../outputs/ui-redesign/TrustNet-Design-Direction.svg). This is a layout/palette concept with system-font fallbacks, not a high-fidelity screen or a functioning dashboard.

## 1. Recommended direction

Create a calm evidence-review workspace with warm neutral surfaces, graphite typography, restrained pine-green actions and an orderly document-like layout. The product should feel useful for reviewing a suspicious message or photograph, with evidence and limitations easy to understand.

Light is the default recommended theme. Provide a fully designed neutral dark theme and a System option. Dark mode uses the same hierarchy and layout; it is not the old midnight/cyan design with different values. This is a product-direction recommendation, not a claim that light mode is universally better.

Use a compact TrustNet wordmark and a simple custom geometric mark derived from two overlapping document corners. Keep the AI descriptor in product copy where relevant. Replace the current shield favicon and repeated shield/sparkle branding. Status symbols remain familiar and functional.

Design rules:
- One primary action per section; use spacing, typography and alignment to establish priority.
- Broad quiet surfaces and thin dividers; reserve elevated surfaces for menus, dialogs and overlays.
- Use a table for history, a form for submission and a readable document for evidence. Do not turn every content block into an identical floating card.
- Use color to support labels, not to imply authenticity or correctness.
- Remove glow, neon cyan, animated radar/scanner ornaments, fake waveform decoration, excessive pills and repeating icon tiles.
- No invented charts, activity feeds, customer counts, confidence percentages or processing stages. Display only data supplied by real services.

## 2. Source audit

This is a fresh source and prior-report-design review, not a new complete live-browser audit of every page. Findings to capture in Phase 0:

| Finding | Evidence | Consequence |
|---|---|---|
| Theme is scattered | 704 hexadecimal color occurrences across 24 TSX/CSS files; 167 in `ReportView.tsx` alone at this audit | Replacing the global theme cannot reliably update the product |
| Conflicting visual foundations | `src/index.css` defines Tailwind theme tokens, parallel custom variables and another HSL token set | Several competing sources of visual truth |
| Headings and body lack a coherent type system | Global Times New Roman headings, Inter body and JetBrains Mono used broadly | Generic report styling and inconsistent hierarchy |
| Decoration dominates | Global glow shadows plus scanner/radar/floating/ping animations | Activity looks more important than evidence |
| Mobile navigation is incomplete | `Navbar.tsx` hides central navigation below `md` with no equivalent menu in that component | Important destinations disappear on small screens |
| All module tabs appear equally actionable | `ScanUploadView.tsx` displays six modalities, while only image, phishing and scam-message views are connected there | Availability is discovered after selection |
| Dashboard counts do not share result semantics | `DashboardView.tsx` groups scans using numeric 50 cutoffs | A high diagnostic image score can appear high-risk while its actual verdict requires review |
| Report information is crowded | General report contains score gauge, classifier, optional reasoning, forensic tools, telemetry and radar in one long surface | Users struggle to identify the result, evidence and next action |
| Navigation is component-state based | `App.tsx` uses `activeTab` rather than URL destinations | Refresh/back/deep-link behavior must be specified before changing the shell |
| Separate report families differ | `ReportView.tsx`, `PhishingReport.tsx`, `ScamResult.tsx` each own layouts and status presentation | A common shell and evidence primitives are needed without flattening their scientific differences |

The audit does not establish new model accuracy or module readiness. UI labels must reflect the current backend contracts.

## 3. Scope inventory

| Surface | Files currently owning it | Redesign scope |
|---|---|---|
| Public home | `views/LandingView.tsx` | Typographic introduction, available checks, honest capabilities, compact example workflow |
| Sign in / registration | `views/LoginView.tsx`, `RegisterView.tsx` | Single focused form, clear validation, password controls, loading/error/session states |
| Application shell | `App.tsx`, `components/Navbar.tsx` | Desktop navigation, mobile navigation, account menu, theme control, concise footer |
| Dashboard/history | `views/DashboardView.tsx` | Overview and history as one coherent screen, truthful summary counts, search/filter/sort, empty/error states |
| New check workspace | `views/ScanUploadView.tsx` | Available-module chooser and one focused task at a time |
| Image checks | `views/image/ImageScanView.tsx`, `components/image/*` | Upload, preview, file validation, actual progress, face scope and result handoff |
| Website checks | `views/phishing_url/PhishingScanView.tsx`, `components/phishing_url/*` | URL entry, preflight, quick vs optional live inspection, redirects, evidence and failures |
| Message checks | `views/scam_message/ScamMessageScanView.tsx`, `components/scam_message/*` | Message input, sender/context fields where supported, attribution, embedded-link actions and limitations |
| Image/general result | `views/ReportView.tsx`, gauge/radar/evidence components | Verdict-first reading order, region evidence, diagnostics disclosure, availability and provenance |
| Unavailable modalities | Audio, video, fake-review views | Consistent unavailable state; prevent dormant prototype screens from being mistaken for working inference |
| Shared states | `Skeleton.tsx`, forms, badges, alerts and menus | Loading, empty, error, partial, unsupported, busy, expired session and unavailable |
| Export/print | `services/pdfExporter.ts` | Paper-first report, matching vocabulary, readable tables, real hashes/statuses and reliable page breaks |

Paths in this table are relative to `frontend/src/`. There is no separate admin or analyst-role dashboard in the inspected `App.tsx`; do not invent roles or new backend products as part of this redesign. All existing modality/result surfaces are included.

## 4. Theme specification

Use semantic tokens with one source of truth. The following is the proposed palette, subject to complete component-state contrast testing.

| Token | Light | Dark | Role |
|---|---|---|---|
| Canvas | `#F5F4F0` | `#171C1A` | Main application background |
| Surface | `#FFFFFF` | `#202723` | Forms, tables and report sheets |
| Subtle surface | `#EEEDE8` | `#2A322E` | Selected groups and secondary regions |
| Primary text | `#222824` | `#EDF1EB` | Headings and body |
| Secondary text | `#5F6963` | `#A8B4AA` | Descriptions and supporting metadata |
| Decorative divider | `#D4D8D2` | `#3B4740` | Nonessential separators |
| Control boundary | `#7D8981` | `#6E7E73` | Inputs and essential outlined controls |
| Brand/action | `#28574E` | `#9CC8B6` | Primary controls and focus accents |
| On-action text | `#FFFFFF` | `#132A20` | Primary button text |
| Hover action | `#1F443D` | `#B6D8C9` | Interactive hover |

Status backgrounds are small, quiet regions; do not wash entire screens in red or green.

| Meaning | Light text / surface | Label treatment |
|---|---|---|
| Review / incomplete assessment | `#805D15` / `#FBF2DC` | Review required; include reason |
| Elevated warning | `#A13E35` / `#FBECEA` | Specific warning, never unsupported certainty |
| Lower detected signal | `#2F6550` / `#EAF2EC` | Low signal; never “verified safe” |
| Unavailable / unsupported | `#59646B` / `#EEF0F2` | Unavailable or unsupported; never numeric zero |
| Neutral information | `#3C5C7D` / `#EAF0F7` | Informational state with descriptive text |

Design matching dark semantic tokens during Phase 1; do not reuse light pastel backgrounds blindly. Brand color and low-signal color have different semantic token names even where related visually.

Calculated contrast for these specific pairs: light body/surface 15.03:1; light secondary/canvas 5.17:1; primary button 8.19:1; light review 5.39:1; warning 5.62:1; low-signal 5.94:1; unavailable 5.31:1. Dark body/surface 13.36:1, secondary/surface 7.10:1 and primary button 8.23:1. Control boundaries are 3.64:1 light and 3.56:1 dark against their surfaces. These calculations do not certify full-page accessibility; opacity, hover, focus, disabled states and overlays require separate tests.

## 5. Typography

Use **IBM Plex Sans** for application text and **IBM Plex Mono** only for technical identifiers, hashes and evidence excerpts where fixed-width alignment helps. Ordinary numbers use tabular numerals in the sans family. Do not make every metric monospaced or every label uppercase. IBM publishes these families under the Open Font License and documents their UI use: https://github.com/IBM/plex .

| Role | Desktop | Mobile | Weight / line height |
|---|---|---|---|
| Public introduction | 44px | 32px | 500 / 1.12 |
| Page title | 30px | 26px | 600 / 1.2 |
| Section title | 20px | 20px | 600 / 1.35 |
| Body / explanations | 16px | 16px | 400 / 1.5–1.6 |
| Controls / table rows | 14px | 14–16px | 400–500 / 1.45 |
| Secondary metadata | 13px | 13px | 400 / 1.45 |
| IDs / hashes | 12–13px | 12–13px | Mono 400; wrap or copy without truncating stored data |

Self-host only the needed WOFF2 files and preserve licenses. Start with 400/500/600 sans and 400 mono, `font-display: swap` and tested system fallbacks. Add the appropriate Plex script package/fallback only where actual message content needs it; Latin fonts alone do not guarantee Hindi or mixed-script support. Verify combining marks, emoji, Unicode domains and attribution offsets. Re-measure layout and PDF line breaks after font changes. PDF font embedding is a separate step from CSS loading.

## 6. Icons and identity

Keep one icon family. Retain the installed Lucide package but replace the selection, sizing and presentation across the product. Switching libraries alone would not change the design quality.

| Use | Proposed symbol |
|---|---|
| Overview | LayoutDashboard |
| New check | Plus |
| History | History |
| Photo | Image |
| Website | Link |
| Message | MessageSquareText |
| Video / audio | Video / AudioLines, only on availability-labelled surfaces |
| Report | FileText |
| Review | CircleHelp |
| Warning | TriangleAlert |
| Unavailable | CircleMinus |
| Copy / download | Copy / Download |

Use a consistent 20px navigation size, 18px action size, 16px inline status size and roughly 1.75px stroke. Avoid colorful square containers around every icon. New custom branding remains separate from interface symbols. Every icon-only control needs an accessible name and a comfortably sized target; visible labels remain preferred. Lucide's guidance explicitly recommends text labels and non-color state cues: https://lucide.dev/how-to/accessibility .

## 7. Layout and interaction system

### Shell

Desktop: 224px quiet left navigation, a 64px contextual header, 32px main gutters and a workspace capped around 1360px. Use a fluid minimum width and a separate readable report column of approximately 760px with an optional 280–320px evidence/source rail. Navigation includes Overview and New check; History is a section/filter destination inside the overview screen initially, not a duplicate dashboard. Account and appearance controls live at the lower navigation edge.

Tablet: compact navigation or an accessible drawer when the content no longer fits. Mobile: 56px top bar, clearly labelled menu, 16px gutters and full-width primary actions. Do not hide navigation with no replacement. Drawer focus returns to its trigger and Escape closes overlays.

Use spacing steps 4/8/12/16/24/32/48/64px. Inputs/buttons are normally 44px high. Use 6px control radius, 8px panel radius and 12px dialog radius. Pill shapes are reserved for compact status chips where useful. Use flat surfaces and 1px separators; shadows only indicate elevation. No scaling cards on hover.

### Overview and history

Lead with “Your checks” and a clear “New check” action. Use a restrained summary strip for Completed, Needs review and Unavailable/failed rather than three oversized colored cards. Include source-count language when only a limited history window has loaded; do not imply a complete global total.

Derive counts from the same semantic result adapter used by the reports. Do not classify an unvalidated image score of 91 as confirmed threat merely because it exceeds 50. Keep state counts mutually understood and test their definitions with success, partial, review, unsupported and failed cases.

History uses a calm table with Item, Check type, Result, Checked at and Open. Place search, status/type filters and sorting in one toolbar. Preserve filter selections when opening and returning from a report. Handle long filenames/URLs, keyboard row actions and empty filtered results. At narrow widths, convert to labelled list rows with the same essential information. Pagination must reflect the real API; do not add fake totals or claim server-side filtering that does not exist.

### New check

Show Photos, Website links and Messages as the current connected choices, with their coverage caveats. Group video/audio/review-batch under “Not available yet” rather than treating every modality as an active tool. Existing unsupported history remains readable.

Use a left-aligned heading and one focused form. Photo: upload/drop target, browse fallback, file preview, validation and remove/replace. Website: URL field, normalized URL review and distinct optional live-inspection action. Message: readable text area, only supported context fields, clear length/coverage feedback and a real example only if labelled illustrative. Preserve values after validation errors and prevent duplicate submissions. Do not add URLs as automatic live visits.

Show real processing states such as submitting/waiting/complete when supported. Do not simulate percentages or stages such as “verifying physics.” Busy, timeout, partial completion and expired-session states each need a next action.

### Reports

Reading order: **result → what was assessed → supporting evidence → limitations → next action**. Use a compact textual verdict with an explanation and timestamp. Put the score beside its definition in secondary content; remove the oversized circular gauge as the main sign of trust. A high fake score and review-required verdict must be understandable without reading telemetry.

Use three sections or accessible tabs: Summary, Evidence and Technical details. The initial summary always includes important coverage limitations; do not hide unavailable-model or unsupported-scope information behind a disclosure.

- Image: source preview when available; face-region list; face scores; frame diagnostic clearly secondary; model/policy availability. Provide a useful re-upload state when originals were not retained.
- Website: normalized address, result, redirects and available domain/page observations. Distinguish URL-model screening from optional page inspection. Preserve suspicious links as controlled actions, not accidental navigation targets.
- Message: original text with evidence markers, a plain-language explanation, separate message and URL results, and optional link inspection. Use a labelled evidence legend; do not make color the only distinction between support/counterevidence/context.
- All reports: copy/export actions in one toolbar; completion feedback; source/model identity in details; accurate partial/failed/skipped states. Preserve existing scientific qualifications and input hashes.

Charts appear only for meaningful comparable data. Replace the decorative radar with named measurements or a compact evidence table unless a documented chart question justifies it. Missing observations have an unavailable state, not a fabricated baseline. Technical labels and diagnostics belong in details.

### Public home and authentication

Home uses a clear proposition, a useful “Start a check” action, available tools and a short explanation of limitations. Keep the public page visually related to the app, with more whitespace and editorial pacing. Remove invented enterprise language, badges and broad authenticity promises.

Auth pages use a single 400–440px form column, visible labels, inline errors, password reveal controls and stable loading states. Do not add password-reset, social sign-in or account features without an existing working backend contract. Preserve keyboard, browser autofill and password-manager behavior.

## 8. Accessibility, motion and responsive rules

Target WCAG 2.2 AA: normal text contrast at least 4.5:1, large text at least 3:1, and applicable non-text control contrast at least 3:1. Use 44px control targets as the project's default, while documenting exceptions rather than misrepresenting this as the WCAG AA minimum. Reference: https://www.w3.org/WAI/WCAG22/quickref/ .

Provide visible focus, proper form labels, linked error text, semantic headings, real buttons/links and keyboard-complete menus/dialogs/tabs. Announce asynchronous errors and status changes without repeatedly interrupting screen-reader users. Test at 200% zoom, narrow reflow, high contrast/forced colors and reduced motion. Add a skip link and avoid sticky elements obscuring focused content.

Motion is limited to 120–180ms opacity/color changes and purposeful loading feedback. Respect `prefers-reduced-motion`. Avoid infinite decorative movement and large staggered entrance animations.

Test widths 320, 375, 768, 1024, 1440 and 1920px. No body-level horizontal overflow; a genuinely wide evidence table may use a clearly labelled local scroll region. Long URLs, mixed-script messages, empty history, 1000 loaded rows and large error descriptions are required stress cases. Test actual mobile hardware separately before claiming device coverage.

## 9. Component and code approach

Keep the existing React/Tailwind stack. Start with a small set of reusable components, adding a headless primitive only when a real keyboard/focus requirement justifies it. Avoid a broad UI-library migration or backend rewrite.

Proposed ownership:
- `src/styles/tokens.css`: light/dark semantic color, typography, spacing, radius and elevation tokens. Map Tailwind theme names to these tokens.
- `src/styles/base.css`: typography, focus, form defaults and reduced-motion rules.
- `src/components/ui/`: Button, IconButton, Field, Input, Textarea, Select, StatusBadge, Alert, EmptyState, Tabs, Dialog/Drawer and table primitives as needed.
- `src/components/layout/`: public shell, workspace shell, contextual header and responsive navigation.
- `src/components/reports/`: result header, evidence section/list, metadata row and action toolbar. Domain result adapters continue to own scientific meaning.
- `src/services/assessmentPresentation.ts`: shared display/status mapping built on existing verdict helpers, including history summaries. Do not change detector outputs merely to match a visual design.

Remove old hardcoded theme literals as each surface migrates. Do not add a competing root style sheet and leave dark hex values inside page components. Keep legitimate chart/heatmap/image colors separate from UI chrome; a mechanical hex-to-token replacement would damage forensic visualization.

Specify URL behavior during shell work. Recommended destinations are home, sign-in, register, checks, new check and a selected report. Verify deep-link reloads and history ownership before exposing routes; do not introduce new endpoints to obtain them. Use browser history or a small router only after verifying current service fetch capabilities. Preserve auth, scan IDs, session handling and back navigation.

## 10. Phases and exit gates

### Phase 0 — Baseline and semantic inventory

Capture existing desktop/mobile screens, keyboard paths and all form/result states. Record route ownership, API contracts, current build/lint and report assertions. List active vs unavailable modules. Map dashboard counts to semantic statuses. Separate unrelated worktree changes before touching components.

**Deliverable:** screen/state matrix and baseline screenshots. **Gate:** every existing destination and important failure state is accounted for; no new backend feature is assumed.

### Phase 1 — Concrete visual specification

Produce high-fidelity desktop overview, new-photo-check and image-result concepts, plus mobile versions and dark equivalents. Define the logo/icon treatment, final palette, font files, density, semantic states and focus behavior. Include the actual image example with high face score/review-required, an unsupported image, a phishing warning and partial message coverage.

**Deliverable:** reviewable screen designs and component-state sheet. **Gate:** layout, hierarchy, light/dark appearance and truthfulness are demonstrable before migrating every page. Review the proposed direction at this concrete stage; do not ask the user to approve an abstract color list.

### Phase 2 — Theme and core components

Create tokens and self-hosted typography; replace old global heading/glow rules; implement controls, notices, status badges, skeletons and appearance persistence. Default to light unless a stored preference exists; support explicit System/Light/Dark and avoid a flash of the wrong theme. Include disabled/hover/focus/loading/error states.

**Gate:** a component gallery works in both themes, keyboard and reduced-motion checks pass, font loading is verified, and build/lint pass. Record actual font transfer cost; initial target is under 200KB for the initial Latin UI font payload, to be confirmed rather than claimed.

### Phase 3 — Shared shell and navigation

Implement public/application shells, responsive navigation, account/actions and the specified URL/back behavior. Keep the footer compact inside the application. Verify session restoration and logout clear private state. Keep key destinations available on mobile.

**Gate:** every destination remains reachable by keyboard and at all target widths; refresh/back/auth transitions function; no content is obscured or horizontally clipped. Run build/lint and browser navigation smoke checks.

### Phase 4 — Overview and complete submission flows

Migrate history and its semantic summary adapter, search/filters, empty/loading/error states. Then migrate image, website and message forms to the shared system. Implement honest unavailable surfaces for video/audio/fake reviews and reconcile dormant components so old styles cannot reappear through a future import.

**Gate:** representative real submissions reach their correct reports; validation, retry, busy, timeout and session errors remain understandable; history counts match report statuses. Build/lint, existing API-contract checks and browser smoke tests pass after each migrated flow.

### Phase 5 — Every report and evidence workflow

Migrate image/general, phishing and message reports. Reorganize hierarchy and progressive disclosure; replace dominant gauges and decorative charts. Preserve evidence offsets, copy/download/listen behavior where supported, region details, embedded-link controls and coverage warnings. Never expose unsafe links through a generic clickable row.

**Gate:** same input result yields the same semantic meaning in summary, history and detailed report. High-score/review-required and unavailable/no-score cases are mandatory acceptance examples. Verify every retained action and browser interaction before continuing.

### Phase 6 — Public pages, auth and PDF/print

Apply the same identity to home, sign-in and registration. Update favicon/title and remove overstated public copy. Redesign PDF/print as a readable light document independent of selected app theme. Verify font embedding, Unicode, real input digest, statuses, long evidence and page boundaries.

**Gate:** auth/autofill/session flows work; public capabilities match actual availability; PDF text assertions and visual rendering pass; no clipped tables or lost limitations. Build/lint and relevant regression tests pass.

### Phase 7 — Whole-product QA and controlled completion

Test all themes and states with representative real results plus explicitly marked deterministic fixtures for rare errors. Run keyboard/screen-reader checks, automated accessibility checks and manual contrast review. Test requested widths, 200% zoom, long content and reduced motion. Compare performance with baseline; investigate regressions rather than adding blanket animation or dependency changes.

Remove unused old theme variables, ornament animations and duplicate components only after migration is complete. Keep data visualizations whose measured purpose remains valid. Preserve version-control rollback and do not mix model training or detection-policy changes into the design release.

**Gate:** no reachable screen uses the old chrome; no contradictory status/score language; all current functionality and security boundaries remain intact; build/lint, relevant report/assessment tests and full browser smoke matrix pass. Release notes distinguish desktop synthetic coverage from actual-device testing.

## 11. Completion checklist

- One light/dark token system, two font families and one consistent interface icon family.
- Every public, auth, dashboard, scan, result, unavailable and shared state is covered.
- Desktop/tablet/mobile navigation remains usable; no hidden-only navigation pattern.
- Status, score, uncertainty and coverage meanings survive the redesign unchanged.
- History totals and result groupings are truthful for the loaded data.
- No dummy charts, fabricated metrics, fake progress, unsupported promises or decorative trust signals.
- No scan text, uploaded image or URL leaves the existing inference/privacy boundaries because of the redesign.
- All product actions retain their real behavior; unavailable functionality stays visibly unavailable.
- Exports are legible and consistent without relying on app background colors.
- Final browser and accessibility evidence is captured after each phase, not postponed to the end.

## 12. Recommended execution order

Baseline → concrete overview/check/report designs → tokens/components → responsive shell → history and connected submission flows → all report families → public/auth/export surfaces → whole-product QA and cleanup.

Start implementation with the representative overview, new check and image-report slice after the visual specification is concrete. That slice establishes the design system while exercising the difficult uncertainty/coverage cases. Extend the proven components across the remaining surfaces; do not redesign each dashboard independently.
