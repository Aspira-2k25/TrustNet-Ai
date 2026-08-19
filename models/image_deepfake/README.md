# TrustNet AI — Image Deepfake Detection: Data Science & Mathematical Specification

## 1. Mathematical Thesis & Architectural Overview

Traditional deepfake detection systems rely solely on end-to-end convolutional neural networks (CNNs) or Vision Transformers (ViTs). While achieving high accuracy on standard test sets, these pure learned models suffer from **out-of-distribution failure, concept drift, and vulnerability to adversarial perturbation**.

TrustNet addresses this through **Physics-Informed Evidential Fusion**: coupling deep neural spatial representations with deterministic mathematical invariants derived from optical physics, digital signal processing, sensor electronics, and photogrammetry.

```
                              ┌────────────────────────────────────────┐
                              │           Input Image Matrix           │
                              │           I(x,y) ∈ ℝ^{H × W × 3}       │
                              └───────────────────┬────────────────────┘
                                                  │
                ┌─────────────────────────────────┴─────────────────────────────────┐
                ▼                                                                   ▼
┌───────────────────────────────┐                                   ┌───────────────────────────────┐
│     Semantic Scene Engine     │                                   │      Face Detection & Crop    │
│    SceneContextAnalyzer(I)    │                                   │       FaceAnalyzer(I)         │
└───────────────┬───────────────┘                                   └───────────────┬───────────────┘
                │ Domain D ∈ {Portrait, Art, Arch, Nature, Object}                  │ has_face ∈ {True, False}
                └─────────────────────────┬─────────────────────────────────────────┘
                                          │
    ┌─────────────────────────────────────┼─────────────────────────────────────┐
    │                                     │                                     │
    ▼                                     ▼                                     ▼
┌─────────────────────────┐   ┌─────────────────────────┐   ┌─────────────────────────┐
│   Learned Neural Layer  │   │  Micro-Forensics Layer  │   │  Physical Optics Layer  │
├─────────────────────────┤   ├─────────────────────────┤   ├─────────────────────────┤
│ • Vision Transformer    │   │ • 2D Fourier (FFT)      │   │ • Corneal Parallax      │
│   (ViT-Base-Patch16)    │   │ • Sub-Pixel Bayer CFA   │   │ • 3D Vanishing Geometry │
│ • EfficientNet-B0       │   │ • Gabor Filter Bank     │   │ • Error Level Analysis  │
│   (1280-dim Backbone)   │   │ • PRNU Sensor Noise     │   │ • Face X-Ray Seams      │
└───────────┬─────────────┘   └───────────┬─────────────┘   └───────────┬─────────────┘
            │                             │                             │
            │ s_learned                   │ s_micro                     │ s_optics
            └─────────────────────────────┼─────────────────────────────┘
                                          │
                                          ▼
                      ┌────────────────────────────────────────┐
                      │    Cross-Domain Evidential Fusion      │
                      │  A_weighted = ∑ (s_i · w_i) / ∑ w_i    │
                      │  + Multi-Vector Corroboration (N ≥ 2)  │
                      │  + Two-Way Contradiction Filter        │
                      └───────────────────┬────────────────────┘
                                          │
                                          ▼
                      ┌────────────────────────────────────────┐
                      │   Calibrated Risk Score & Verdict      │
                      │   Risk ∈ [0, 100], Verdict ∈ 4 Levels  │
                      └───────────────────┬────────────────────┘
```

---

## 2. Master Algorithm Inventory & Execution Map

