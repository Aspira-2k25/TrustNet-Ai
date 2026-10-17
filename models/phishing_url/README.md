# Phishing detection module

The active deployment is `checkpoints/modern_v5/manifest.json`: masked URL text, structural features, learned fusion and calibration, supplemented by URL forensics, visual-domain comparison and the isolated live collector. Start it with `scripts/start-phishing-infrastructure.ps1`; no CUDA is required. Current behaviour and limits are documented in `docs/phishing/model_card.md`, `forensics.md` and `link-inputs-and-lookalikes.md`.

The active bundle's four manifest-listed components, domain/confusables reference and license notices must be retained. Training data, the structural-v3 retraining dependency, referenced research experiments and explicitly supported older bundles are retained for reproducibility/rollback. The 17 October cleanup removed the rejected unmasked-v4 runtime/trainer/weights, a duplicate non-resumable progress checkpoint and superseded debug output/screenshots. The exact removal list is in `research/cleanup-2026-10-17.json`.

## Historical training workflows

Requirements, dataset gates and research comparison are in `docs/phishing/`. Overall progress is in root `track.md`.

Pure model code never performs external collection or imports service infrastructure. `preprocessing/url_parser.py` validates URLs without accessing them. `extract_features.py` supplies the same ordered lexical features at training and inference. The trained hybrid combines LightGBM lexical features with BERT URL classification, validation-selected voting, isotonic calibration and calibrated branch fallbacks. It does not reproduce the 30-feature UCI extractor.

Audit the official UCI archive with:

```powershell
python -m models.phishing_url.research.audit_uci models/phishing_url/data/uci/source.zip models/phishing_url/research/uci_audit.json
```

The official UCI target dictionary is unresolved. Its audit reports original labels without assigning meaning. The offline experiment is executed with explicit -1=phishing and +1=legitimate and is documented as conditional on that research-supported mapping. It deduplicates feature vectors, excludes conflicting vectors and records ten-fold development plus frozen test metrics. Domain/time generalization is unmeasurable from this archive. UCI artifacts must never be loaded as raw-URL models.

Raw-URL baseline training (after primary dataset gates close):

```powershell
python -m models.phishing_url.training.train_baselines dataset.csv models/phishing_url/checkpoints/baseline
```

Input CSV uses url,label,domain_group,split. Each partition must have both classes and every domain group must stay in one partition. Caller-supplied groups must come from a frozen Public Suffix List and undergo campaign-overlap review; the trainer cannot verify arbitrary group names. Do not treat synthetic test fixture metrics as model quality.

Prepare the approved Kaggle version 1 archive first:

```powershell
python -m models.phishing_url.training.prepare_primary models/phishing_url/data/primary/source.zip models/phishing_url/data/primary/metadata.json models/phishing_url/data/primary/prepared
```

This command never fetches submitted URLs. It uses tldextract's bundled PSL offline, includes private suffixes and records the package version/snapshot hash. Normalized duplicates collapse, conflicting URL labels are quarantined, invalid/unknown-suffix rows are counted, and scheme-less rows retain their original text with an explicit inferred-scheme flag. A grouped fifth is held out for test before ten development folds are assigned. Fold 0 is the initial baseline validation partition; folds 1–9 train that baseline. Later cross-validation must refit each learned component per fold. Per-row timestamps and campaign identifiers are unavailable; those generalization claims remain unmeasured.

Only trusted locally produced joblib files may be loaded. The schema/checksum validation prevents accidental bundle mismatch; it does not make untrusted pickle data safe. Runtime needs artifacts, not training CSVs. Baseline probabilities are uncalibrated and evidence is observational. LR/RF primary artifacts are separate from UCI/Mendeley experiments.
