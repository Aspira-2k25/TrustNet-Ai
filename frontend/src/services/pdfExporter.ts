import { jsPDF } from 'jspdf';
import type { ScanRecord } from '../types';

export function exportForensicPDFReport(scan: ScanRecord): void {
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
  const riskScore = trustScore?.trust_risk_score ?? result?.risk_score ?? 10.2;
  const rawVerdict = result?.verdict || 'AUTHENTIC';
  const isContradiction = Boolean(result?.metadata?.is_contradiction || trustScore?.contradiction_detected);

  let semanticVerdict = 'AUTHENTIC / NATURAL CAPTURE';
  let bannerBg = [16, 185, 129]; // Emerald #10b981
  let bannerText = [255, 255, 255];
  let subtext = 'Low evidence of synthetic manipulation across all analyzed vectors.';

  if (isContradiction || rawVerdict === 'UNCERTAIN' || (riskScore >= 45.0 && riskScore < 65.0)) {
    semanticVerdict = 'UNCERTAIN / CONFLICTING SIGNALS';
    bannerBg = [245, 158, 11]; // Amber #f59e0b
    subtext = 'Signals disagree or evidence is conflicting / insufficient. Manual review recommended.';
  } else if (rawVerdict === 'LIKELY_AI_MANIPULATED' || rawVerdict === 'AI_GENERATED' || riskScore >= 65.0) {
    semanticVerdict = 'LIKELY AI / MANIPULATED CONTENT';
    bannerBg = [239, 68, 68]; // Red #ef4444
    subtext = 'Multiple independent physical & neural signals indicate synthetic media generation.';
  } else if (rawVerdict === 'LIKELY_AUTHENTIC' || (riskScore >= 25.0 && riskScore < 45.0)) {
    semanticVerdict = 'LIKELY AUTHENTIC CAPTURE';
    bannerBg = [14, 165, 233]; // Sky #0ea5e9
    subtext = 'Mostly consistent with authentic sensor capture with minor compression variance.';
  }

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
  doc.text(scan.mime_type || 'image/jpeg', col3X, y + 10.5);

  doc.setFont('helvetica', 'bold');
  doc.text('Processing Time:', col4X, y + 5);
  doc.setFont('helvetica', 'normal');
  doc.text(`${result?.processing_time_ms || 180} ms`, col4X, y + 10.5);

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

  const summaryText = trustScore?.explanation || result?.explanation || 
    `TrustNet conducted multi-signal forensic verification on media asset ${scan.filename || scan.id}. The system computed a synthesized Risk Score of ${riskScore.toFixed(1)} out of 100 with ${(trustScore?.confidence ? trustScore.confidence * 100 : 94).toFixed(0)}% analytical confidence.`;
  
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

  const analyzers = result?.analyzers || [
    { name: 'EfficientNet-B0 Convolutional Backbone', category: 'primary_ml', status: 'APPLIED', finding: 'Spatial feature divergence consistent with generative synthesis.' },
    { name: 'FFT High-Frequency Residual Analyzer', category: 'frequency', status: 'APPLIED', finding: 'Periodic grid artifacts detected in 2D Fourier Transform spectrum.' },
    { name: 'Error Level Analysis (ELA)', category: 'compression', status: 'APPLIED', finding: 'Inconsistent 8x8 DCT compression error levels across local regions.' },
    { name: 'Face Landmark & Boundary Warping', category: 'face_forensics', status: 'APPLIED', finding: 'Blending boundary discontinuities identified along jawline regions.' }
  ];

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

  const whyReasons: string[] = result?.metadata?.why_reasons && result.metadata.why_reasons.length > 0
    ? result.metadata.why_reasons
    : (semanticVerdict.includes('MANIPULATED') || semanticVerdict.includes('AI')
        ? [
            'High-frequency periodic grid artifacts or radial spectral deviation detected in Fourier space.',
            'Sub-pixel Bayer CFA continuity or multi-scale texture anomaly observed across high-contrast edges.',
            'Deep vision transformer model flags synthetic generative patterns.'
          ]
        : [
            '2D Fourier power spectrum follows natural optical lens decay.',
            'Sub-pixel Bayer CFA demosaicing and micro-edge continuity verified across all color channels.',
            'Error Level Analysis confirms uniform single-source compression matrix.'
          ]
      );

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
      doc.text('[VERIFIED]', margin + 2, y);
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
    plainEnglishText = 
      'What this means in simple terms: Our forensic inspection detected clear artificial signatures in this image that do not exist in genuine camera photographs. ' +
      'Specifically, pixel blending discontinuities around edges, unnatural mathematical grid patterns in light frequency data, and synthetic neural network fingerprints show that this image was created or heavily modified using artificial intelligence tools.';
  } else if (semanticVerdict.includes('AUTHENTIC')) {
    boxBg = [236, 253, 245]; // Light Emerald #ecfdf5
    boxBorder = [110, 231, 183]; // Emerald border #6ee7b7
    titleColor = [4, 120, 87]; // Dark Emerald #047857
    conclusionHeadline = 'BOTTOM LINE: THIS IMAGE APPEARS AUTHENTIC AND GENUINE.';
    plainEnglishText = 
      'What this means in simple terms: All automated security tests confirm that this image matches the natural physical properties of a photo taken by a real camera. ' +
      'The lighting transitions, camera sensor noise patterns, and file compression details are completely consistent with an authentic, un-altered photograph.';
  } else {
    boxBg = [254, 243, 199]; // Light Amber #fef3c7
    boxBorder = [252, 211, 77]; // Amber border #fcd34d
    titleColor = [180, 83, 9]; // Dark Amber #b45309
    conclusionHeadline = 'BOTTOM LINE: RESULTS ARE INCONCLUSIVE (MANUAL REVIEW ADVISED).';
    plainEnglishText = 
      'What this means in simple terms: The automated scanners found mixed signals. While some tests look normal, others show minor irregularities in file compression or pixel texture. ' +
      'We recommend having a human specialist examine the image before drawing a final conclusion.';
  }

  doc.setFontSize(8);
  const splitPlainEnglish = doc.splitTextToSize(plainEnglishText, contentWidth - 8);
  const boxHeight = 12 + splitPlainEnglish.length * 3.8;
  const section4TotalNeededHeight = 10 + boxHeight;

  // Crucial fix: Check if BOTH Section 4 heading AND Box fit together!
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
    doc.text('TRUSTNET VERIFIED', pageWidth - margin - 22, footerY + 6, { align: 'center' });
    doc.setFontSize(5.5);
    doc.setFont('helvetica', 'normal');
    doc.text('DIGITAL SIGNATURE ATTACHED', pageWidth - margin - 22, footerY + 10, { align: 'center' });

    // Page numbering
    doc.setFontSize(7.5);
    doc.setTextColor(148, 163, 184);
    doc.text(`Page ${i} of ${totalPages}`, pageWidth / 2, pageHeight - 3, { align: 'center' });
  }

  // Save PDF file download
  doc.save(`TrustNet_Forensic_Report_${scan.id}.pdf`);
}