| # | Algorithm / Method | Underlying Framework / Tool | Mathematical Role | How It Is Used in TrustNet | Source File |
|---|---|---|---|---|---|
| **1** | **Vision Transformer (ViT) Multi-Head Self-Attention** | PyTorch / Hugging Face `transformers` | Global patch-level feature correlation | Divides $224 \times 224$ images into 196 patches ($16 \times 16$), computes self-attention $\text{softmax}\left(\frac{\mathbf{Q}\mathbf{K}^T}{\sqrt{d_k}}\right)\mathbf{V}$ to classify deepfake vs authentic face structures. | `inference/huggingface_client.py` |
| **2** | **Grad-CAM Backpropagation Algorithm** | PyTorch Autograd | Gradient-weighted spatial activation maps | Computes partial derivatives $\frac{\partial y^c}{\partial A^k}$ with respect to layer-4 feature maps in EfficientNet-B0 to generate explainable spatial heatmaps. | `explainability/grad_cam.py` |
| **3** | **2D Fast Fourier Transform (2D FFT)** | `numpy.fft.fft2` | Frequency decomposition & power spectrum | Converts spatial pixels $I(x,y)$ to frequency domain $F(u,v)$, performs $360^\circ$ concentric radial integration, and fits linear regression to check $1/f^\alpha$ natural decay vs periodic GAN/diffusion lattice spikes. | `forensics/frequency_analyzer.py` |
| **4** | **Sub-Pixel Bayer CFA Interpolation Residual** | NumPy Matrix Vectorization | Sensor demosaicing continuity | Measures linear pixel dependency between the Green channel and Red/Blue neighbors: $\Delta = \|G - (R+B)/2\|$. High-order kurtosis $\kappa$ flags latent diffusion synthesis. | `forensics/pixel_morphing_analyzer.py` |
| **5** | **Multi-Scale Gabor Filter Bank** | `cv2.getGaborKernel` / `cv2.filter2D` | Spatial-frequency texture & orientation | Convolves image across 4 orientations ($\theta = 0^\circ, 45^\circ, 90^\circ, 135^\circ$) and 3 scales ($\lambda = 4, 8, 16$). Computes orientation Shannon entropy $H_\theta$ to detect unnatural texture smoothing. | `forensics/gabor_analyzer.py` |
| **6** | **JPEG Quantization Error Level Analysis (ELA)** | Pillow (`PIL.Image`) DCT Engine | Compression error disparity | Recompresses image at quality $Q=90$, subtracts recompressed pixels from original, and computes foreground-to-background error variance ratio $\frac{\text{Var}(E)}{\text{Mean}(E)}$ to detect spliced boundaries. | `forensics/ela_analyzer.py` |
| **7** | **Photo-Response Non-Uniformity (PRNU) Median Filter** | `cv2.medianBlur` / SciPy | Camera sensor fingerprint extraction | Applies a $3 \times 3$ spatial median filter to remove scene content, leaving the high-pass sensor noise residual $W = I - \text{Median}(I)$. Kurtosis and variance quantify non-physical sensor noise. | `forensics/noise_analyzer.py` |
| **8** | **Face X-Ray Multi-Pass Boundary Gradient** | OpenCV Haar Cascades + Sobel Operators | Facial blending seam detection | Detects faces with multi-angle rotation sweeps (+/-15°, +/-25°), extracts a $22\%$ expanded margin crop, and computes outer-perimeter vs inner-mask gradient ratio $\frac{|\bar{G}_{\text{inner}} - \bar{G}_{\text{outer}}|}{\bar{G}_{\text{outer}}}$. | `forensics/face_analyzer.py` |
| **9** | **Corneal Specular Reflection Parallax Vectors** | OpenCV Contours + `cv2.moments` | 3D environmental lighting physics | Detects left and right eye pairs, thresholds brightest corneal reflection centroids, normalizes 2D directional vectors $\vec{v}_L, \vec{v}_R$, and calculates cosine similarity $\cos \theta = \vec{v}_L \cdot \vec{v}_R$. $\cos \theta < 0.20$ flags impossible multi-directional lighting. | `forensics/physics_eye_reflection_analyzer.py` |
| **10** | **Probabilistic Hough Line Transform** | `cv2.HoughLinesP` | 3D vanishing line consistency | Identifies straight architectural perspective lines, intersects them to find 3D vanishing points, and measures line curvature variance $\sigma_{\text{lines}}$ to detect AI building melting. | `forensics/geometry_physics_analyzer.py` |
| **11** | **Semantic YCbCr Skin Tone Segmentation** | NumPy Array Masking | Domain categorization | Isolates human epidermis pixels via $(130 \le C_r \le 175) \land (75 \le C_b \le 128)$ to prevent false anime classification on crowd/group photographs. | `forensics/scene_analyzer.py` |
| **12** | **Evidential Multi-Vector Corroboration Fusion** | Custom NumPy Engine | Cross-domain sensor synthesis | Dynamically weights active sensors based on semantic scene domain, applies evidential max-pooling, and requires $\ge 2$ independent physical domains before escalating to high-risk verdicts. | `inference/efficientnet_detector.py` |

---

## 3. Learned Deep Neural Representations

