# Reading the phishing report

The detector verdict and risk index remain unchanged. The opinion is a qualitative interpretation of existing evidence, not another classifier, probability or independent vote.

The default view now describes the particular URL's recorded observations and a conclusion. Generic model internals and feature tables are collapsed. PDF export uses the same per-URL summary.

## Scores and confidence in the phishing report

Risk is the existing risk index (higher means riskier). The phishing report's displayed trust score is `100 - risk` (higher means less detected risk). This is a display transformation, not independently verified trust or a probability of authenticity. The shared backend field `trust_risk_score` retains its original higher-means-risk semantics; other modules are unchanged.

Assessment confidence is qualitative evidence strength, not a measured prediction probability. Incomplete assessments have unavailable confidence. A recent qualifying exact-URL reputation report provides strong supporting evidence. Substantial branch disagreement (difference of at least 0.40), a model estimate within 0.05 of its threshold, or fewer than four core observed checks yields limited confidence. Otherwise evidence is described as moderate. These presentation rules are not independently calibrated, and observed checks can contain adverse results. Check coverage is not presented as an accuracy percentage.

For example, structure 7.6%, text 99.0% and ensemble 69.9% against a 70% threshold is explicitly described as borderline with conflicting model signals and limited confidence. Being below the threshold does not make it clearly legitimate.

- A strong forensic indicator or a model estimate crossing the recorded alert threshold produces a phishing leaning.
- Medium concerns produce a suspicious leaning, even when the model is below threshold.
- A legitimate leaning requires a model estimate below half its recorded alert threshold, no medium/high findings, and at least three observed core checks. This is a presentation heuristic, not validated confidence or ownership verification.
- Borderline estimates or limited collection retain only a weak legitimate-pattern leaning; missing estimates and incomplete assessments cannot support a recommendation.

The main uncertain verdict stays uncertain. Model feature measurements are not causal attributions. Character alignment explains differences between the actual registered domain and the similar reference domain, including insertions, deletions and Unicode code points. Canonical names may be lowercased or punycode; this is not a claim that the original letter casing is suspicious. A similar reference is not authenticated affiliation.

## Current threat source

PhishStats is already integrated in the isolated collector. Matching is exact URL matching after documented normalization, not a blanket hostname blacklist. A qualifying report is at most seven days old with provider score at least seven. Cached results can be up to 90 minutes old. The report shows provider, scope, report identifiers and timestamps. A fresh match means known reported phishing, not an infallible claim. Historical/no-match/unavailable results are distinct. No-match is never a safe certificate. URLs in evidence remain inert text.

## Suggested improvements

1. Add a second independent phishing source, such as PhishTank's verified-online feed (https://phishtank.org/developer_info.php). Preserve per-source status, verification date, exact URL scope and freshness; avoid counting mirrored feeds as independent corroboration. Provider access must be configured before claiming it is connected.
2. Validate uncertainty and combined-index calibration on an independent, time-separated dataset. Include hard legitimate negatives, new domains and lookalikes; measure precision/recall and review-band error rates.
3. Add campaign-level evidence and isolated rendered-page inspection for JavaScript-only phishing. This requires a separate sandbox, resource limits and public-address checks at every navigation step; do not execute forms or credentials.
4. Record feed freshness, provider outages and cache expiry operationally. Display stale evidence rather than silently treating it as current.
5. Add validated model attribution so the report can distinguish a measured URL property from a demonstrated influence on the model prediction.

URLhaus (https://urlhaus.abuse.ch/api/) covers malware distribution; its policy excludes phishing. It may supplement a separately labeled malware check but should not be presented as phishing corroboration.
