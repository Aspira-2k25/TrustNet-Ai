# Image Deepfake Service (services/image_deepfake)

Worker and direct API service for image-forensics inference.

## Endpoints

- `POST /detect/file` - run detector on uploaded image
- `POST /detect/key` - run detector by storage key
- `GET /health`

## Responsibilities

- Runs multi-signal image forensic detection via `EfficientNetDetector`.
- Integrates 15 forensic modules:
  - 2D Fourier (FFT) Power Spectrum (1/f^alpha natural lens decay)
  - Sub-pixel Bayer CFA demosaicing & micro-morphing
  - Multi-Scale Gabor Texture Filter Bank (8 kernels across 4 angles)
  - JPEG Quantization Error Level Analysis (ELA)
  - Camera Sensor Pattern Noise (PRNU)
  - Face X-Ray Facial Boundary Step Gradients
  - Corneal Specular Reflection Physics (3D lighting parallax)
  - 3D Geometry Support & Symmetry
  - Generative Watermark Icon Scanner (convexity defect pointedness)
  - Social Recompression & 8x8 DCT Grid Boundary Analysis
  - Provenance & AI Metadata Scanners (50+ known generator signatures)
  - Vision Transformer (ViT) & EfficientNet-B0 Convolutional Backbone
  - LM Studio Local Vision Semantic Reasoning (Qwen3-VL local inference)
- Supports direct synchronous REST inference (`POST /detect/file`) with full CORS enabled.
- Consumes Kafka events in background thread when `ENABLE_KAFKA_CONSUMER` is active.
- Emits structured `DetectorCompletedEvent` events with full forensic telemetry.

## Kafka

- Consumes: `detection.requested.image_deepfake`
- Consumer group default: `trustnet_image_deepfake_group`
- Toggle: `ENABLE_KAFKA_CONSUMER` (default true)

## Runtime Defaults

- Port: `8003`
- Kafka default: `localhost:9092`
- Storage fallback: `./storage_uploads`

## Run Locally

```bash
pip install -r services/image_deepfake/requirements.txt
uvicorn services.image_deepfake.app.main:app --port 8003 --reload
```

## Tests

```bash
python -m pytest services/image_deepfake/tests -v
```
