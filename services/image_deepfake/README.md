# Image Deepfake Worker Service

The **Image Deepfake Worker** is the core heavy-lifting microservice of the TRUST[NET] architecture. It subscribes to the `detection.requested.image_deepfake` Kafka topic and processes incoming raw image bytes through 9 parallel scientific forensic analyzers.

## Technology Stack
- **Framework**: FastAPI, Python 3.10+
- **Deep Learning**: PyTorch (EfficientNet-B0), Torchvision, Facenet-PyTorch
- **Computer Vision**: OpenCV, Pillow, Numpy
- **Message Broker**: `aiokafka` (KRaft Mode)
- **External API**: Hugging Face Hub (`transformers` pipeline)

## The 9-Layer Forensic Logic

This worker does NOT just use a simple deep learning model. It fuses multiple independent physical and statistical domains to catch AI synthesis.

### Artifact-Based Branches
1. **EfficientNet-B0**: Extracts deep spatial feature divergence.
2. **Hugging Face ViT**: Semantic vision transformer classification.
3. **Sub-Pixel Morphing**: Detects Color Filter Array (CFA) Bayer lattice interpolation failure.
4. **Fourier (FFT)**: Detects radial power spectrum decay anomalies.
5. **ELA (Error Level Analysis)**: Detects localized 8x8 DCT recompression artifacts.
6. **PRNU Noise**: Extracts Laplacian sensor pattern noise residues to check hardware silicon consistency.
7. **Face X-Ray**: Uses skin-color segmentation and boundary variance to detect periocular blending.

### Physics-Based Branches
8. **Optics Physics (Corneal Specular Reflection)**: Analyzes light reflection vectors in human eyes to detect asymmetrical/impossible light sources.
9. **Geometry Physics (Support & Symmetry)**: Uses ORB feature matching and Canny edge density to detect floating objects (missing contact shadows) and severe structural asymmetry.

## Execution Flow
1. **Consume**: Receives a `DetectionRequest` from Kafka.
2. **Process**: The `EfficientNetDetector` feeds the image to all 9 analyzers.
3. **Fusion**: Analyzers are weighted. For example, if an image is classified as Digital Art, PRNU (Camera Noise) weight is reduced, while Hugging Face and FFT weights are increased.
4. **Publish**: Packages the result as a `DetectionResult` and publishes to the `detector.image_deepfake.completed` Kafka topic.
