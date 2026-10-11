# TrustNet Mail 1.0

Chrome/Edge Manifest V3 implementation for Gmail opened messages. Outlook Web is unsupported: paste the selected email in the website's Email mode. Chrome and Edge APIs and DOM/navigation fixtures have been tested; actual installation and live Gmail extraction have not yet been verified. Gmail DOM changes can break extraction.

1. Start TrustNet's gateway, authentication, scanner and scam inference services.
2. Open `chrome://extensions` (Chrome) or `edge://extensions` (Edge), enable Developer mode, choose **Load unpacked**, and select this folder.
3. Open the extension's Options. Select the fixed localhost gateway and sign in with your existing TrustNet account. Create an account on the website first if needed. Passwords are not saved. The access token remains in trusted extension session storage, never the email DOM; reconnect after expiry or browser restart.
4. Reload Gmail, open/expand a message, then click its **TrustNet Scan** control. Scanning happens only on click. Multiple expanded messages have separate controls. Quoted text inside the selected body is included. Hidden/collapsed content and attachments are excluded.
5. Wait for the panel. Cancellation/navigation invalidates stale results. Disconnected, unsupported or oversized content gives a manual-paste instruction rather than a safe verdict.

Only Gmail and the two fixed localhost gateway origins are permitted. No arbitrary fetch proxy, inbox API, Gmail password access, mail modification, links opened, tracking images loaded by TrustNet, or provider calls are used. Optional Groq is always off in this extension. Local requests include visible body, subject, claimed sender and displayed-link text/href. Reply-to/header authentication is unavailable from this adapter.

The selected predictor has limited English SMS/email training and collection-specific evaluation. Modern inbox reliability is not established; low scores do not verify sender identity. AI authorship is not assessed. Positive/negative highlights are partial changes in the complete deployed probability when spans are masked, not probability percentages for individual words. A long/slow request may have no model highlights because an additional masked inference would exceed the attribution budget; unavailable evidence is displayed honestly.

External QA: `scam/qa/continuation/extension_tests.cjs` tests DOM, worker validation and stale navigation. `extension_live.cjs` runs the real worker with a fixture Chrome API against the actual authenticated gateway. These are not live Gmail/browser installation tests.