### 3.1 Vision Transformer (ViT) Classifier
- **Model**: `dima806/deepfake_vs_real_image_detection` (hosted on Hugging Face).
- **Base Architecture**: Google Vision Transformer (`ViT-Base-Patch16-224-in21k`).
- **Input Transformation**: Image $I$ is divided into non-overlapping patches $x_p \in \mathbb{R}^{N \times (P^2 \cdot C)}$, where $P = 16$, $N = \frac{HW}{P^2} = 196$.
- **Linear Projection & Multi-Head Self-Attention**:
  $$\mathbf{z}_0 = [\mathbf{x}_{\text{class}}; \mathbf{x}_p^1 \mathbf{E}; \mathbf{x}_p^2 \mathbf{E}; \dots; \mathbf{x}_p^N \mathbf{E}] + \mathbf{E}_{\text{pos}}, \quad \mathbf{E} \in \mathbb{R}^{(P^2 C) \times D}$$
  $$\text{Attention}(\mathbf{Q}, \mathbf{K}, \mathbf{V}) = \text{softmax}\left(\frac{\mathbf{Q}\mathbf{K}^T}{\sqrt{d_k}}\right)\mathbf{V}$$
- **Training Baseline**: Trained on 140,000 real (FFHQ/CelebA-HQ) and synthetic (StyleGAN/DeepFaceLab) face crops ($256 \times 256$), delivering a baseline validation accuracy of **95.8%** ($F_1\text{-score: } 95.7\%$, loss: $0.119$).

### 3.2 Convolutional Feature Backbone & Grad-CAM Saliency
- **Model**: PyTorch `torchvision.models.efficientnet_b0(weights=DEFAULT)` pretrained on ImageNet-1K.
- **Role**: Computes high-dimensional spatial representation diversity and acts as the target for gradient-weighted class activation mapping (Grad-CAM).
- **Grad-CAM Formulation**:
  For target feature map $A^k$ at convolutional layer 4:
  $$\alpha_k^c = \frac{1}{Z} \sum_{i=1}^u \sum_{j=1}^v \frac{\partial y^c}{\partial A_{i,j}^k}$$
  $$L_{\text{Grad-CAM}}^c = \text{ReLU}\left(\sum_k \alpha_k^c A^k\right)$$

---

## 4. Mathematical Formulations of the 8 Forensic Engines

### 4.1 Frequency Domain: Radial Spectral Power-Law ($1/f^\alpha$) Residuals
Natural optical photographs obey a scale-invariant power-law spectrum:
$$S(f) = \frac{C}{f^\alpha} \quad \text{where } \alpha \approx 2.0 \pm 0.4$$
Generative diffusion upsamplers (e.g. latent diffusion transposed convolutions) introduce high-frequency periodic lattice spikes and break the radial decay slope $\alpha$.

1. Compute the 2D Discrete Fourier Transform (DFT):
   $$F(u, v) = \sum_{x=0}^{M-1} \sum_{y=0}^{N-1} I(x, y) \cdot e^{-j 2\pi \left(\frac{ux}{M} + \frac{vy}{N}\right)}$$
2. Shift zero-frequency components to the center and compute the power spectrum:
   $$P(u, v) = |F(u, v)|^2$$
3. Perform azimuthal radial integration for concentric frequency bands $r = \sqrt{u^2 + v^2}$:
   $$\bar{P}(r) = \frac{1}{N_r} \sum_{\theta=0}^{2\pi} P(r \cos \theta, r \sin \theta)$$
4. Fit linear regression in log-log space: $\ln \bar{P}(r) = -\alpha \ln r + \beta$.
5. Anomaly score:
   $$s_{\text{freq}} = \text{clamp}\left(\frac{|\hat{\alpha} - 2.0|}{1.5} + \frac{N_{\text{spikes}}}{200}, 0.0, 1.0\right)$$

---

### 4.2 Micro-Structural Domain: Sub-Pixel Bayer CFA Continuity
Physical camera sensors capture light through a Color Filter Array (Bayer CFA pattern). Demosaicing creates structured cross-channel correlation between the green channel $G$ and red/blue channels $R, B$:
$$\hat{G}(x, y) = \frac{1}{4} \big[R(x+1, y) + R(x-1, y) + B(x, y+1) + B(x, y-1)\big] + \epsilon(x, y)$$
Latent diffusion and GAN models synthesize all RGB channels simultaneously without a physical Bayer grid.

1. Estimate the demosaicing error residual:
   $$\Delta_{\text{CFA}}(x, y) = \left| G(x, y) - \frac{R(x, y) + B(x, y)}{2} \right|$$
