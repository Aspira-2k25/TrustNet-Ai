# Phishing URL and message fusion figures

The editable PowerPoint contains exactly two methodology diagrams. Text, boxes and arrows are native objects. The white background and black lines are suitable for print and Canva import.

1. **Phishing URL methodology:** URL validation, text and structural branches, baseline/correction experts, routing, alert rescue, local rules and optional website collection.
2. **Scam message and URL fusion:** website/Gmail inputs, authenticated scan management, separate text and URL assessment, decision fusion, saved results and explicit link inspection.

Use the individual vector PDFs in a paper. Each is 180 mm wide, with the same layout as the PowerPoint. The PNG exports are 2400 by 2976 pixels. Use the figure across the page or both columns to keep labels readable. Avoid taking a screenshot of a slide.

Example Overleaf inclusion after uploading the individual PDFs:

```latex
\begin{figure*}[t]
  \centering
  \includegraphics[width=\textwidth,height=0.84\textheight,keepaspectratio]{Phishing_URL_Methodology.pdf}
  \caption{Phishing URL assessment in TrustNet AI. URL text and structure feed the selected expert policy. Explicit website inspection adds available network and static page evidence.}
  \label{fig:url-methodology}
\end{figure*}
```

For the second figure, use `Scam_Message_URL_Fusion_Methodology.pdf` and this caption:

> Scam message and phishing URL decision fusion in TrustNet AI. Website and Gmail inputs share the authenticated backend. The system retains separate model outputs, applies a conservative warning policy and stores the result with link coverage. Explicit inspection saves a separate website evidence snapshot.

The selected URL runtime is `regional-recall-v1`. Its two text pipelines use TF-IDF and SGDClassifier. LightGBM handles lexical structure, while histogram gradient boosting and isotonic calibration form the baseline/correction experts. Routing and rescue use versioned boundaries rather than one universal threshold. The message runtime is `message-distilbert-lexical-links-hybrid-4`, using DistilBERT, TF-IDF/Logistic Regression and 14 literal URL structure features.

Solid lines show the default inference path. Dashed lines show explicit website inspection. Quick embedded-link inference does not fetch the destination. Live collection does not execute JavaScript or submit forms. An inspection snapshot retains its timestamp and does not overwrite the quick message result.

Fusion means decision combination after separate assessments. Its maximum risk index is not a calibrated probability. The frozen source comparison increased recall but also increased false positives and reduced F1. These figures do not claim improved accuracy. See `docs/message-url-fusion.md` for measured results and limitations. Automated extension adapter/API tests passed; a live Gmail installation test was skipped, and support for every browser is not established.

Speaker notes in the PowerPoint record the source files and additional implementation detail. No application code, model weights or thresholds were changed to create these figures.
