(() => {
  const TrustNetExtract = (typeof window !== 'undefined' && window.TrustNetExtract) ||
    (typeof globalThis !== 'undefined' && globalThis.TrustNetExtract) ||
    (() => {
      const shown = el => {
        if (!el || !el.isConnected) return false;
        if (el.getAttribute('aria-hidden') === 'true' || el.hidden) return false;
        try {
          const style = window.getComputedStyle(el);
          if (style.display === 'none' || style.visibility === 'hidden') return false;
        } catch {}
        const rect = el.getBoundingClientRect();
        if (rect.height === 0 && rect.width === 0) return false;
        return true;
      };
      function opened(root = document) {
        const bodies = [...root.querySelectorAll('.a3s')].filter(shown);
        if (bodies.length > 0) {
          const containers = bodies.map(b => b.closest('.adn') || b.closest('[data-message-id]') || b.closest('[role="listitem"]') || b.parentElement).filter(Boolean);
          return [...new Set(containers)];
        }
        return [...root.querySelectorAll('.adn.ads')].filter(el => !el.closest('.a3s') && shown(el));
      }
      function extract(container) {
        const body = container.querySelector('.a3s') || (container.classList?.contains('a3s') ? container : null);
        if (!body || !shown(body)) throw new Error('Message is collapsed or not readable. Expand it or paste it into TrustNet.');
        const subject = document.querySelector('h2.hP')?.innerText || document.querySelector('h2.hP')?.textContent || document.querySelector('[data-thread-perm-id]')?.innerText || '';
        const text = body.innerText ?? body.textContent;
        const headerSender = [...container.querySelectorAll('.gD[email]')].find(el => !body.contains(el)) || document.querySelector('.gD[email]');
        const sender = headerSender?.getAttribute('email') || '';
        if (!text?.trim()) throw new Error('Selected message has no readable text. Use manual paste.');
        if (Array.from(text).length + Array.from(subject).length + 2 > 10000) throw new Error('Subject/body exceed 10,000 characters. Paste and explicitly select a shorter section; nothing was silently truncated.');
        const isWebHref = h => {
          if (!h || typeof h !== 'string') return false;
          const lower = h.trim().toLowerCase();
          if (lower.startsWith('mailto:') || lower.startsWith('tel:') || lower.startsWith('javascript:') || lower.startsWith('#')) return false;
          return lower.startsWith('http://') || lower.startsWith('https://') || lower.startsWith('www.');
        };
        const anchors = [...body.querySelectorAll('a[href]')].filter(shown);
        const displayed_links = anchors
          .map(a => ({ text: (a.innerText || a.textContent || '').trim(), href: (a.getAttribute('href') || '').trim() }))
          .filter(a => isWebHref(a.href));
        if (displayed_links.length > 50) throw new Error('More than 50 displayed web links. Use manual paste; links were not silently discarded.');
        if (displayed_links.some(a => a.href.length > 2048 || a.text.length > 500) || Array.from(subject).length > 500 || sender.length > 320) throw new Error('A link or header exceeds supported length. Use manual paste.');
        return { message_type: 'email', text, subject: subject.slice(0, 500), claimed_sender: sender.slice(0, 320), reply_to: '', displayed_links, optional_analysis: false };
      }
      return { opened, extract, fingerprint: message => JSON.stringify(message) };
    })();

  const installed = new Map();
  let timer;
  const rpc = request => chrome.runtime.sendMessage(request);

  function el(tag, className = '', text = '') {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text) element.textContent = text;
    return element;
  }

  function renderInspection(container, inspection) {
    container.replaceChildren();
    if (!inspection) { container.append(el('p', '', 'No inspection snapshot was returned. The quick assessment is unchanged.')); return; }
    container.append(el('p', '', `Inspection: ${inspection.status}. Snapshot: ${new Date(inspection.updated_at).toLocaleString()}.`));
    if (inspection.reason) container.append(el('p', '', inspection.reason));
      const result = inspection.result;
      if (result && ['SUCCESS', 'PARTIAL_SUCCESS'].includes(result.status)) {
        container.append(el('p', '', `Separate website assessment: ${result.risk_score}/100. This does not replace the original quick warning.`));
      }
    const summary = inspection.summary;
    if (!summary) return;
    container.append(el('p', '', summary.scope));
    container.append(el('h4', '', 'What we observed and why it matters'));
    for (const item of summary.observations || []) {
      const card=el('div','tn-explanation');
      card.append(el('strong','',item.title),el('p','',item.observed),el('p','',`Why it matters: ${item.why_it_matters}`));
      container.append(card);
    }
    container.append(el('h4','','Model assessment'),el('p','',summary.model_assessment));
    container.append(el('h4','','What we could not check'));
    for (const item of summary.missing_checks || []) container.append(el('p','',`${item.check.replaceAll('_',' ')}: ${item.reason}`));
  }

  // Safe In-Email Highlighting Helper
  function clearEmailHighlights(container) {
    if (!container) return;
    const marks = container.querySelectorAll('.trustnet-email-mark');
    marks.forEach(m => {
      const parent = m.parentNode;
      while (m.firstChild) parent.insertBefore(m.firstChild, m);
      parent.removeChild(m);
    });
  }

  function applyEmailHighlights(container, highlightWords) {
    clearEmailHighlights(container);
    if (!container || !highlightWords || highlightWords.length === 0) return;

    // Filter meaningful words (length >= 3 to avoid highlighting single letters like 'a', 'we')
    const validWords = highlightWords.filter(w => w.text && w.text.trim().length >= 3);
    if (validWords.length === 0) return;

    const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT, null, false);
    const textNodes = [];
    let node;
    while ((node = walker.nextNode())) {
      if (node.parentElement && !node.parentElement.closest('.trustnet-email-mark')) {
        textNodes.push(node);
      }
    }

    textNodes.forEach(textNode => {
      const parent = textNode.parentNode;
      let content = textNode.nodeValue;
      if (!content || !content.trim()) return;

      for (const item of validWords) {
        const word = item.text.trim();
        const regex = new RegExp(`\\b(${word.replace(/[.*+?^${}()|[\\]\\]/g, '\\$&')})\\b`, 'i');
        const match = content.match(regex);
        if (match && match.index !== undefined) {
          const matchStart = match.index;
          const matchEnd = matchStart + match[0].length;

          const before = content.slice(0, matchStart);
          const matchedText = content.slice(matchStart, matchEnd);
          const after = content.slice(matchEnd);

          const mark = document.createElement('mark');
          mark.className = 'trustnet-email-mark';
          mark.textContent = matchedText;
          mark.style.borderRadius = '4px';
          mark.style.padding = '1px 4px';
          mark.style.fontWeight = '600';
          mark.style.boxShadow = '0 1px 3px rgba(0,0,0,0.1)';

          if (item.type === 'support') {
            mark.style.backgroundColor = '#fecaca';
            mark.style.color = '#991b1b';
            mark.title = `TrustNet Red Flag: Risk indicator (+${item.val || ''})`;
          } else if (item.type === 'counter') {
            mark.style.backgroundColor = '#bbf7d0';
            mark.style.color = '#166534';
            mark.title = `TrustNet Context: Legitimate pattern`;
          } else {
            mark.style.backgroundColor = '#fef08a';
            mark.style.color = '#854d0e';
            mark.title = `TrustNet Context Observation: ${item.note || 'Indicator'}`;
          }

          const frag = document.createDocumentFragment();
          if (before) frag.appendChild(document.createTextNode(before));
          frag.appendChild(mark);
          if (after) frag.appendChild(document.createTextNode(after));

          parent.replaceChild(frag, textNode);
          break;
        }
      }
    });
  }

  function attach(message) {
    if (installed.has(message)) return;

    const host = el('div', 'trustnet-host-root');
    host.dataset.trustnetControl = 'true';
    host.style.cssText = 'display: block !important; margin: 14px 0 18px 0 !important; width: 100% !important; clear: both !important; position: relative !important; z-index: 1000 !important;';
    const shadow = host.attachShadow({ mode: 'open' });

    const style = el('style', '', `
      :host {
        display: block !important;
        width: 100% !important;
        max-width: 100% !important;
        box-sizing: border-box !important;
        margin: 14px 0 18px 0 !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif !important;
      }
      * { box-sizing: border-box; }
      [hidden] { display: none !important; }

      /* Executive Cyber Security Card */
      .tn-card {
        background: #0f172a;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 14px 18px;
        color: #f1f5f9;
        box-shadow: 0 4px 16px -2px rgba(15, 23, 42, 0.12), 0 2px 6px -1px rgba(0, 0, 0, 0.08);
        transition: all 0.25s ease;
      }
      .tn-card:hover {
        border-color: #475569;
      }

      /* Header Bar */
      .tn-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        flex-wrap: wrap;
      }

      .tn-brand {
        display: flex;
        align-items: center;
        gap: 10px;
      }
      .tn-shield {
        width: 22px;
        height: 22px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: linear-gradient(135deg, #0284c7, #0369a1);
        border-radius: 6px;
        box-shadow: 0 0 10px rgba(14, 165, 233, 0.35);
      }
      .tn-shield svg {
        width: 14px;
        height: 14px;
        fill: #ffffff;
      }
      .tn-title-group {
        display: flex;
        align-items: center;
        gap: 8px;
      }
      .tn-title {
        font-size: 14px;
        font-weight: 700;
        letter-spacing: -0.01em;
        color: #ffffff;
      }
      .tn-version-pill {
        font-size: 10px;
        font-weight: 600;
        padding: 1px 6px;
        background: rgba(148, 163, 184, 0.15);
        color: #94a3b8;
        border-radius: 4px;
        text-transform: uppercase;
        letter-spacing: 0.04em;
      }

      /* Action Buttons */
      .tn-actions {
        display: flex;
        align-items: center;
        gap: 8px;
      }

      .tn-btn {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 7px 13px;
        border-radius: 7px;
        font-size: 12px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.18s cubic-bezier(0.4, 0, 0.2, 1);
        border: none;
        outline: none;
        user-select: none;
      }

      .tn-btn-primary {
        background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%);
        color: #ffffff;
        box-shadow: 0 1px 3px rgba(2, 132, 199, 0.3);
      }
      .tn-btn-primary:hover:not(:disabled) {
        background: linear-gradient(135deg, #0369a1 0%, #075985 100%);
        box-shadow: 0 2px 8px rgba(2, 132, 199, 0.5);
        transform: translateY(-1px);
      }
      .tn-btn-primary:disabled {
        opacity: 0.6;
        cursor: not-allowed;
      }

      .tn-btn-ghost {
        background: rgba(255, 255, 255, 0.06);
        color: #cbd5e1;
        border: 1px solid rgba(255, 255, 255, 0.1);
      }
      .tn-btn-ghost:hover {
        background: rgba(255, 255, 255, 0.12);
        color: #ffffff;
        border-color: rgba(255, 255, 255, 0.2);
      }

      .tn-btn-sparkle {
        background: rgba(56, 189, 248, 0.12);
        color: #38bdf8;
        border: 1px solid rgba(56, 189, 248, 0.3);
      }
      .tn-btn-sparkle:hover {
        background: rgba(56, 189, 248, 0.22);
        color: #7dd3fc;
      }
      .tn-btn-sparkle.active {
        background: rgba(239, 68, 68, 0.15);
        color: #f87171;
        border-color: rgba(239, 68, 68, 0.35);
      }

      /* Cyber Scanner Bar */
      .tn-scan-track {
        margin-top: 12px;
        background: rgba(30, 41, 59, 0.6);
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 10px 14px;
      }
      .tn-laser-bar {
        width: 100%;
        height: 3px;
        background: #1e293b;
        border-radius: 2px;
        overflow: hidden;
        position: relative;
        margin-bottom: 8px;
      }
      .tn-laser-beam {
        position: absolute;
        width: 40%;
        height: 100%;
        background: linear-gradient(90deg, transparent, #38bdf8, #0284c7, transparent);
        border-radius: 2px;
        animation: laserScan 1.2s infinite ease-in-out;
      }
      @keyframes laserScan {
        0% { left: -40%; }
        100% { left: 100%; }
      }
      .tn-scan-status {
        font-size: 12px;
        font-weight: 500;
        color: #38bdf8;
        display: flex;
        align-items: center;
        gap: 6px;
      }

      /* Result Deck */
      .tn-results {
        margin-top: 12px;
        display: flex;
        flex-direction: column;
        gap: 10px;
      }

      /* Verdict Hero Bar */
      .tn-verdict-banner {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 10px 14px;
        border-radius: 8px;
        gap: 12px;
        flex-wrap: wrap;
      }
      .tn-verdict-banner.safe {
        background: rgba(16, 185, 129, 0.12);
        border: 1px solid rgba(16, 185, 129, 0.3);
      }
      .tn-verdict-banner.warn {
        background: rgba(245, 158, 11, 0.12);
        border: 1px solid rgba(245, 158, 11, 0.3);
      }
      .tn-verdict-banner.danger {
        background: rgba(239, 68, 68, 0.15);
        border: 1px solid rgba(239, 68, 68, 0.35);
      }

      .tn-verdict-left {
        display: flex;
        align-items: center;
        gap: 10px;
      }
      .tn-verdict-icon {
        width: 24px;
        height: 24px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 50%;
        font-size: 13px;
        font-weight: 700;
      }
      .safe .tn-verdict-icon { background: #065f46; color: #34d399; }
      .warn .tn-verdict-icon { background: #78350f; color: #fbbf24; }
      .danger .tn-verdict-icon { background: #7f1d1d; color: #f87171; }

      .tn-verdict-title {
        font-size: 13px;
        font-weight: 700;
      }
      .safe .tn-verdict-title { color: #34d399; }
      .warn .tn-verdict-title { color: #fbbf24; }
      .danger .tn-verdict-title { color: #f87171; }

      .tn-verdict-desc {
        font-size: 11px;
        color: #94a3b8;
      }

      .tn-score-pill {
        font-size: 12px;
        font-weight: 700;
        padding: 4px 10px;
        border-radius: 6px;
      }
      .safe .tn-score-pill { background: rgba(16, 185, 129, 0.2); color: #34d399; }
      .warn .tn-score-pill { background: rgba(245, 158, 11, 0.2); color: #fbbf24; }
      .danger .tn-score-pill { background: rgba(239, 68, 68, 0.25); color: #f87171; }

      /* Metrics Triple Deck */
      .tn-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
        gap: 8px;
      }
      .tn-stat-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 7px;
        padding: 8px 12px;
      }
      .tn-stat-label {
        font-size: 10px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #64748b;
        font-weight: 600;
      }
      .tn-stat-val {
        font-size: 13px;
        font-weight: 600;
        color: #e2e8f0;
        margin-top: 2px;
      }

      /* Explanation Callout */
      .tn-explanation {
        font-size: 12px;
        line-height: 1.5;
        color: #94a3b8;
        background: rgba(15, 23, 42, 0.5);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 7px;
        padding: 9px 12px;
      }

      /* Evidence Badges */
      .tn-clues-section {
        display: flex;
        flex-direction: column;
        gap: 6px;
      }
      .tn-clues-heading {
        font-size: 11px;
        font-weight: 600;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.03em;
      }
      .tn-chips-flow {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
      }
      .tn-chip {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        padding: 3px 8px;
        border-radius: 5px;
        font-size: 11px;
        font-weight: 600;
      }
      .tn-chip.red {
        background: rgba(239, 68, 68, 0.12);
        color: #f87171;
        border: 1px solid rgba(239, 68, 68, 0.25);
      }
      .tn-chip.green {
        background: rgba(16, 185, 129, 0.12);
        color: #34d399;
        border: 1px solid rgba(16, 185, 129, 0.25);
      }
      .tn-chip.blue {
        background: rgba(56, 189, 248, 0.12);
        color: #38bdf8;
        border: 1px solid rgba(56, 189, 248, 0.25);
      }

      /* Collapsible Annotated Text */
      details.tn-details {
        background: rgba(0, 0, 0, 0.2);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 7px;
        padding: 7px 12px;
      }
      summary.tn-summary {
        font-size: 11px;
        font-weight: 600;
        color: #64748b;
        cursor: pointer;
        user-select: none;
        outline: none;
      }
      summary.tn-summary:hover {
        color: #94a3b8;
      }
      .tn-annotated-box {
        margin-top: 8px;
        font-size: 12px;
        line-height: 1.6;
        color: #cbd5e1;
        white-space: pre-wrap;
        word-break: break-word;
        max-height: 200px;
        overflow-y: auto;
        padding: 8px;
        background: rgba(0, 0, 0, 0.3);
        border-radius: 5px;
      }
      mark.support {
        background: #991b1b;
        color: #fecaca;
        padding: 1px 3px;
        border-radius: 3px;
      }
      mark.counter {
        background: #166534;
        color: #bbf7d0;
        padding: 1px 3px;
        border-radius: 3px;
      }

      .tn-status-note {
        font-size: 11px;
        color: #64748b;
        margin-top: 4px;
      }
    `);

    const box = el('section', 'tn-card');

    // Header Bar
    const header = el('div', 'tn-header');
    
    const brand = el('div', 'tn-brand');
    brand.innerHTML = `
      <div class="tn-shield">
        <svg viewBox="0 0 24 24"><path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm-1 6h2v2h-2V7zm0 4h2v6h-2v-6z"/></svg>
      </div>
      <div class="tn-title-group">
        <span class="tn-title">TrustNet Security Guard</span>
        <span class="tn-version-pill">DistilBERT v2</span>
      </div>
    `;

    const actions = el('div', 'tn-actions');
    const highlightBtn = el('button', 'tn-btn tn-btn-sparkle', '✨ Highlight in Email');
    highlightBtn.hidden = true;

    const scanBtn = el('button', 'tn-btn tn-btn-primary', '🛡️ Scan Message');
    const cancelBtn = el('button', 'tn-btn tn-btn-ghost', 'Cancel');
    cancelBtn.hidden = true;

    actions.append(highlightBtn, scanBtn, cancelBtn);
    header.append(brand, actions);

    // Cyber Scanning Bar
    const scanTrack = el('div', 'tn-scan-track');
    scanTrack.hidden = true;
    scanTrack.innerHTML = `
      <div class="tn-laser-bar"><div class="tn-laser-beam"></div></div>
      <div class="tn-scan-status">
        <span>⚡</span>
        <span class="tn-scan-status-text">Analyzing message tokens & security signals…</span>
      </div>
    `;
    const scanStatusText = scanTrack.querySelector('.tn-scan-status-text');

    // Default connection note
    const connectionNote = el('div', 'tn-status-note', 'Checking local TrustNet engine connection…');

    // Results container
    const resultsDeck = el('div', 'tn-results');
    resultsDeck.hidden = true;

    box.append(header, scanTrack, connectionNote, resultsDeck);
    shadow.append(style, box);

    // Insert directly above email body
    const bodyEl = message.querySelector('.a3s') || (message.classList?.contains('a3s') ? message : null);
    if (bodyEl && bodyEl.parentElement) {
      bodyEl.parentElement.insertBefore(host, bodyEl);
    } else {
      message.prepend(host);
    }
    console.log('[TrustNet Mail] Card injected into message body');

    const state = {
      host,
      identity: '',
      id: '',
      busy: false,
      isHighlighted: false,
      flaggedWords: []
    };
    installed.set(message, state);

    function cancelScan() {
      if (state.id) rpc({ action: 'CANCEL', id: state.id }).catch(() => {});
      state.id = '';
      state.busy = false;
      scanBtn.disabled = false;
      cancelBtn.hidden = true;
      scanTrack.hidden = true;
    }
    state.cancel = cancelScan;

    cancelBtn.onclick = () => {
      cancelScan();
      connectionNote.textContent = 'Scan cancelled.';
      connectionNote.hidden = false;
    };

    rpc({ action: 'STATUS' }).then(r => {
      if (r.ok && r.connected) {
        connectionNote.textContent = 'Ready. Click "Scan Message" to evaluate this email for scams & smishing.';
      } else {
        connectionNote.textContent = 'Local TrustNet offline. Ensure backend is running at http://localhost:8000.';
      }
    }).catch(() => {
      connectionNote.textContent = 'Extension disconnected. Please reload Gmail.';
    });

    highlightBtn.onclick = () => {
      const currentBody = message.querySelector('.a3s');
      if (!state.isHighlighted) {
        applyEmailHighlights(currentBody, state.flaggedWords);
        state.isHighlighted = true;
        highlightBtn.textContent = '✖ Clear Highlights';
        highlightBtn.classList.add('active');
      } else {
        clearEmailHighlights(currentBody);
        state.isHighlighted = false;
        highlightBtn.textContent = '✨ Highlight in Email';
        highlightBtn.classList.remove('active');
      }
    };

    scanBtn.onclick = async () => {
      if (state.busy) return;
      let input;
      try {
        input = TrustNetExtract.extract(message);
      } catch (e) {
        connectionNote.textContent = e.message;
        return;
      }

      const identity = TrustNetExtract.fingerprint(input);
      const id = crypto.randomUUID();
      state.identity = identity;
      state.id = id;
      state.busy = true;

      scanBtn.disabled = true;
      cancelBtn.hidden = false;
      resultsDeck.hidden = true;
      resultsDeck.replaceChildren();

      connectionNote.hidden = true;
      scanTrack.hidden = false;
      scanStatusText.textContent = 'Analysing message and embedded links…';

      const stepTimer = setTimeout(() => {
        if (state.busy) scanStatusText.textContent = 'Evaluating DistilBERT neural fraud signals…';
      }, 750);

      try {
        const response = await rpc({ action: 'SCAN', id, message: input });
        clearTimeout(stepTimer);

        if (state.id !== id || !message.isConnected || TrustNetExtract.fingerprint(TrustNetExtract.extract(message)) !== identity) return;
        if (!response.ok) throw new Error(response.error);
        if (response.id !== id) throw new Error('Mismatched response; retry.');

        const result = response.scan.result;
        const meta = result.metadata || {};

        // Explicitly hide scanning track
        scanTrack.hidden = true;
        resultsDeck.hidden = false;
        highlightBtn.hidden = false;
        scanBtn.textContent = '↻ Re-Scan';

        const riskScore = Number(result.risk_score || 0);

        // 1. Verdict Banner
        let toneClass = 'safe';
        let iconSymbol = '✓';
        let headline = 'No strong scam indicators';
        let subline = 'Limited model assessment. Sender identity and website safety are not verified.';

        if (result.verdict === 'LIKELY_SCAM' || result.verdict === 'SMISHING_RISK') {
          toneClass = 'danger';
          iconSymbol = '!';
          headline = 'Phishing / Fraud Warning';
          subline = 'High risk deceptive pattern detected. Do not click links or share credentials.';
        } else if (['SUSPICIOUS','UNABLE_TO_ASSESS'].includes(result.verdict) || meta.assessment_dimensions?.message_category?.value === 'spam') {
          toneClass = 'warn';
          iconSymbol = 'ℹ';
          headline = result.verdict === 'UNABLE_TO_ASSESS' ? 'Unable to assess reliably' : 'Review recommended';
          subline = meta.display_verdict || 'Some signals or missing checks require review.';
        }

        const banner = el('div', `tn-verdict-banner ${toneClass}`);
        banner.innerHTML = `
          <div class="tn-verdict-left">
            <div class="tn-verdict-icon">${iconSymbol}</div>
            <div>
              <div class="tn-verdict-title">${headline}</div>
              <div class="tn-verdict-desc">${subline}</div>
            </div>
          </div>
          <div class="tn-score-pill">${riskScore.toFixed(1)} / 100 Risk</div>
        `;
        resultsDeck.append(banner);
        if (meta.fusion?.links_found) {
          resultsDeck.append(el('div','tn-explanation',`Message model: ${Number(meta.fusion.message_score).toFixed(1)}/100. Highest URL risk: ${meta.fusion.url_score==null?'Unavailable':Number(meta.fusion.url_score).toFixed(1)+'/100'}. ${meta.fusion.links_assessed}/${meta.fusion.links_found} links assessed. Combined score is a warning index, not a probability.`));
          for (const [linkIndex, link] of (meta.links || []).entries()) {
            const isWeb = typeof link.url === 'string' && /^(?:https?:\/\/|www\.)/i.test(link.url.trim());
            const linkCard=el('div','tn-explanation');
            linkCard.append(el('p','',`${link.url} — ${link.status}${link.risk_score==null?'':': '+Number(link.risk_score).toFixed(1)+'/100'}. ${link.reason||''}`));
            const details=el('div');
            if(link.inspection)renderInspection(details,link.inspection);
            if(linkIndex<8 && isWeb){
              const inspectButton=el('button','tn-btn-secondary','Inspect this URL');
              const notice=el('p','','On request, the backend contacts this destination for bounded DNS, HTTPS and static page checks. Scripts are not run.');
              inspectButton.onclick=async()=>{
                if(state.busy)return;
                const inspectId='inspect-'+Date.now().toString(36)+'-'+Math.random().toString(36).slice(2);
                state.id=inspectId;state.busy=true;scanBtn.disabled=true;cancelBtn.hidden=false;inspectButton.disabled=true;
                details.replaceChildren(el('p','','Inspecting website...'));
                try{
                  const inspected=await rpc({action:'INSPECT_LINK',id:inspectId,scanId:response.scan.id,linkIndex});
                  if(state.id!==inspectId||!message.isConnected||TrustNetExtract.fingerprint(TrustNetExtract.extract(message))!==identity)return;
                  if(!inspected.ok)throw new Error(inspected.error||'Inspection unavailable');
                  renderInspection(details,inspected.scan.result.metadata?.links?.[linkIndex]?.inspection);
                }catch(error){if(state.id===inspectId)details.replaceChildren(el('p','',error.message||'Inspection unavailable. The quick assessment is unchanged.'));}
                finally{if(state.id===inspectId){state.id='';state.busy=false;scanBtn.disabled=false;cancelBtn.hidden=true;inspectButton.disabled=false;}}
              };
              linkCard.append(inspectButton,notice);
            }
            linkCard.append(details);resultsDeck.append(linkCard);
          }
        }

        // 2. Metrics Deck
        const metricsDeck = el('div', 'tn-grid');
        metricsDeck.innerHTML = `
          <div class="tn-stat-card">
            <div class="tn-stat-label">Category</div>
            <div class="tn-stat-val">${meta.assessment_dimensions?.message_category?.value || 'Standard'}</div>
          </div>
          <div class="tn-stat-card">
            <div class="tn-stat-label">Message-model confidence</div>
            <div class="tn-stat-val">${(Number(meta.message_model?.confidence ?? result.confidence ?? 0) * 100).toFixed(1)}%</div>
          </div>
          <div class="tn-stat-card">
            <div class="tn-stat-label">Sender Authenticity</div>
            <div class="tn-stat-val">Not verified</div>
          </div>
        `;
        resultsDeck.append(metricsDeck);

        // 3. Explanation Callout
        if (result.explanation) {
          const exp = el('div', 'tn-explanation', result.explanation);
          resultsDeck.append(exp);
        }

        // 4. Meaningful Clues & Evidence Chips (Filtered for high quality)
        const text = Array.from(meta.assessed_text || '');
        const spans = (meta.spans || []).filter(s =>
          Number.isInteger(s.start) && Number.isInteger(s.end) &&
          s.start >= 0 && s.end <= text.length && s.start < s.end
        );

        state.flaggedWords = [];
        const chipsFlow = el('div', 'tn-chips-flow');

        // Comprehensive stopword set to prevent common grammatical words from appearing as indicators
        const ignoreList = new Set([
          'a', 'about', 'above', 'after', 'again', 'against', 'all', 'am', 'an', 'and', 'any', 'are', 'as', 'at',
          'be', 'because', 'been', 'before', 'being', 'below', 'between', 'both', 'but', 'by', 'can', 'could',
          'did', 'do', 'does', 'doing', 'down', 'during', 'each', 'few', 'for', 'from', 'further', 'gap', 'had', 'has',
          'have', 'having', 'he', 'her', 'here', 'hers', 'herself', 'him', 'himself', 'his', 'how', 'i', 'if',
          'in', 'into', 'is', 'it', 'its', 'itself', 'just', 'live', 'me', 'more', 'most', 'my', 'myself', 'no', 'nor',
          'not', 'now', 'of', 'off', 'on', 'once', 'only', 'or', 'other', 'our', 'ours', 'ourselves', 'out', 'over',
          'own', 'same', 'she', 'should', 'so', 'some', 'such', 'than', 'that', 'the', 'their', 'theirs',
          'them', 'themselves', 'then', 'there', 'these', 'they', 'this', 'those', 'through', 'to', 'too', 'under',
          'until', 'up', 'very', 'was', 'we', 'were', 'what', 'when', 'where', 'which', 'while', 'who', 'whom',
          'why', 'will', 'with', 'would', 'you', 'your', 'yours', 'yourself', 'yourselves'
        ]);

        spans.forEach(s => {
          const rawWord = text.slice(s.start, s.end).join('').trim();
          if (!rawWord || ignoreList.has(rawWord.toLowerCase()) || rawWord.length <= 2) return;
          // Filter out sub-threshold model noise (micro-fluctuations below 1.5% probability sensitivity)
          if (s.kind === 'model' && Math.abs(s.contribution || 0) < 0.015) return;

          let chipClass = 'green';
          let prefix = '✓';
          let itemType = 'counter';

          if (s.kind === 'model' && s.contribution > 0) {
            chipClass = 'red';
            prefix = '▲';
            itemType = 'support';
          } else if (s.kind === 'link') {
            chipClass = 'blue';
            prefix = '🔗';
            itemType = 'link';
          } else if (s.kind === 'context') {
            chipClass = 'red';
            prefix = '⚡';
            itemType = 'context';
          }

          state.flaggedWords.push({
            text: rawWord,
            type: itemType,
            val: s.contribution ? s.contribution.toFixed(2) : null,
            note: s.note
          });

          const chip = el('span', `tn-chip ${chipClass}`, `${prefix} ${rawWord}`);
          chipsFlow.append(chip);
        });

        if (chipsFlow.children.length > 0) {
          const cluesSection = el('div', 'tn-clues-section');
          cluesSection.innerHTML = '<div class="tn-clues-heading">Key Signal Indicators</div>';
          cluesSection.append(chipsFlow);
          resultsDeck.append(cluesSection);
        }

        // 5. Collapsible Full Text
        const details = el('details', 'tn-details');
        const summary = el('summary', 'tn-summary', '▾ View Model Attribution Full Text');
        const annotatedBox = el('div', 'tn-annotated-box');

        const points = [...new Set([0, text.length, ...spans.flatMap(s => [s.start, s.end])])].sort((a, b) => a - b);
        for (let i = 0; i < points.length - 1; i++) {
          const a = points[i];
          const b = points[i + 1];
          const value = spans.filter(s => s.start <= a && s.end >= b).reduce((sum, s) => sum + s.contribution, 0);
          const hasSignificantModel = Math.abs(value) >= 0.015;
          const part = el(hasSignificantModel ? 'mark' : 'span', value >= 0.015 ? 'support' : value <= -0.015 ? 'counter' : '', text.slice(a, b).join(''));
          annotatedBox.append(part);
        }

        details.append(summary, annotatedBox);
        resultsDeck.append(details);

      } catch (e) {
        clearTimeout(stepTimer);
        scanTrack.hidden = true;
        connectionNote.hidden = false;
        connectionNote.textContent = 'Scan error: ' + (e.message || 'Unknown error');
      } finally {
        if (state.id === id) {
          state.id = '';
          state.busy = false;
          scanBtn.disabled = false;
          cancelBtn.hidden = true;
        }
      }
    };
  }

  function refresh() {
    const opened = new Set(TrustNetExtract.opened());
    for (const [message, state] of installed) {
      if (!opened.has(message) || !message.isConnected) {
        state.cancel();
        clearEmailHighlights(message.querySelector('.a3s'));
        state.host.remove();
        installed.delete(message);
      } else if (state.identity) {
        try {
          if (TrustNetExtract.fingerprint(TrustNetExtract.extract(message)) !== state.identity) {
            state.cancel();
            clearEmailHighlights(message.querySelector('.a3s'));
            state.host.remove();
            installed.delete(message);
          }
        } catch {
          state.cancel();
          clearEmailHighlights(message.querySelector('.a3s'));
          state.host.remove();
          installed.delete(message);
        }
      }
    }
    for (const message of opened) attach(message);
    if (opened.size > 0) {
      console.log('[TrustNet Mail] Active message cards attached:', opened.size);
    }
  }

  new MutationObserver(records => {
    if (records.every(r => r.target.closest?.('[data-trustnet-control]'))) return;
    clearTimeout(timer);
    timer = setTimeout(refresh, 250);
  }).observe(document.body, {
    childList: true,
    subtree: true,
    attributes: true,
    attributeFilter: ['aria-hidden', 'class', 'style']
  });

  addEventListener('hashchange', refresh);
  addEventListener('popstate', refresh);
  setInterval(refresh, 1000);
  refresh();
  console.log('[TrustNet Mail] Content script initialized on Gmail');
})();
