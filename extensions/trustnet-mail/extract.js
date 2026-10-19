/* Scoped Gmail adapter. Never reads inbox previews or an entire conversation. */
var TrustNetExtract = (() => {
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

  const fingerprint = message => JSON.stringify(message);
  return { opened, extract, fingerprint };
})();

if (typeof globalThis !== 'undefined') globalThis.TrustNetExtract = TrustNetExtract;
if (typeof window !== 'undefined') window.TrustNetExtract = TrustNetExtract;
