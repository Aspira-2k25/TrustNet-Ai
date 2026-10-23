# Image service

- POST /detect/file: authenticated bounded still-image screening.
- POST /detect/key: forbidden publicly; internal workers use contained relative storage keys.
- GET /health: process liveness.
- GET /ready: selected model/localization runtime readiness, separately reporting decision-policy validation.

Default port 8003. The default policy is `image-vit-v3`, using the existing local face ViT without CNN weights. No detected assessable face means unsupported; missed faces remain possible. A loaded model can be ready while decisions remain review-required pending independent validation.

Kafka and direct scan routes share the detector contract. Original uploads are not retained by direct scanning. See [current operations](../../docs/image-vit-v3.md) for evaluation, candidate installation, promotion and rollback. `image-screening-v2` is an explicit historical CNN policy, not the default.