2. Compute spatial micro-jitter kurtosis $\kappa$:
   $$\kappa = \frac{\frac{1}{N} \sum_{i=1}^N (x_i - \mu)^4}{\left(\frac{1}{N} \sum_{i=1}^N (x_i - \mu)^2\right)^2}$$
3. Synthetic images lack micro-jitter kurtosis and display broken Bayer periodicity ($\kappa < 4.0$ or $\Delta_{\text{CFA}} > 22.0$).

---

### 4.3 Spatial Texture Domain: Multi-Scale Gabor Filter Bank
AI generators often produce anisotropic texture smoothing or unnatural directional frequency concentration. A 2D Gabor filter is defined as:
$$g(x, y; \lambda, \theta, \psi, \sigma, \gamma) = \exp\left(-\frac{x'^2 + \gamma^2 y'^2}{2\sigma^2}\right) \cos\left(2\pi \frac{x'}{\lambda} + \psi\right)$$
where $x' = x \cos \theta + y \sin \theta$ and $y' = -x \sin \theta + y \cos \theta$.

1. Apply filter bank across 4 orientations $\theta \in \{0, \frac{\pi}{4}, \frac{\pi}{2}, \frac{3\pi}{4}\}$ and 3 wavelengths $\lambda \in \{4, 8, 16\}$.
2. Calculate the orientation entropy $H_\theta$:
   $$H_\theta = -\sum_{k=1}^4 p_k \log_2(p_k), \quad p_k = \frac{E(\theta_k)}{\sum_j E(\theta_j)}$$
3. Anomaly score $s_{\text{gabor}} = 1.0 - \text{min}(1.0, H_\theta / \log_2(4))$.

---

### 4.4 Compression Domain: Error Level Analysis (ELA)
When an authentic image is saved as a JPEG, the entire canvas undergoes uniform Discrete Cosine Transform (DCT) quantization:
$$F_{Q}(u, v) = \text{round}\left(\frac{\text{DCT}(f(x, y))}{Q(u, v)}\right)$$
In composite deepfakes or inpainted images, modified areas have different compression histories than the surrounding background.

1. Re-encode the image at quality $Q = 90$ to obtain $I_{\text{recompressed}}$.
2. Compute the absolute difference matrix:
   $$E(x, y) = |I(x, y) - I_{\text{recompressed}}(x, y)|$$
3. Calculate foreground-to-background error variance ratio:
   $$s_{\text{ela}} = \text{clamp}\left(\frac{\text{Var}(E)}{\text{Mean}(E) \cdot 255}, 0.0, 1.0\right)$$

---

### 4.5 Sensor Noise Domain: Photo-Response Non-Uniformity (PRNU)
Every physical camera sensor embeds a unique high-frequency noise fingerprint (PRNU) caused by silicon manufacturing tolerances:
$$I = I^{(0)} + I^{(0)} \cdot K + \Theta$$
where $K$ is the PRNU multiplicative factor and $\Theta$ is additive random noise.

1. Extract noise residual using a 4-neighbor spatial median filter:
   $$W(x, y) = I(x, y) - \text{MedianFilter}(I(x, y), 3 \times 3)$$
2. Compute the standard deviation $\sigma_W$ and kurtosis $\kappa_W$ of the residual.
3. Completely synthetic images exhibit either near-zero noise ($\sigma_W < 2.0$) or Gaussian-synthesized noise with $\kappa_W < 3.2$.

---

### 4.6 Face Forensics: Landmark & Boundary Discontinuity (Face X-Ray)
In face-swap deepfakes (DeepFaceLab, SimSwap, InsightFace), the synthesized face is blended into the target frame. This leaves a boundary seam with step gradients:
$$\nabla I(x, y) = \left( \frac{\partial I}{\partial x}, \frac{\partial I}{\partial y} \right), \quad \|\nabla I\| = \sqrt{G_x^2 + G_y^2}$$

1. Detect face bounding boxes using contrast-equalized Haar cascades and skin topography.
2. Extract an expanded facial crop with a $22\%$ margin covering the jawline, hairline, and neck.
3. Compute the perimeter-to-inner boundary gradient disparity:
   $$\text{Disparity} = \frac{|\bar{G}_{\text{inner}} - \bar{G}_{\text{outer}}|}{\bar{G}_{\text{outer}} + 10^{-6}}$$
4. Anomaly score $s_{\text{face}} \ge 0.60$ if $\text{Disparity} > 0.85$ or boundary standard deviation $> 52.0$.

---

### 4.7 Physical Optics: Corneal Specular Reflection Parallax
For genuine human subjects illuminated by an environmental light source, reflections on the curved corneas of both eyes must point in parallel 3D direction vectors:

1. Detect left and right eyes: $E_L, E_R$.
2. Extract the specular reflection centroid $(c_x, c_y)$ relative to the corneal center $(e_x, e_y)$:
   $$\vec{v} = \left(\frac{c_x - e_x}{\sqrt{(c_x - e_x)^2 + (c_y - e_y)^2}}, \frac{c_y - e_y}{\sqrt{(c_x - e_x)^2 + (c_y - e_y)^2}}\right)$$
3. Compute the cosine similarity between the left and right reflection vectors:
   $$\cos \theta = \vec{v}_L \cdot \vec{v}_R$$
4. Scoring:
   - $\cos \theta \ge 0.60 \implies s_{\text{optics}} = 0.05$ (Physically consistent light source)
   - $\cos \theta < 0.20 \implies s_{\text{optics}} = 0.65$ (Impossible multi-directional lighting)

---

### 4.8 3D Photogrammetry: Geometric Vanishing Line & Support Physics
1. Compute the Hough line transform on architectural edges:
   $$\rho = x \cos \theta + y \sin \theta$$
2. Identify vanishing points $\mathbf{v}_p = l_1 \times l_2$.
3. Compute perspective consistency variance: in AI-generated buildings, parallel lines wobble and exhibit high structural variance ($\sigma_{\text{lines}} > 88.0$).

---

## 5. Semantic Domain Routing & Adaptive Weight Matrix

Forensic signals have different validity depending on the image content. For example, CFA demosaicing and corneal optics are not applicable to digital paintings or screenshots.

`SceneContextAnalyzer` categorizes media into 5 domains using skin tone YCbCr masks, edge gradients, and chromatic saturation:

$$\text{Skin Mask}: (130 \le C_r \le 175) \land (75 \le C_b \le 128) \land (R > G) \land \left(\frac{R}{G+1} \le 2.2\right)$$

### Adaptive Sensor Weight Matrix $\mathbf{W}$:

| Forensic Sensor | Portrait / Human ($w_i$) | Digital Art / Anime ($w_i$) | Architecture ($w_i$) | Landscape ($w_i$) | Object ($w_i$) |
|---|---|---|---|---|---|
| **Hugging Face ViT** ($s_{\text{ViT}}$) | **0.30** | **0.00** *(gated if 0 faces)* | **0.00** | **0.00** | **0.00** |
| **Face X-Ray Boundary** ($s_{\text{face}}$) | **0.25** | **0.00** *(gated if 0 faces)* | **0.00** | **0.00** | **0.00** |
| **Corneal Reflection** ($s_{\text{optics}}$) | **0.20** | **0.00** | **0.00** | **0.00** | **0.00** |
| **2D Fourier DFT** ($s_{\text{freq}}$) | **0.20** | **0.12** | **0.20** | **0.25** | **0.20** |
| **Sub-Pixel Bayer CFA** ($s_{\text{cfa}}$) | **0.16** | **0.12** | **0.18** | **0.18** | **0.18** |
| **Gabor Texture Bank** ($s_{\text{gabor}}$) | **0.16** | **0.08** | **0.16** | **0.16** | **0.16** |
| **Error Level Analysis** ($s_{\text{ela}}$) | **0.12** | **0.05** | **0.15** | **0.12** | **0.14** |
| **PRNU Sensor Noise** ($s_{\text{noise}}$) | **0.10** | **0.04** | **0.12** | **0.12** | **0.12** |
| **3D Geometry Support** ($s_{\text{geom}}$) | **0.00** *(skipped for faces)* | **0.00** | **0.18** | **0.00** | **0.15** |
| **Semantic Context** ($s_{\text{scene}}$) | **0.12** | **0.35** | **0.12** | **0.12** | **0.12** |

---

## 6. Evidential Fusion & Decision Mathematics

### 6.1 Normalized Weighted Fusion
The raw baseline anomaly score $A_{\text{weighted}}$ is:
$$A_{\text{weighted}} = \frac{\sum_{i \in \text{Active}} s_i \cdot w_i}{\sum_{i \in \text{Active}} w_i}$$

### 6.2 Multi-Vector Physical Corroboration Rule
Let $\mathcal{D} = \{\text{Frequency}, \text{Microstructure}, \text{Compression}, \text{Texture}, \text{Anatomy}, \text{Optics}, \text{Learned}\}$ be distinct physical domains. A domain is **active positive** if:
$$\exists s_i \in \mathcal{D}_k \quad \text{such that } s_i \ge 0.60$$

- **Strong Multi-Domain Corroboration ($|\mathcal{D}_{\text{active}}| \ge 2$)**:
  $$A_{\text{calibrated}} = \max\left(0.75, \min(0.98, A_{\text{weighted}} \times 1.15)\right)$$
- **Isolated Single-Domain Spike ($|\mathcal{D}_{\text{active}}| = 1$)**:
  Without multi-vector confirmation, a single sensor cannot force a fake verdict. It is capped within the `UNCERTAIN` boundary:
  $$A_{\text{calibrated}} = \max\left(A_{\text{weighted}}, \min(0.52, \max_i(s_i) \times 0.68)\right)$$
- **Zero Strong Domains ($|\mathcal{D}_{\text{active}}| = 0$)**:
  $$A_{\text{calibrated}} = \min\left(0.20, A_{\text{weighted}}\right)$$

### 6.3 Two-Way Cross-Modal Contradiction Handling
When the learned Vision Transformer and physical forensic sensors disagree:
$$\text{Contradiction} = \begin{cases} 
\text{True} & \text{if } s_{\text{ViT}} \le 0.15 \land |\mathcal{D}_{\text{active}}| \ge 2 \\
\text{True} & \text{if } s_{\text{ViT}} \ge 0.75 \land |\mathcal{D}_{\text{active}}| = 0 \land \max(s_i) \le 0.25 \\
\text{False} & \text{otherwise}
\end{cases}$$
If $\text{Contradiction} = \text{True} \implies A_{\text{calibrated}} \in [0.46, 0.58] \implies \mathbf{Verdict} \leftarrow \mathbf{UNCERTAIN}$.

---

## 7. Output Calibration & Metric Definitions

### 7.1 Native Score & Risk Score
- **Native Score (Probability of Authentic)**:
  $$P(\text{REAL}) = \text{clamp}(1.0 - A_{\text{calibrated}}, 0.01, 0.99)$$
- **Calibrated Risk Score**:
  $$\text{Risk Score} = (1.0 - P(\text{REAL})) \times 100.0$$

### 7.2 4-Level Semantic Verdict Scale

$$\mathbf{Verdict} = \begin{cases}
\mathbf{AUTHENTIC} & \text{if } \text{Risk} < 25.0 \land \neg \text{Contradiction} \\
\mathbf{LIKELY\_AUTHENTIC} & \text{if } 25.0 \le \text{Risk} < 45.0 \land \neg \text{Contradiction} \\
\mathbf{UNCERTAIN} & \text{if } 45.0 \le \text{Risk} < 65.0 \lor \text{Contradiction} \\
\mathbf{LIKELY\_AI\_MANIPULATED} & \text{if } \text{Risk} \ge 65.0 \land \neg \text{Contradiction}
\end{cases}$$

### 7.3 Cross-Domain Sensor Consistency Metric
Measures the standard deviation $\sigma$ across the active forensic domain scores:
$$\sigma_{\text{domains}} = \text{std}\left(\left[ \bar{s}_{\text{spatial}}, s_{\text{freq}}, s_{\text{ela}}, s_{\text{ViT}} \right]\right)$$
$$\text{Consistency} = \max\left(0.60, \min\left(0.98, 1.0 - \sigma_{\text{domains}} \times 0.45\right)\right) \times 100\%$$

---

## 8. Formal Benchmark & Verification Equations

The formal scientific benchmark suite (`benchmark/benchmark_suite.py`) calculates the following evaluation metrics on labelled validation sets:

1. **Receiver Operating Characteristic Area (ROC-AUC)**:
   $$\text{ROC-AUC} = \int_{0}^{1} \text{TPR}(\text{FPR}^{-1}(t)) \, dt$$
2. **Expected Calibration Error (ECE)** (across $M=10$ probability bins):
   $$\text{ECE} = \sum_{m=1}^M \frac{|B_m|}{N} \left| \text{acc}(B_m) - \text{conf}(B_m) \right|$$
3. **Brier Score**:
   $$\text{Brier} = \frac{1}{N} \sum_{i=1}^N (p_i - y_i)^2$$
4. **Equal Error Rate (EER)**:
   $$\text{EER} = \text{FPR}(t^*) \quad \text{where } \text{FPR}(t^*) = 1 - \text{TPR}(t^*)$$
