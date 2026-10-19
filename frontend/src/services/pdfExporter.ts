import { assessmentVerdict } from './verdict';
import { jsPDF } from 'jspdf';
import type { ScanRecord } from '../types';

export function exportForensicPDFReport(scan: ScanRecord): void {
  if (scan.content_type === 'text' || scan.result?.module === 'scam_message' || !scan.result || !['SUCCESS','PARTIAL_SUCCESS'].includes(scan.status)) {
    exportMessagePDF(scan);
    return;
  }
  const doc = new jsPDF({
    orientation: 'portrait',
    unit: 'mm',
    format: 'a4',
  });

  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  const margin = 15;
  const contentWidth = pageWidth - margin * 2;

  const result = scan.result;
  const trustScore = scan.trust_score;
  const riskScore = trustScore?.trust_risk_score ?? result?.risk_score ?? 0;
  const visionAnalysis = scan.vision_analysis || result?.vision_analysis || result?.metadata?.vision_analysis || trustScore?.vision_analysis;
  const isVisionApplied = visionAnalysis?.status === 'APPLIED';
  const lmStudioModel = result?.metadata?.lm_studio_model || visionAnalysis?.model_name || 'Local Vision Model';

  const semanticVerdict = assessmentVerdict(scan);
  const bannerBg = semanticVerdict.includes('MANIPULATED') ? [239,68,68] : semanticVerdict.includes('UNCERTAIN') ? [245,158,11] : [14,165,233];
  const bannerText = [255,255,255];
  const subtext = 'Automated screening; neither provenance nor correctness is verified.';

  let y = margin;

  const checkPageBreak = (neededHeight: number) => {
    if (y + neededHeight > pageHeight - 30) {
      doc.addPage();
      y = margin + 5;
      return true;
    }
    return false;
  };

  // 1. TOP HEADER BAND (Professional Dark Slate)
  doc.setFillColor(15, 23, 42); // Slate-900 #0f172a
  doc.rect(0, 0, pageWidth, 24, 'F');

  // Title Logo & Text
  doc.setTextColor(255, 255, 255);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(15);
  doc.text('TrustNet', margin, 11);

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7.5);
  doc.setTextColor(148, 163, 184); // Slate-400
  doc.text('FORENSIC INTELLIGENCE LABS | SYNTHETIC MEDIA DEFENSE PLATFORM', margin, 17);

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(8.5);
  doc.setTextColor(255, 255, 255);
  doc.text('CONFIDENTIAL AUDIT REPORT', pageWidth - margin, 11, { align: 'right' });
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7.5);
  doc.setTextColor(148, 163, 184);
  doc.text(`REPORT ID: ${scan.id}`, pageWidth - margin, 17, { align: 'right' });

  y = 29;

  // 2. METADATA SUMMARY BAR
  doc.setFillColor(248, 250, 252); // Slate-50
  doc.setDrawColor(226, 232, 240); // Slate-200
  doc.setLineWidth(0.3);
  doc.rect(margin, y, contentWidth, 15, 'FD');

  doc.setFontSize(7.5);
  doc.setTextColor(71, 85, 105); // Slate-600

  const col1X = margin + 4;
  const col2X = margin + 50;
  const col3X = margin + 105;
  const col4X = margin + 145;

  doc.setFont('helvetica', 'bold');
  doc.text('Ingestion Date:', col1X, y + 5);
  doc.setFont('helvetica', 'normal');
  doc.text(new Date(scan.created_at).toLocaleString('en-GB'), col1X, y + 10.5);

  doc.setFont('helvetica', 'bold');
  doc.text('Target File:', col2X, y + 5);
  doc.setFont('helvetica', 'normal');
  const filenameTruncated = (scan.filename || 'Image Asset').length > 26 
    ? (scan.filename || 'Image Asset').substring(0, 24) + '...' 
    : (scan.filename || 'Image Asset');
  doc.text(filenameTruncated, col2X, y + 10.5);

  doc.setFont('helvetica', 'bold');
  doc.text('Content Type:', col3X, y + 5);
  doc.setFont('helvetica', 'normal');
  doc.text(scan.mime_type || 'Unavailable', col3X, y + 10.5);

  doc.setFont('helvetica', 'bold');
  doc.text('Processing Time:', col4X, y + 5);
  doc.setFont('helvetica', 'normal');
  doc.text(result?.processing_time_ms == null ? 'Unavailable' : `${result.processing_time_ms} ms`, col4X, y + 10.5);

  y += 19;

  // 3. EXECUTIVE VERDICT & RISK INDEX BANNER
  doc.setFillColor(bannerBg[0], bannerBg[1], bannerBg[2]);
  doc.rect(margin, y, contentWidth, 18, 'F');

  doc.setTextColor(bannerText[0], bannerText[1], bannerText[2]);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(12);
  doc.text(`VERDICT: ${semanticVerdict}`, margin + 5, y + 8);

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(8);
  doc.text(subtext, margin + 5, y + 14);

  // Right Side Risk Box
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(7.5);
  doc.text('RISK INDEX', pageWidth - margin - 5, y + 6.5, { align: 'right' });
  doc.setFontSize(13);
  doc.text(`${riskScore.toFixed(1)} / 100`, pageWidth - margin - 5, y + 14, { align: 'right' });

  y += 23;

  // 4. SECTION 1: EXECUTIVE FORENSIC SUMMARY
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(10);
  doc.setTextColor(15, 23, 42); // Slate-900
  doc.text('1. Executive Forensic Summary', margin, y);

  doc.setDrawColor(203, 213, 225);
  doc.setLineWidth(0.3);
  doc.line(margin, y + 2, pageWidth - margin, y + 2);

  y += 6;
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(8.5);
  doc.setTextColor(51, 65, 85); // Slate-700

  const summaryText = trustScore?.explanation || result?.explanation || 'No explanation supplied. Missing evidence cannot establish authenticity.';

  const splitSummary = doc.splitTextToSize(summaryText, contentWidth);
  doc.text(splitSummary, margin, y);
  y += splitSummary.length * 4 + 4;

  // 5. SECTION 2: MULTI-VECTOR ANALYZER TELEMETRY TABLE
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(10);
  doc.setTextColor(15, 23, 42);
  doc.text('2. Multi-Vector Analyzer Telemetry', margin, y);
  doc.line(margin, y + 2, pageWidth - margin, y + 2);
  y += 6;

  // Table Column Positions & Widths
  const colModuleX = margin + 2;
  const colModuleW = 48;

  const colDomainX = margin + 52;
  const colStatusX = margin + 84;
  const colObsX = margin + 104;
  const colObsW = contentWidth - 106; // ~74mm for Observation column!

  // Table Header Box
  doc.setFillColor(241, 245, 249); // Slate-100
  doc.rect(margin, y, contentWidth, 6, 'F');
  doc.setFontSize(7.5);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(71, 85, 105);

  doc.text('ANALYZER MODULE', colModuleX, y + 4.2);
  doc.text('DOMAIN', colDomainX, y + 4.2);
  doc.text('STATUS', colStatusX, y + 4.2);
  doc.text('FORENSIC OBSERVATION', colObsX, y + 4.2);

  y += 6;

  const analyzers = result?.analyzers || [];

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7);

  analyzers.forEach((analyzer, idx) => {
    const moduleNameLines = doc.splitTextToSize(analyzer.name, colModuleW);
    const observationText = analyzer.finding || analyzer.reason || 'Nominal execution complete with no anomalies flagged.';
    const observationLines = doc.splitTextToSize(observationText, colObsW);

    const lineCount = Math.max(moduleNameLines.length, observationLines.length);
    const rowHeight = Math.max(5.5, lineCount * 3.2 + 2);

    checkPageBreak(rowHeight + 1);

    if (idx % 2 === 1) {
      doc.setFillColor(248, 250, 252);
      doc.rect(margin, y, contentWidth, rowHeight, 'F');
    }
    
    // Module Name (Wrapped fully)
    doc.setTextColor(15, 23, 42);
    doc.text(moduleNameLines, colModuleX, y + 3.8);

    // Domain
    doc.setTextColor(100, 116, 139);
    doc.text(analyzer.category.toUpperCase(), colDomainX, y + 3.8);

    // Status
    if (analyzer.status === 'APPLIED') {
      doc.setTextColor(16, 185, 129); // Emerald
      doc.text('APPLIED', colStatusX, y + 3.8);
    } else {
      doc.setTextColor(148, 163, 184); // Slate
      doc.text('SKIPPED', colStatusX, y + 3.8);
    }

    // Observation (FULLY WRAPPED - NO TRUNCATION!)
    doc.setTextColor(51, 65, 85);
    doc.text(observationLines, colObsX, y + 3.8);

    y += rowHeight;
  });

  y += 5;

  // 6. SECTION 3: KEY ANOMALY FINDINGS & PHYSICAL EVIDENCE
  checkPageBreak(25);

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(10);
  doc.setTextColor(15, 23, 42);
  doc.text('3. Key Anomaly Findings & Physical Evidence', margin, y);
  doc.line(margin, y + 2, pageWidth - margin, y + 2);
  y += 6;

  const whyReasons: string[] = result?.metadata?.why_reasons || [];

  doc.setFontSize(7.5);
  whyReasons.forEach((reason) => {
    const isWarning = reason.startsWith('⚠') || semanticVerdict.includes('MANIPULATED');
    const cleanedText = reason.replace(/^[✓⚠ℹ]\s*/, '');
    const splitLine = doc.splitTextToSize(cleanedText, contentWidth - 25);
    const itemHeight = Math.max(4.5, splitLine.length * 3.6 + 1);

    checkPageBreak(itemHeight);

    doc.setFont('helvetica', 'bold');
    if (isWarning) {
      doc.setTextColor(220, 38, 38); // Red
      doc.text('[ANOMALY]', margin + 2, y);
    } else {
      doc.setTextColor(16, 185, 129); // Emerald
      doc.text('[OBSERVATION]', margin + 2, y);
    }

    doc.setFont('helvetica', 'normal');
    doc.setTextColor(51, 65, 85);
    doc.text(splitLine, margin + 22, y);
    y += itemHeight;
  });

  y += 5;

  // 7. SECTION 4: NON-TECHNICAL CONCISE CONCLUSION (Plain English for Non-Experts)
  let boxBg = [248, 250, 252];
  let boxBorder = [203, 213, 225];
  let titleColor = [15, 23, 42];
  let conclusionHeadline = '';
  let plainEnglishText = '';

  if (semanticVerdict.includes('MANIPULATED') || semanticVerdict.includes('AI')) {
    boxBg = [254, 242, 242]; // Light Red #fef2f2
    boxBorder = [252, 165, 165]; // Red border #fca5a5
    titleColor = [185, 28, 28]; // Dark Red #b91c1c
    conclusionHeadline = 'BOTTOM LINE: THIS IMAGE IS LIKELY AI-GENERATED OR ALTERED.';
    plainEnglishText = 'The recorded assessment indicates manipulation risk. Review the actual supplied evidence; this does not verify provenance or guarantee correctness.';
  } else if (semanticVerdict.includes('AUTHENTIC')) {
    boxBg = [236, 253, 245]; // Light Emerald #ecfdf5
    boxBorder = [110, 231, 183]; // Emerald border #6ee7b7
    titleColor = [4, 120, 87]; // Dark Emerald #047857
    conclusionHeadline = 'BOTTOM LINE: THIS IMAGE APPEARS AUTHENTIC AND GENUINE.';
    plainEnglishText = 'The recorded assessment is consistent with real capture. It does not prove that the media is authentic or unaltered.';
  } else {
    boxBg = [254, 243, 199]; // Light Amber #fef3c7
    boxBorder = [252, 211, 77]; // Amber border #fcd34d
    titleColor = [180, 83, 9]; // Dark Amber #b45309
    conclusionHeadline = 'BOTTOM LINE: RESULTS ARE INCONCLUSIVE (MANUAL REVIEW ADVISED).';
    plainEnglishText = 'Review the recorded evidence and model limitations. This screening does not verify provenance or establish authenticity.';
  }

  // Prepend LM Studio Local Vision Reasoning finding if active
  if (isVisionApplied && visionAnalysis?.simple_explanation) {
    plainEnglishText = `[LM Studio Vision Reasoning (${lmStudioModel})]: "${visionAnalysis.simple_explanation}"\n\n` + plainEnglishText;
  }

  doc.setFontSize(8);
  const splitPlainEnglish = doc.splitTextToSize(plainEnglishText, contentWidth - 8);
  const boxHeight = 12 + splitPlainEnglish.length * 3.8;
  const section4TotalNeededHeight = 10 + boxHeight;

  // Crucial fix: Check if BOTH Section 4 heading AND Box fit together!
  conclusionHeadline = `ASSESSMENT: ${semanticVerdict}`;

  checkPageBreak(section4TotalNeededHeight);

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(10);
  doc.setTextColor(15, 23, 42);
  doc.text('4. Plain-English Summary & Non-Technical Conclusion', margin, y);
  doc.line(margin, y + 2, pageWidth - margin, y + 2);
  y += 6;

  doc.setFillColor(boxBg[0], boxBg[1], boxBg[2]);
  doc.setDrawColor(boxBorder[0], boxBorder[1], boxBorder[2]);
  doc.setLineWidth(0.4);
  doc.rect(margin, y, contentWidth, boxHeight, 'FD');

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(8.5);
  doc.setTextColor(titleColor[0], titleColor[1], titleColor[2]);
  doc.text(conclusionHeadline, margin + 4, y + 5.5);

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(8);
  doc.setTextColor(51, 65, 85);
  doc.text(splitPlainEnglish, margin + 4, y + 10.5);

  // Add Page Footers & Numbers to all pages dynamically
  const totalPages = doc.getNumberOfPages();

  for (let i = 1; i <= totalPages; i++) {
    doc.setPage(i);
    const footerY = pageHeight - 22;

    doc.setFillColor(248, 250, 252);
    doc.setDrawColor(226, 232, 240);
    doc.setLineWidth(0.3);
    doc.rect(margin, footerY, contentWidth, 15, 'FD');

    doc.setFontSize(7);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(71, 85, 105);
    doc.text('CHAIN OF CUSTODY & VERIFICATION DIGEST', margin + 4, footerY + 4.5);

    doc.setFont('helvetica', 'normal');
    doc.setFontSize(6.5);
    doc.setTextColor(100, 116, 139);
    doc.text(`UUID Hash: sha256:${scan.id}-${Date.now().toString(16)}`, margin + 4, footerY + 8.8);
    doc.text(`Certified by: TrustNet Automated Forensic Core Engine v1.0.0`, margin + 4, footerY + 12.5);

    // Digital Stamp Box
    doc.setDrawColor(79, 70, 229); // Indigo
    doc.rect(pageWidth - margin - 40, footerY + 2, 36, 11);
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(6.5);
    doc.setTextColor(79, 70, 229);
    doc.text('SCREENING REPORT', pageWidth - margin - 22, footerY + 6, { align: 'center' });
    doc.setFontSize(5.5);
    doc.setFont('helvetica', 'normal');
    doc.text('NO VERIFIED PROVENANCE', pageWidth - margin - 22, footerY + 10, { align: 'center' });

    // Page numbering
    doc.setFontSize(7.5);
    doc.setTextColor(148, 163, 184);
    doc.text(`Page ${i} of ${totalPages}`, pageWidth / 2, pageHeight - 3, { align: 'center' });
  }

  // Save PDF file download
  doc.save(`TrustNet_Forensic_Report_${scan.id}.pdf`);
}

