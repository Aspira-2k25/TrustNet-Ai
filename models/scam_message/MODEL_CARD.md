# Selected message policy: multilingual lexical v1

The default CPU runtime now uses a small word and character TF-IDF logistic model for supported English/Hinglish short messages, explicit request rules, and the existing embedded-URL branch. The old DistilBERT mixture is an optional rollback, not the default detector. `SCAM_TEXT_POLICY=legacy` also requires the separately supplied old model package and `requirements/scam-legacy.txt`.

Selected weights and vocabulary are included in Git at `multilingual_artifacts/`, about 1.5 MB total, with SHA-256 checks before loading. Loading uses JSON/NPZ, never pickle. Training and inference share NFKC/case/URL/email/number normalization. Language routing reads the text, never the source language annotation. Readings are not calibrated probabilities; confidence is unavailable. Messages longer than the trained 1,800-character view remain explicitly incomplete, while full-message rules still run.

## Data, selection and release gate

Source: `sidzzz07/scamshield-dataset`, revision `059dee884476a45e380808e68d09e74baff67291`, MIT according to its dataset card. Underlying source rights and label quality are not independently established. Raw messages remain outside the repository. There are 5,215 training examples, 412 validation examples and 492 reserved test examples after the stated selection. Normalized template groups present in the original validation/test collections or earlier comparison are excluded. Conflicting normalized labels are discarded. Groups are disjoint across the new splits; numbers, URLs and email addresses are replaced before grouping and feature extraction. This does not eliminate every semantic paraphrase or unknown upstream English training overlap.

An initial offline comparison incorrectly used the dataset language annotation for routing. That comparison is invalid for runtime. It was corrected to text-only routing and thresholds were reselected on validation, without fitting to test outcomes. The 492-row test has now been consumed. A separate ten-message synthetic hard-negative release gate rejected standalone Hindi classification after two false warnings on normal OTP/delivery notices. Hindi therefore keeps limited explicit rules and uncertainty, not the new head's standalone decisions. MuRIL's earlier same-split small comparison remains rejected because of benign false alerts; its headline score is not attributed to this model.

## Actual API comparison

These are detector-branch warnings, including rules and assessed links. They are not final presentation recall when checks are missing.

| Frozen diagnostic | Prior recall | Selected recall | Prior precision | Selected precision | Prior F1 | Selected F1 | Prior FPR | Selected FPR |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 492 reserved public-source records | 48.83% | 82.81% | 87.41% | 100.00% | 62.66% | 90.60% | 7.63% | 0/236, 0.00% |
| Previously consumed 800-record audit | 53.50% | 94.50% | 96.40% | 98.44% | 68.81% | 96.43% | 2.00% | 6/400, 1.50% |

Selected branch FPR 95% Wilson intervals are 0–1.60% on the 492 set and 0.69–3.23% on the 800 set. Zero observed errors is not a guarantee. The 800 set has scarce Hindi/Hinglish positives, public label noise and previously inspected examples. Neither set establishes field accuracy. There is no claim of an untouched independent production certification.

The final public contract deliberately reports incomplete when required link checks fail or lack coverage, even if the message branch warns. On 492 records its warning recall is 46.48%, precision 100%, F1 63.47%, FPR 0/236 and not-sure/incomplete share 47.15%. On 800 records its warning recall is 66.50%, precision 99.25%, F1 79.64%, FPR 2/400 (0.50%, 95% interval 0.14–1.80%) and not-sure/incomplete share 28.00%. Warning evidence remains visible in reasons; missing checks never become safe. Do not replace these UI figures with head-only or branch recall.

CPU API p50/p95 were 0.031/0.906 seconds (492) and 0.016/0.703 seconds (800), on the developer machine under concurrent load, not controlled hardware benchmarks. Outputs and split manifests remain external; compact aggregate records are in `benchmark/results/reference-evaluation.json`.

## Important limits

Hindi standalone inference, new scam styles, quoted instructions, mixed scripts, long email context, source label noise and unfamiliar domains remain difficult. The model does not verify the sender, SPF/DKIM/DMARC, intent or AI authorship. Local inference needs no API key. Optional provider summaries do not change predictions. Live Gmail extraction was not tested, as requested.

## Historical DistilBERT rollback evidence

Everything below describes the earlier model and its old evaluation, not the selected default above.

# Selected model: message-distilbert-lexical-links-hybrid-4

Current runtime adds explicit rule warnings and language coverage handling. The accuracy figures below are historical selected-weight results, not a measurement of the changed runtime. The small multilingual comparison and current limitations are recorded in `benchmark/results/reference-evaluation.json`. Live Gmail extraction remains unverified. Image and message PDF downloads were verified in the browser with a synthetic local QA account.

Local three-class English SMS/email screening: ham, phishing/smishing/fraud (legacy class name `smishing`), and unsolicited spam. Sender verification and AI authorship are not implemented. Contemporary inbox reliability and multilingual/Hinglish performance are not established.

Selected mixture: 50% refined DistilBERT and 50% word/character TF-IDF logistic regression with 14 literal URL features. Training-fitted vocabulary/IDF/scales; no external URL requests. Semantic temperature 1.391455493, lexical temperature 0.811629986, mixture temperature 0.789818328; validation-selected fraud alert threshold 0.450. Threshold alerts and class argmax are different measures.

