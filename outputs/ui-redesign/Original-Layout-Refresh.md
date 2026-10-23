# Original layout, refreshed theme

20 October 2026. This is the current direction and supersedes the editorial and investigation-workspace alternatives.

The original source in Git was inspected for layout reference. Its top navigation, welcome banner, two-column Home section, six category cards, three history summary cards and horizontal scanner selector have been restored through the current components. The existing routing, authentication integration, filtering/pagination, unavailable-tool states and corrected assessment meanings remain in place. No old backend or score-threshold logic was restored.

The theme uses charcoal surfaces and restrained amber accents, with a corresponding light appearance. IBM Plex typography, consistent rounded controls, stronger spacing and a matching shield mark polish the familiar structure. Page surfaces and report headers use the same shared tokens. Model outputs, uncertainty, evidence and privacy disclosures were preserved.

Build, lint, image assessment checks and UI presentation checks passed. Automated browser coverage and raw results are in `runtime_state/ui-redesign/refresh-accessibility.json`. The matrix covers Home, guest Scan History, image/website/message scanners, sign-in and registration at 320/375/768/1024/1440/1920px in both themes. Manual checks include mobile menu focus, Escape dismissal and the restored scanner-tab layout. This does not establish signed-in backend integration, actual-device coverage, assistive-technology certification or detector accuracy.

Previews: `TrustNet-Refreshed-Home-Dark.png`, `TrustNet-Refreshed-Home-Light.png`, `TrustNet-Refreshed-Scanner.png`, `TrustNet-Refreshed-History.png`. Earlier images in this folder are historical alternatives. The temporary preview server and QA assets were stopped/removed after verification. The existing lazy PDF chunk-size warning remains.