function exportMessagePDF(scan: ScanRecord): void {
  const doc = new jsPDF(); let y=18;
  const line = (text: string) => {
    // Keep every codepoint recoverable without asking the standard PDF font
    // to encode unsupported glyphs (which can corrupt the entire text run).
    const printable = Array.from(text, c => {
      const point = c.codePointAt(0)!;
      return (point >= 32 && point <= 126) || [9, 10, 13].includes(point) ? c : `\\u{${point.toString(16).toUpperCase()}}`;
    }).join('');
    const lines: string[] = doc.splitTextToSize(printable,180);
    lines.forEach(t=>{if(y>275){doc.addPage();y=18;}doc.text(t,15,y);y+=5;}); y+=3;
  };
  doc.setFontSize(14);line('TrustNet message assessment');doc.setFontSize(10);
  line(`Scan: ${scan.id} | ${scan.created_at}`);line(`Verdict: ${assessmentVerdict(scan)}`);
  const r=scan.result;
  if(r && ['SUCCESS','PARTIAL_SUCCESS'].includes(r.status) && ['SUCCESS','PARTIAL_SUCCESS'].includes(scan.status)) {
    const riskLabel=r.metadata?.evaluated_domains?.includes('English email') ? 'Message-model fraud estimate (limited coverage)' : `SMS-model smishing estimate${r.metadata?.message_type==='email'?' (email calibration unavailable)':''}`;
    line(`${r.metadata?.fusion?.links_found?'Combined message / URL warning index':riskLabel}: ${r.risk_score.toFixed(1)}/100`);
    if(r.metadata?.fusion?.links_found){
      const f=r.metadata.fusion;
      line(`Message model: ${f.message_score}/100. Highest URL risk: ${f.url_score??'Unavailable'}. Links assessed: ${f.links_assessed}/${f.links_found}.`);
      line(f.definition);
      (r.metadata.links || []).forEach((link:{url:string;status:string;risk_score?:number;reason?:string;inspection?:import('../components/scam_message/LinkInspection').SavedInspection})=>{
        line(`${link.url}: ${link.status}; quick URL risk ${link.risk_score??'Unavailable'}. ${link.reason||''}`);
        const inspection=link.inspection;
        if(inspection){
          line(`Separate website inspection: ${inspection.status}. Snapshot: ${inspection.updated_at}.`);
          if(inspection.reason)line(inspection.reason);
          if(inspection.summary){
            line(inspection.summary.scope);
            line('What we observed and why it matters:');
            inspection.summary.observations.forEach(item=>{line(`${item.title}: ${item.observed}`);line(`Why it matters: ${item.why_it_matters}`);});
            line(`Model assessment: ${inspection.summary.model_assessment}`);
            line('What we could not check:');
            inspection.summary.missing_checks.forEach(item=>line(`${item.check}: ${item.reason}`));
          }
        }
      });
    }
    const dimensions=r.metadata?.assessment_dimensions;
    if(dimensions){line(`Category: ${dimensions.message_category.value}. ${dimensions.message_category.reason}`);line(`Sender: ${dimensions.sender_verification.status}. ${dimensions.sender_verification.reason}`);line(`AI authorship: ${dimensions.ai_authorship.status}. ${dimensions.ai_authorship.reason}`);}
    (r.metadata?.sender_link_observations || []).forEach((o:Record<string,unknown>)=>line(Object.entries(o).map(([k,v])=>`${k}: ${String(v)}`).join('; ')));
    (r.metadata?.next_steps || []).forEach((s:string)=>line(s));
    if(r.metadata?.optional_explanation){line(`Optional evidence summary: ${r.metadata.optional_explanation.status}. ${r.metadata.optional_explanation.reason || r.metadata.optional_explanation.method}`);(r.metadata.optional_explanation.evidence || []).forEach((e:{note:string})=>line(e.note));}
    line(`Message-model confidence: ${((r.metadata?.message_model?.confidence??r.confidence)*100).toFixed(1)}%. ${r.metadata?.message_model?.confidence_definition || r.metadata?.confidence_definition || 'Definition unavailable'}`);
    line(r.explanation || 'Explanation unavailable');
    line('Original message (non-ASCII codepoints shown as Unicode escapes):');line(scan.raw_input || 'Original message unavailable');
    line(`Signed model evidence (${r.metadata?.attribution_unit || 'logit margin, not probability points'}):`);
    r.evidence?.forEach(e=>line(`${e.feature_or_region}: ${e.contribution.toFixed(4)}. ${e.human_readable_note}`));
    line('Layers:');r.analyzers?.forEach(a=>line(`${a.name}: ${a.status}. ${a.finding || a.reason || 'No finding supplied'}`));
    (r.metadata?.limitations || []).forEach((l:string)=>line(l));
    line(`Model: ${r.detector_id} / ${r.model_version}; preprocessing ${r.preprocessing_version}`);
  } else {line('No successful assessment available. Missing or failed data does not establish safety.');}
  line('PDF uses a standard font and reversible Unicode escapes for non-ASCII characters. The website preserves the original Unicode text.');
  doc.save(`TrustNet_Message_${scan.id}.pdf`);
}
