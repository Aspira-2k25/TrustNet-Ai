# TrustNet interface redesign — implementation and verification

Completed locally on 20 October 2026. This records the UI implementation, not a production release or detector accuracy evaluation.

## Delivered

- Shared warm ivory/pine light theme, neutral dark theme and system appearance; persistent preference; self-hosted IBM Plex Sans/Mono with licenses.
- Workspace sidebar, mobile dialog navigation, public navigation, keyboard focus and consistent icons, controls and status badges.
- Landing, sign-in, registration, history/dashboard, image, website and message submission pages. Video/audio/review-batch routes explicitly explain unavailability.
- Search, result/type filters, sorting, pagination and honest loading/error/empty states. History grouping follows verdict and availability, never an arbitrary score cutoff.
- Evidence-first image, phishing and message reports, preserving existing data, source offsets, privacy disclosures and limitations. Screening score, prediction confidence and assessment coverage remain distinct.
- Paper PDF layout with embedded Plex fonts, page numbers and retained evidence/limitations. Unsupported font glyphs use reversible Unicode escapes with an explicit disclosure; original Unicode remains available on the website.
- Removed decorative gauges/radar from primary reports and simulated scan progress from dormant modalities. Existing backend/model changes were preserved.

## Verification

| Check | Result |
| --- | --- |
| Production frontend build | Pass |
| Frontend lint | Pass |
| UI presentation regression checks | Pass: review-required, unavailable, mixed-case and queued results |
| Image assessment checks | Pass: face/frame disagreement and unavailable scores |
| Image PDF contract checks using prior real portrait response | Pass |
| Phishing report checks | Pass: domain alignment, Unicode, evidence and uncertainty |
| Git whitespace check | Pass |
| Browser layout + axe WCAG-tag checks | 108 combinations: 9 screens × 6 widths × 2 themes; zero reported violations, runner errors or horizontal overflow |
| Manual browser checks | Theme persistence, navigation/back/refresh, password reveal, required-field validation, unavailable tools, message input, technical/evidence navigation, saved image missing-original state |
| PDF visual inspection | All 3 pages of actual portrait-result export inspected |

Browser matrix widths: 320, 375, 768, 1024, 1440 and 1920px. The widths were simulated with same-origin browser frames. The screens were home, guest dashboard, new check, sign-in, registration, image report, populated history fixture, website report fixture and message report fixture. Fixture pages carried a visible test label and did not submit data or create history. Axe was run after fonts and theme transitions settled. This is automated coverage, not accessibility certification or a screen-reader audit.

Raw matrix results are in `runtime_state/ui-redesign/layout-accessibility-light.json` and `layout-accessibility-dark.json`. Saved previews are beside this document. The temporary QA pages and preview server were removed/stopped after verification.

## Remaining release checks and limits

- Full signed-in authentication/session/submission flows against the complete running backend were not exercised in this UI pass. Existing API paths were retained; frontend fixtures do not prove backend integration.
- Actual phones/tablets, assistive technology, browser zoom, system color-scheme changes and clipboard/speech/download permissions still need release testing. System appearance support and reduced-motion styles are implemented; those are not claims of exhaustive device testing.
- No new model training, calibration, dataset validation or detection-accuracy claim belongs to this redesign.
- The build reports a 524.57 kB lazy PDF chunk containing jsPDF and embedded fonts. It is loaded for export rather than the initial page. No measured production-performance claim is made.
- The original image is not retained in saved reports. Re-uploading the source remains necessary for pixel inspection after refresh.

## Main implementation locations

Design tokens/base styles: `frontend/src/styles/`. Shared navigation/appearance/auth/status: `frontend/src/components/`. Page layouts: `frontend/src/views/`. Verdict presentation: `frontend/src/services/assessmentPresentation.ts`. PDF layout/fonts: `frontend/src/services/pdfLayout.ts` and `pdfTypography.ts`.
