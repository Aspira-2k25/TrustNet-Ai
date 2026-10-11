/* Scoped Gmail adapter. Never reads inbox previews or an entire conversation. */
globalThis.TrustNetExtract = (() => {
  const shown = el => {if(!el)return false;for(let node=el;node;node=node.parentElement){const style=getComputedStyle(node);if(node.getAttribute('aria-hidden')==='true'||style.display==='none'||style.visibility==='hidden')return false;}return true;};
  function opened(root = document) {
    return [...root.querySelectorAll('.adn.ads')].filter(el => !el.closest('.a3s') && shown(el) && shown(el.querySelector('.a3s')));
  }
  function extract(container) {
    const body = container.querySelector('.a3s');
    if (!shown(body)) throw new Error('Message is collapsed or not readable. Expand it or paste it into TrustNet.');
    const subject = document.querySelector('h2.hP')?.innerText || document.querySelector('h2.hP')?.textContent || '';
    const text = body.innerText ?? body.textContent;
    const headerSender = [...container.querySelectorAll('.gD[email]')].find(el=>!body.contains(el));
    const sender = headerSender?.getAttribute('email') || '';
    if (!text?.trim()) throw new Error('Selected message has no readable text. Use manual paste.');
    if (Array.from(text).length + Array.from(subject).length + 2 > 10000) throw new Error('Subject/body exceed 10,000 characters. Paste and explicitly select a shorter section; nothing was silently truncated.');
    const anchors = [...body.querySelectorAll('a[href]')].filter(shown);
    if (anchors.length > 50) throw new Error('More than 50 displayed links. Use manual paste; links were not silently discarded.');
    const displayed_links = anchors.map(a => ({text: (a.innerText ?? a.textContent), href: a.getAttribute('href')}));
    if (displayed_links.some(a => a.href.length>2048 || a.text.length>500)||Array.from(subject).length>500||sender.length>320) throw new Error('A link or header exceeds supported length. Use manual paste.');
    // Gmail does not reliably expose raw Reply-To or authentication headers.
    return {message_type:'email', text, subject:subject.slice(0,500), claimed_sender:sender.slice(0,320), reply_to:'', displayed_links, optional_analysis:false};
  }
  const fingerprint = message => JSON.stringify(message);
  return {opened, extract, fingerprint};
})();
