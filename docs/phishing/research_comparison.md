# Reference comparison — Phase 0

Reference: BGL-PhishNet, DOI https://doi.org/10.1109/ACCESS.2025.3551542. Publisher DOI access failed during this audit. An author-version excerpt is discoverable at https://www.researchgate.net/publication/389854613_BGL-PhishNet_Phishing_Website_Detection_Using_Hybrid_Model-BERT_GNN_and_LightGBM; full methodological reproduction has not been verified.

The inspected author excerpt describes BERT for linguistic inputs, a URL-structure GNN and LightGBM, with validation/cross-validation-derived weighted voting. It also describes URLs, subdomains and paths as graph components. Exact tokenizer revision, labeled text serialization, graph edge construction, domain-disjoint split methodology and executable training code remain unverified. Do not invent these details or borrow paper metrics as TrustNet measurements.

The supplied plan intentionally stages LR/RF baselines → separately trained LightGBM+BERT → two-branch weighted voting/calibration → later GNN. This is a staged project adaptation, not an existing three-branch reproduction. Compare branch-only versus fused results on the same fixed primary partitions, with domain-safe folds and metadata coverage reporting. Record every divergence from the source when the full reference is reviewed.
