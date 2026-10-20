import { ArrowDown, ArrowUpRight, Check, Image, Link, MessageSquare, ScanLine, ShieldCheck } from 'lucide-react';
import type { ModalityType } from './ScanUploadView';
import './landing.css';

interface Props { onStart: (module?: ModalityType) => void }

export function LandingView({ onStart }: Props) {
  return <div className="landing-page">
    <section className="landing-hero" aria-labelledby="landing-title">
      <div className="landing-copy">
        <h1 id="landing-title">A little doubt.<br/>A <em>closer look.</em></h1>
        <p className="landing-lead">The photo. The message. The link.<br/>Get a second opinion before you trust it.</p>
        <p className="landing-description">TrustNet checks for signs of AI generation, image editing and online scams, then shows you the evidence and what it cannot determine.</p>
        <div className="landing-actions">
          <button className="primary-button" onClick={() => onStart()}>Check something <ArrowUpRight size={19} aria-hidden="true"/></button>
          <a href="#how-it-works">See how it works <ArrowDown size={16} aria-hidden="true"/></a>
        </div>
        <div className="landing-assurance"><ShieldCheck size={17} aria-hidden="true"/><span>You choose what to scan. Nothing runs automatically.</span></div>
      </div>
      <div className="evidence-art" aria-hidden="true">
        <div className="art-floor"/>
        <div className="evidence-object">
          <div className="evidence-plane plane-back"><MessageSquare/><div className="object-lines"><span/><span/><span/></div><span className="plane-label">MESSAGE</span></div>
          <div className="evidence-plane plane-middle"><Link/><div className="object-link">https://<span>look.closer</span></div><span className="plane-label">URL</span></div>
          <div className="evidence-plane plane-front"><Image/><div className="image-composition"><div className="composition-sun"/><div className="composition-mountain"/><div className="composition-scan"/></div><span className="plane-label">IMAGE</span></div>
          <div className="inspection-lens"><div className="lens-inner"><ScanLine size={56} strokeWidth={1}/></div></div>
        </div>
        <div className="art-caption"><span/>Separate signals. A clearer picture.</div>
      </div>
    </section>

    <section className="landing-tools" aria-labelledby="tools-title">
      <div className="tools-heading"><h2 id="tools-title">What would you like<br/>to take a closer look at?</h2><p>Start with the thing you are unsure about.</p></div>
      <div className="tool-links">
        <button onClick={() => onStart('image')}><Image size={24} strokeWidth={1.5}/><span><strong>An image</strong><small>AI generation clues and supported editing evidence</small></span><ArrowUpRight size={22}/></button>
        <button onClick={() => onStart('scam_message')}><MessageSquare size={24} strokeWidth={1.5}/><span><strong>A message or email</strong><small>Scam warning signs, with embedded links checked too</small></span><ArrowUpRight size={22}/></button>
        <button onClick={() => onStart('phishing')}><Link size={24} strokeWidth={1.5}/><span><strong>A suspicious link</strong><small>URL patterns, lookalikes and available website evidence</small></span><ArrowUpRight size={22}/></button>
      </div>
    </section>

    <section className="landing-process" id="how-it-works" aria-labelledby="process-title">
      <div className="process-heading"><h2 id="process-title">An answer you can<br/>look into.</h2><p>A score is only the beginning. Understand what raised a warning, which checks ran and where the evidence stops.</p></div>
      <div className="process-steps">
        <div><span className="step-marker">1</span><h3>Bring what looks off</h3><p>Upload an original image, paste a message or enter a link. Sign in to run and save your scan.</p></div>
        <div><span className="step-marker">2</span><h3>See the reasons</h3><p>Review the available signals, highlighted evidence and checks that could not be completed.</p></div>
        <div><span className="step-marker">3</span><h3>Keep the context</h3><p>Return to saved scans and export a PDF. An Inconclusive result means more evidence is needed.</p></div>
      </div>
    </section>

    <section className="landing-mail" aria-labelledby="mail-title">
      <div className="mail-symbol" aria-hidden="true"><MessageSquare size={40} strokeWidth={1.2}/><ShieldCheck size={24}/></div>
      <div><h2 id="mail-title">Pause before you reply.</h2><p>The TrustNet Mail extension connects selected Gmail messages to the same message and URL checks. You decide when a scan starts.</p><details><summary>Extension setup and browser support</summary><ol><li>Start TrustNet and create a local account.</li><li>In Chrome or Edge, open the extensions page and enable Developer mode.</li><li>Choose Load unpacked and select <code>extensions/trustnet-mail</code> from this project.</li><li>Connect your account in the extension options, then reload Gmail.</li></ol><p>Chrome and Edge are the intended targets. Automated checks pass; live Gmail extraction is not yet verified. Firefox, Safari and Outlook are not supported.</p></details></div>
      <button className="mail-button" onClick={() => onStart('scam_message')}>Try a message first <ArrowUpRight size={18}/></button>
    </section>
    <section className="landing-limits"><Check size={22} aria-hidden="true"/><p><strong>Useful evidence. Honest limits.</strong> TrustNet can make mistakes. Results are probabilistic indicators, not proof. Image editing and newer AI generators have limited coverage. Verify important decisions another way.</p></section>
  </div>;
}
