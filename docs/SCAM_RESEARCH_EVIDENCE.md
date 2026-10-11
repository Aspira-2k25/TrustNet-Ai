# Scam research evidence and limits

This record distinguishes published results, local adaptations, and product evaluation. It is not a claim of publication readiness. Local inference, calibrated class probabilities, literal URL features, and optional Groq evidence ordering are ordinary engineering combinations; this work does not establish a novel algorithm. Groq does not change the local verdict.

## Primary papers

Agrawal et al. (2023), DOI 10.1109/I2CT57861.2023.10126300, describes TF-IDF/NB/random-forest/extra-trees spam screening followed by URL checking. Reported figures differ between abstract, tables and conclusion (approximately 96–98% accuracy). Its exact fusion rule and operational URL-check policy are underspecified. Our local equal-vote comparison is an adaptation, not an exact reproduction, and does not send message URLs to VirusTotal.

Mehmood et al. (2024), DOI 10.1109/ACCESS.2024.3463871, describes classical and CNN–LSTM models on combined Mendeley/Kaggle spam data. Spam and smishing are merged into a positive class. Table 6 reports 99.74% accuracy; the listed confusion counts imply approximately 99.68% over 11,545 examples, a population different from the stated 20% test partition. This ambiguity does not establish misconduct. A binary spam detector's accuracy is not a three-class fraud detector's accuracy.

Local grouped UCI binary holdout: 1,033 messages, 917 ham and 116 spam. TF-IDF equal voting achieved 97.48% accuracy / 0.9299 macro-F1, with zero ham false positives and 22.41% spam misses. The adapted CNN–LSTM achieved 97.97% / 0.9472, with 0.65% ham false positives and 12.93% spam misses. Vocabulary and preprocessing were fitted on training examples only. The CNN adaptation used bounded sequence length and early stopping, rather than claiming the paper's exact training protocol. These results cannot be compared directly with the published combined-corpus percentage.

## Product data and distribution

Runtime artifacts contain selected weights, tokenizers, preprocessing/label definitions, temperatures, thresholds and checksums. Raw datasets, source emails, paper PDFs, authored training/challenge messages and experiment outputs remain in the external `scam/` workspace and are not runtime dependencies or distributed with the application.

DistilBERT base provenance: `distilbert/distilbert-base-uncased-finetuned-sst-2-english`, revision `714eb0fa89d2f80546fda750413ed43d93601a13`, Apache-2.0. Mendeley SMS data and Nazario phishing collections require CC BY 4.0 attribution. SpamAssassin public corpora retain their original authors' copyrights; public availability is not a blanket CC license. No raw source emails or corpus copies are included in model packages. Original corpus labels are retained: ordinary spam is not automatically relabelled as credential theft or financial fraud.

Exact and normalized template groups, class conflicts, and character n-gram near matches were audited across development and test partitions. Collection-level overlap audits reduce contamination but cannot prove independence from all historical sources or correlated campaigns. Raw/canonical size bounds exclude substantial long HTML mail; measured performance describes accepted messages, not every original corpus item. Synthetic augmentation and its challenge set are explicitly fictional and never evidence of real-world accuracy.

## Retained results and corrective work

The preserved version-2 baseline was weak on independent-source scam messages: PhishNet macro-F1 0.5941 and alert recall 45.56%; the previously inspected email set had only 36% alert recall. These weaknesses were not concealed.

Version 3 was selected using separate training, validation and calibration data before a 929-message audited holdout. On that holdout it achieved macro-F1 0.8226 and threshold-based fraud recall 99.21%, but legitimate-message false positives were 4.57%, exceeding the 1% validation target. Runtime coverage and verdict policy reduce its actual detection counts; raw threshold recall alone overstates deployed performance. The holdout's 19 manually annotated historical promotions had zero fraud alerts, with a wide 95% Wilson upper bound of 16.82%; this is not proof of reliable modern promotion screening.

On the older, already inspected PhishNet diagnostic population, version 3's macro-F1 fell to 0.4897 despite higher fraud alert recall (78.13%). This is a measured regression in category discrimination. Subsequent integration checks also exposed serious false positives on constructed benign OTP and receipt warnings. Version 3 therefore cannot be described as a completed quality improvement.

A separate 577-message holdout was frozen and audited before corrective fitting (SHA-256 `7d603fa40e23118d11876cf5c8ccdd3b255c6ca1d488951323f566a6bc49a648`). The earlier 929 examples and inspected benchmarks are now diagnostic. This new holdout uses different held-out records/years from the same broad source families; it is not a wholly new independent provider or a field deployment. Corrective lexical fits and contextual checkpoint refinement reuse prior training and add paired benign-warning/fraud-request examples. A predefined diagnostic gate rejects hiding high benign fraud probability by merely raising the alert threshold. Corrective selection and frozen evaluation completed. Version 4 achieved macro-F1 0.9647, fraud threshold recall 95.65%, and ham fraud alerts 0/200. Version 3 on the same population had macro-F1 0.9655, recall 98.33%, and ham alerts 3/200. The reduction in benign alerts trades off fraud recall; final macro-F1 did not improve. The 95% Wilson upper bound for 0/200 ham alerts is 1.88%, so the observed zero does not establish a sub-1% field rate. No final outcome was used for retuning.

## Explainability and unavailable claims

Evidence spans use signed changes in the model's fraud probability when bounded spans are masked. This measures model sensitivity, not causal truth or human understanding. Long-message windows cover the full accepted canonical text; expensive attribution can stop at its explicit time budget without silently truncating initial inference. Literal URL features inspect strings locally and do not establish domain ownership, reputation or sender identity. Placeholder URLs in public SMS collections can be a source-specific shortcut and limit portability.

Sender identity is unverified and AI authorship is not assessed. No multilingual/Hinglish quality claim, human utility study, contemporary inbox field study or comparable labelled image accuracy is established. Source labels may contain errors. False-positive rates on small benign/promotion populations need confidence intervals and more diverse prospective data.


Version-4 replay retains limitations: PhishNet macro-F1 0.5561 (below version-2 0.5941), alert recall 70.46%; prior curated-email fraud recall 77%, ham alerts 6%. The 929 previously inspected records now have diagnostic macro-F1 0.8257, fraud alert recall 97.63%, ham alerts 1/197. Long-message inference covers all windows but a constructed benign-dominated 8,450-character example with a fraud request was missed at 14.52% risk. Modern promotion false positives and explanation human utility remain unestablished.
