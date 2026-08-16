# TRUST[NET] Image Deepfake Detection Service

This microservice provides an advanced, multi-signal scientific pipeline for detecting AI-generated images and deepfakes.

## The Architecture (Artifact + Physics Fusion)

Modern AI image generators (like Midjourney V6, DALL-E 3, and Stable Diffusion) are becoming increasingly skilled at eliminating pixel-level artifacts. To combat this, this service uses a **Two-Pronged Detection Strategy**:
1. **Artifact-Based Forensics**: "Does this look like known AI/fake patterns?"
2. **Physics-Based Forensics**: "Does this obey real-world physical constraints?"

These two domains are processed by 9 specialized forensic analyzers and fused together in the `efficientnet_detector.py`.

### 1. The Technology Stack
- **Framework**: FastAPI, Python 3.10+
- **Deep Learning**: PyTorch, Torchvision (EfficientNet, MTCNN via facenet-pytorch)
- **Computer Vision**: OpenCV, Pillow
- **AI Backend**: Hugging Face `transformers` (ViT pipelines)
- **Message Broker**: Kafka (for async inter-service communication)

---

## 2. Core Forensic Modules (Artifacts & Machine Learning)

### EfficientNet-B0 Convolutional Backbone
Extracts deep spatial feature embeddings. AI models leave microscopic generative fingerprints (checkerboard artifacts from upsampling, transposed convolutions) that are invisible to the human eye but easily detected by CNNs trained on natural images.

### Hugging Face Transformer Integration
Connects to state-of-the-art vision transformers (e.g., `prithivMLmods/Deep-Fake-Detector-v2-Model`) to process global semantic structures and classify the image against known AI datasets.

### Sub-Pixel CFA Micro-Particle Morphing (`pixel_morphing_analyzer.py`)
Analyzes the Color Filter Array (CFA) interpolation (Bayer patterns). Authentic digital cameras have specific demosaicing noise patterns. AI-generated images do not pass through a physical camera sensor, so they exhibit severe sub-pixel morphing and lack a valid CFA pattern.

### FFT High-Frequency Residual Analyzer (`frequency_analyzer.py`)
Uses the 2D Fast Fourier Transform (FFT) to convert the image into the frequency domain. Diffusion models and GANs typically generate unnatural high-frequency "floors" or grid-like spectral peaks in the latent space. 

### Error Level Analysis / ELA (`ela_analyzer.py`)
Tests for compression inconsistencies. By re-saving the image at a known JPEG quality and subtracting the difference, it highlights regions that were composited or edited at different compression levels.

### Sensor Pattern Noise / PRNU (`noise_analyzer.py`)
Extracts the Photo Response Non-Uniformity (PRNU). Every physical camera sensor has unique silicon imperfections. AI images lack this consistent sensor noise, presenting unnaturally clean or mismatched noise entropies.

### Semantic Scene Context (`scene_analyzer.py`)
Detects the primary subject (Nature, Architecture, Anime, Faces). This allows the fusion engine to dynamically adjust weights. (For example, digital art will not have physical camera sensor noise, so PRNU weights are reduced to prevent false positives).

---

## 3. Core Physics Modules (The Real-World Laws)

AI models predict 2D pixels without a true 3D spatial engine, frequently violating global physical laws.

### Optics Physics: Corneal Specular Parallax (`physics_eye_reflection_analyzer.py`)
Analyzes the specular highlights (bright light reflections) inside human eyes. 
- **The Logic**: If a face is illuminated by a real-world light source, the reflections in both the left and right eyes must be geometrically consistent (parallel vectors).
- **The Algorithm**: Uses OpenCV Haar Cascades to extract eyes, applies adaptive thresholding to find the centroid of the light reflection, and calculates the dot product between the left and right displacement vectors. Asymmetrical vectors trigger a Physics Violation.

### Geometry Physics: Structural Symmetry & Support (`geometry_physics_analyzer.py`)
Analyzes the image for impossible 3D object intersections, floating limbs, or severe structural asymmetry.
- **The Logic**: AI generators sometimes merge dense structures into blank space or hallucinate floating objects without ground contact shadows.
- **The Algorithm**: Uses OpenCV Canny Edge detection to calculate edge density on the ground-plane (bottom 25%) to detect missing contact shadows. Uses ORB (Oriented FAST and Rotated BRIEF) feature matching to measure bilateral structural density and detect severe asymmetry.

---

## 4. Provenance & Metadata Forensics

### EXIF Analytics (`metadata_analyzer.py`)
Extracts cryptographic and software footprints. Many generative tools embed their signatures directly into the image file (e.g., `Software: Midjourney`). The engine provides a 100% deterministic override if known AI signatures are found, while raising mild suspicion if EXIF is completely stripped (since authentic camera photos always contain metadata).

## Usage
The service runs on port `8003` and consumes Kafka messages from `detection.requested.image_deepfake`. Results are published back to `detection.completed.image_deepfake`.