Selected safetensors SHA-256: `1a47b442ad8c847cbc1a78a0cd00cae344c57ae15ae3291f22997630c5cfe3a9`. Initialization, source attribution, training plan, label mapping and file hashes are in `artifacts/manifest.json`. Base DistilBERT revision `714eb0fa89d2f80546fda750413ed43d93601a13`, Apache-2.0. Original SMS fine-tuning was reused; English scam-email domain adaptation and bounded contextual correction trained upper layers. Fictional augmentation is training/diagnostic material, never independent accuracy evidence. The original version-2 model is retained through `rollback-package.json` and its separate archive.

Frozen corrective holdout: 577 records, 200 ham / 299 fraud / 78 spam. SHA-256 `7d603fa40e23118d11876cf5c8ccdd3b255c6ca1d488951323f566a6bc49a648`. Audited exact/normalized/near-template overlap; split fixed before corrective training. Different held-out records/years from the same collection families, not a prospective field study. Earlier 929-message holdout and previously inspected benchmarks are now diagnostic.

Accuracy 97.4003%; macro-F1 0.964667; threshold fraud recall 286/299 (95.65%). Actual covered verdicts detect 284/299 (94.98%): 270 likely scam and 14 threshold-qualified suspicious. Eight other fraud examples receive uncertainty-only review; they are not counted as detected. Six examples abstain. Ham fraud alerts 0/200: observed 0%, 95% Wilson upper bound 1.88%. Spam fraud alerts 0/78: upper bound 4.69%. Zero observed errors does not prove a zero field error rate.

Compared on these same 577 records, version 3 had macro-F1 0.965528, fraud recall 98.33%, and ham alerts 3/200 (1.5%). Corrective selection prioritizes resolving severe constructed OTP/receipt false positives with lower observed ham FPR; it trades off fraud recall and does not improve final macro-F1. Full per-class/confusion/calibration/PR/coverage/source/ablation tables are in `models/scam_message/evaluation/selected-weights-historical.json`.

Remaining quality limits: the older PhishNet diagnostic macro-F1 is 0.5561 versus version-2 0.5941, despite improved alert recall 70.46% versus 45.56%. Prior curated email diagnostic fraud recall is 77%, ham fraud FPR 6%. Reliable contemporary genuine-promotion FPR is not established; 19 historical promotions are now diagnostic and too small. A constructed 8,450-character mixture with one fraud request among repeated benign text received only 14.52% risk: all windows were processed, but mean-window/whole-message fusion diluted the fraud signal. No final-label tuning or whitelist was used to hide these weaknesses.

Accepted input bounds: 10,000 canonical Unicode characters; all 384-token windows with stride overlap 64, mean logits. Size/extraction exclusions narrow corpus coverage. Signed occlusion recomputes the full deployed probability, including the lexical/link mixture, within a partial 3-second budget. No human utility or causal explanation claim. Model CPU/GPU equivalence, numerical explanation fidelity, actual authenticated API/persistence, browser report/PDF and Kafka completion/replay/failure flow were verified with this selection. Extension fixtures and actual worker/API communication are verified; live Gmail remains pending user setup.

Install the separately shared selected model archive using `scripts/setup/install-scam-model.py`; `model-package.json` records the exact archive and per-file checksums. No undeclared Hugging Face cache, external `scam/` folder, Git LFS or Groq key is needed. See the root `README.md` and `licenses/scam/THIRD-PARTY-NOTICES.md`.


## Expanded current-API diagnostic, 21 October 2026

A frozen public-source set of 800 messages, 400 scam and 400 normal, was evaluated before and after the scoped secret-request negation fix. Both runs produced 214 true scam warnings, 8 false warnings, recall 53.50%, precision 96.40%, F1 including abstentions 68.81%, normal false-warning rate 2.00%, and uncertain share 28.125%. There were zero service errors in either run. The fix changes specific verified Hinglish negation cases but did not change any verdict on this selected set; no aggregate accuracy improvement is claimed. Weights and model thresholds were unchanged.

The diagnostic has 659 English, 104 Hindi and 37 Hinglish messages. Hindi scam recall was 0/4 and all Hindi outputs were uncertain. Hinglish scam recall was 3/25. These reveal weak broad multilingual coverage; they do not support a claim that Hindi/Hinglish scams are solved. The English recall was 211/371 (56.87%). The historical 97.4% selected-weight accuracy belongs to its earlier cohort and cannot substitute for this result.

Source: `sidzzz07/scamshield-dataset`, revision `059dee884476a45e380808e68d09e74baff67291`, official test partition, excluding general spam positives and exact normalized-text duplicates. The source card declares MIT; upstream source rights and annotation quality still apply. Fifty selected examples had already appeared in the earlier multilingual comparison. Unknown English training overlap, synthetic templates, noisy labels and scarce minority-language positives prevent independent field-accuracy claims. No new classifier was promoted from this audit. Raw messages remain external.

Before/after request p50/p95 were 1.79/4.05 seconds and 1.23/2.81 seconds respectively, under varying developer CPU load. This was not a controlled speed comparison. Main API regression checks confirm that `Aapka KYC nahi hua, apna OTP bhejo abhi` now warns, while `OTP kabhi share mat karna` does not create a secret-request warning. The rule policy is recorded as `secret-negation-v2`; rule warnings are not calibrated probabilities.
