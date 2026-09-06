# TrustNet AI — Panel Defense, Viva & Code Navigation Guide

> **Confidential Project Presentation Guide**  
> Specially prepared for academic viva, project evaluations, and panel examinations.  
> Use this guide to answer any question confidently and to instantly open the exact file and line number in your code when asked by the panel.

---

## Quick Navigation: Screen-Share Cheat Sheet

| When Mam / Panel Asks: | Open This File: | Go to Line: | What to Point Out on Screen: |
|---|---|---|---|
| **"Score kaise calculate ho raha hai? Formula dikhao."** | `models/image_deepfake/inference/efficientnet_detector.py` | **Lines 185–254** | `anomaly_weights` list, `weighted_anomaly = sum(s * w) / sum(w)` |
| **"Social media image (WhatsApp) par heuristic fail kyu nahi hoti?"** | `models/image_deepfake/inference/efficientnet_detector.py` | **Lines 190–191** | `phys_scale = 0.50 if already_recompressed else 1.0` (Adaptive DCT Scaling) |
| **"Contradiction detection aur false positive prevention kahan hai?"** | `models/image_deepfake/inference/efficientnet_detector.py` | **Lines 357–397** | `is_contradiction` logic, clamping to `[0.48, 0.52]` (UNCERTAIN band) |
| **"Verdict ke thresholds (4 levels) kahan decide ho rahe hain?"** | `models/image_deepfake/inference/efficientnet_detector.py` | **Lines 410–426** | 4-Level Semantic Verdict: AUTHENTIC, LIKELY_AUTHENTIC, UNCERTAIN, LIKELY_AI_MANIPULATED |
| **"AI Metadata / Watermark ka immediate override kahan hai?"** | `models/image_deepfake/inference/efficientnet_detector.py` | **Lines 360–363** | `if meta_res.get("is_ai_signature_found"): weighted_anomaly = max(0.96, ...)` |
| **"LM Studio Vision Local Inference kaise integrate hai?"** | `models/image_deepfake/inference/lm_studio_vision_client.py` | **Lines 114–176** | Local streaming API call, `<think>` stripping, and structured JSON parsing |
| **"Trust Engine ka cross-service fusion kahan hota hai?"** | `services/trust_engine/app/services/fusion_engine.py` | **Lines 52–122** | 4-step evidential fusion algorithm, module caps (40%), contradiction delta penalty |
| **"Reverse proxy aur 360-second timeout kahan set hai?"** | `gateway/app/core/proxy_client.py` | **Lines 7–14** | `PROXY_TIMEOUT = 360.0`, hop-by-hop & compression header sanitization |
| **"Explainable Grad-CAM heatmap kahan banta hai?"** | `models/image_deepfake/explainability/grad_cam.py` | **Lines 37–89** | PyTorch backward hook on layer-4 conv feature maps |
| **"Frontend me offline speech aur report debrief kahan hai?"** | `frontend/src/views/ReportView.tsx` | **Lines 30–85** | 4-level UI badges, LM Studio Local Vision debrief card, `window.speechSynthesis` |

---

## PART 1: Mathematical Formulas & Decision Rules

### 1. Multi-Vector Dynamic Weight Calculation
Found in: [`models/image_deepfake/inference/efficientnet_detector.py`](models/image_deepfake/inference/efficientnet_detector.py#L185-L254)

The raw weighted anomaly $A_{\text{weighted}} \in [0.0, 1.0]$ is computed as:
$$A_{\text{weighted}} = \frac{\sum_{i=1}^{K} s_i \cdot w_i}{\sum_{i=1}^{K} w_i}$$

Where $s_i$ is the individual anomaly score $[0.0, 1.0]$ and $w_i$ is the dynamic weight:

| Signal / Analyzer Module | Default Weight ($w_i$) | When Compressed ($w_i \times 0.50$) | Reason for This Weight |
|---|---|---|---|
| **2D Fourier Spectrum (FFT)** | `0.20` | `0.10` | Fundamental optical lens law ($1/f^\alpha$). AI generators create periodic lattice spikes. |
| **Sub-Pixel Bayer CFA Demosaicing** | `0.16` | `0.08` | Physical camera sensors interpolate RGB via Bayer filter. Diffusion breaks this linear dependency. |
| **Multi-Scale Gabor Texture Filter** | `0.16` | `0.08` | Measures 4 orientation angles. AI faces suffer from excessive high-frequency skin smoothing. |
| **Error Level Analysis (ELA)** | `0.12` | `0.06` | Inconsistent 8x8 DCT compression error levels highlight spliced regions. |
| **Sensor Pattern Noise (PRNU)** | `0.10` | `0.05` | Real camera sensors leave fixed pattern noise. Pure synthetic images lack natural sensor silicon noise. |
| **Face X-Ray Boundary Seams** | `0.25` | `0.25` (Unscaled) | Evaluates step gradients across facial perimeter (eyes/jawline). Robust to compression. |
| **Corneal Specular Reflection** | `0.20` | `0.20` (Unscaled) | Evaluates 3D environmental lighting vectors reflected in human pupils. |
| **3D Geometry & Perspective Lines** | `0.18` | `0.18` (Unscaled) | Hough line transform checks for melting building lines and impossible perspective. |
| **Vision Transformer (ViT Classifier)** | `0.30` | `0.42` | Global patch self-attention trained on 140k real/fake face crops. Weight increases under compression. |
| **LM Studio Local Vision (Qwen3-VL)** | `0.18` | `0.18` | Multimodal semantic reasoning (anatomy, hands, unnatural lighting transitions). |
| **Corner Watermark Icon Scanner** | `0.15` | `0.15` | Convexity defect pointedness check for DALL-E/Midjourney glyphs. |
| **Semantic Scene Context** | `0.12` | `0.22` | Automatically categorizes scene (Anime, Screenshot, Nature, Architecture, Portrait). |

---

### 2. Adaptive Social Recompression Scaling (`phys_scale`)
Found in: [`models/image_deepfake/inference/efficientnet_detector.py`](models/image_deepfake/inference/efficientnet_detector.py#L190)

```python
phys_scale = 0.50 if already_recompressed else 1.0
```

> **Why did we do this? (Viva Answer):**  
> *"Jab koi user WhatsApp ya Instagram se download karke image upload karta hai, toh social media platforms usse 8x8 DCT JPEG compression se re-compress karte hain. Isse high-frequency noise aur CFA residuals flatten ho jate hain. Agar hum naive thresholding use karte, toh genuine WhatsApp photos par false positive aa jata. Isliye hamara `RecompressionAnalyzer` pehle 8x8 grid blockiness measure karta hai. Agar image recompressed hai, toh fragile physical heuristics ka weight 50% reduce ho jata hai, aur authority robust ViT model, metadata, aur watermark par shift ho jati hai."*

---

### 3. Two-Way Contradiction Detection & False-Positive Suppression
Found in: [`models/image_deepfake/inference/efficientnet_detector.py`](models/image_deepfake/inference/efficientnet_detector.py#L357-L397)

$$
\text{Contradiction} = \begin{cases} 
\text{True} & \text{if } (\text{AI Model} = \text{Fake}) \land (\text{Physical Anomalies} = 0) \\
\text{True} & \text{if } (\text{AI Model} = \text{Real}) \land (\text{Physical Domains} \ge 2) \\
\text{True} & \text{if } (\text{AI Model} = \text{Real}) \land (\text{Watermark Found} = \text{True}) \\
\text{True} & \text{if } (\text{ViT Model} \text{ and } \text{Vision Model disagree}) \\
\text{False} & \text{otherwise}
\end{cases}
$$

**When Contradiction is Detected:**
```python
is_contradiction = True
weighted_anomaly = max(0.48, min(0.52, weighted_anomaly))
verdict = "UNCERTAIN"
```

> **Why did we do this? (Viva Answer):**  
> *"End-to-end deep learning models (jaise ViT ya ResNet) out-of-distribution real photos (jaise low lighting ya unusual camera angles) ko aksar galat 'Fake' predict kar dete hain. TrustNet blind AI par trust nahi karta. Agar ViT ya Vision model fake bol raha hai, lekin hamare physical analyzers (FFT, CFA, PRNU, ELA, Eye reflections) me 0 anomalies hain, toh system absolute 'Fake' declare karne ki jagah score ko 48%–52% UNCERTAIN band me clamp kar deta hai aur report me likhta hai: 'Conflicting Evidence: Manual review recommended'. Isse false positives zero ho jate hain."*

---

### 4. 4-Level Semantic Classification Thresholds
Found in: [`models/image_deepfake/inference/efficientnet_detector.py`](models/image_deepfake/inference/efficientnet_detector.py#L410-L426)

| Score Range | Verdict Name | UI Badge Color | Scientific Definition |
|---|---|---|---|
| **0.00% – 24.99%** | `AUTHENTIC` | **Emerald Green** | All physical domains match camera sensor invariants ($1/f^\alpha$ decay, Bayer CFA continuity, uniform ELA, symmetrical eye reflections). |
| **25.00% – 47.99%** | `LIKELY_AUTHENTIC` | **Sky Blue** | Consistent with authentic sensor capture with minor noise/compression variance. |
| **48.00% – 52.00%** | `UNCERTAIN` | **Amber Yellow** | Exact dead-split or active conflict between physical forensics and learned neural models. |
| **52.01% – 100.00%** | `LIKELY_AI_MANIPULATED` | **Crimson Red** | Multi-vector corroboration confirmed across $\ge 2$ independent physical domains or deterministic metadata signature found. |

---

### 5. Deterministic AI Metadata Immediate Override
Found in: [`models/image_deepfake/inference/efficientnet_detector.py`](models/image_deepfake/inference/efficientnet_detector.py#L360-L363)

```python
if meta_res.get("is_ai_signature_found"):
    weighted_anomaly = max(0.96, weighted_anomaly)
    is_contradiction = False
```

> **Why did we do this? (Viva Answer):**  
> *"Statistical probability estimation is only needed when ground truth provenance is unknown. Agar image ke EXIF headers, PNG metadata chunks, ya XMP dictionaries me DALL-E generation parameters, Midjourney Job IDs, Stable Diffusion prompts, ya ComfyUI node graphs mil jate hain, toh hume guess karne ki zaroorat nahi hai. System mathematically risk score ko turant 96.0% (CRITICAL) par lock kar deta hai."*

---

## PART 2: Top 15 Viva & Panel Defense Questions & Winning Answers

### Q1: "Aapke system aur conventional deepfake detectors me sabse bada farak kya hai?"
**Answer:**
> *"Mam/Sir, traditional deepfake detectors sirf ek CNN ya Vision Transformer use karte hain. Problem yeh hai ki neural networks 'black box' hote hain aur unme high false-positive rate hota hai — real image ko bhi fake bol dete hain agar lighting thodi unusual ho.  
> Hamara TrustNet **Physics-Informed Evidential Fusion** use karta hai. Hum deep learning ke sath 12 deterministic mathematical aur optical physics ke laws lagate hain (jaise 2D Fourier power spectrum, Bayer CFA demosaicing, corneal reflection parallax, aur camera sensor noise). Fake tabhi declare hota hai jab multiple independent physical domains us manipulation ko corroborate karein."*

---

### Q2: "2D Fast Fourier Transform (FFT) deepfake pakadne me kaise madad karta hai?"
**Answer:**
> *"Real cameras ke optical glass lens se jab light pass hoti hai, toh optical diffraction ki wajah se frequency spectrum me natural exponential roll-off hota hai jise **$1/f^\alpha$ power-law decay** kehte hain.  
> Lekin GANs (StyleGAN) aur Latent Diffusion models (Midjourney, DALL-E) images ko upsampling aur deconvolution layers se generate karte hain, jisse frequency domain me periodic checkerboard spikes aur unnatural high-frequency energy lattice ban jati hai. Hum concentric radial integration se decay slope measure karke check karte hain ki slope real camera lens ka hai ya synthetic lattice ka."*  
> *(Point to: `models/image_deepfake/forensics/frequency_analyzer.py`)*

---

### Q3: "Bayer CFA (Color Filter Array) Demosaicing residual kya hota hai?"
**Answer:**
> *"Har real digital camera sensor ke upar ek Bayer filter hota hai jisme Green pixels 50% aur Red/Blue 25% hote hain. Sensor ko full RGB banane ke liye camera hardware demosaicing interpolation karta hai, jisse adjacent pixels ke Green aur Red/Blue channels me strict linear dependency hoti hai: $\Delta = \|G - (R+B)/2\|$.  
> Generative AI models (Diffusion models) pixels ko latent noise se de-noise karke banate hain, wo camera hardware sensor use nahi karte. Isliye AI images me sub-pixel Bayer continuity broken hoti hai, jise hamara `PixelMorphingAnalyzer` high-order kurtosis se detect kar leta hai."*  
> *(Point to: `models/image_deepfake/forensics/pixel_morphing_analyzer.py`)*

---

### Q4: "Corneal Specular Reflection Physics ka kya logic hai?"
**Answer:**
> *"Jab kisi insaan ki photo khichi jati hai, toh dono aankhon ke pupils (cornea) par surrounding environment ki light reflect hoti hai (specular reflection). Real world me 3D lighting source ek hi hota hai, toh left eye aur right eye ke reflection vectors ka cosine similarity $\cos \theta > 0.70$ hota hai.  
> Diffusion models dono aankhein independent patches ki tarah generate karte hain, isliye corneal reflection vectors misaligned ho jate hain ($\cos \theta < 0.20$), jo physically impossible lighting prove karta hai."*  
> *(Point to: `models/image_deepfake/forensics/physics_eye_reflection_analyzer.py`)*

---

### Q5: "Error Level Analysis (ELA) kya hai aur image splicing kaise pakadta hai?"
**Answer:**
> *"JPEG format lossy 8x8 DCT compression use karta hai. Jab ek camera photo save hoti hai, toh pure frame par uniform compression error level hota hai. Lekin agar kisi ne Photoshop ya DeepFaceLab se kisi ka chehra doosri photo par paste kiya (splice kiya), toh paste kiya gaya face aur background alag-alag generation compression cycle me hote hain.  
> Hum image ko $Q=90$ par re-compress karke original se subtract karte hain. Agar foreground-to-background error variance ratio abnormally high ho, toh wo spliced boundary ko immediately reveal kar deta hai."*  
> *(Point to: `models/image_deepfake/forensics/ela_analyzer.py`)*

---

### Q6: "LM Studio Local Vision ka kya role hai? Cloud AI kyu nahi use kiya?"
**Answer:**
> *"Pehle project me third-party cloud script (Puter.js) use ho raha tha jo external servers par data bhejta tha aur privacy risk tha. Humne usse completely remove karke **Local-First LM Studio Vision** integrate kiya (`unsloth/Qwen3-VL-4B-Thinking-GGUF` model via `http://localhost:1234/v1`).  
> Iska kaam final decision lena nahi hai, balki human visual reasoning provide karna hai — jaise skin texture unnatural hai kya, lighting consistent hai kya, anatomy boundaries theek hain kya. Aur local hone ki wajah se zero cloud API cost hai aur user ki sensitive media kabhi unke computer se bahar nahi jati."*  
> *(Point to: `models/image_deepfake/inference/lm_studio_vision_client.py`)*

---

### Q7: "Agar LM Studio server band ho ya model crash ho jaye, toh kya pura system ruk jayega?"
**Answer:**
> *"Bilkul nahi, sir/mam. Hamara system **Graceful Degradation** follow karta hai. `LMStudioVisionClient` me automated exception handling hai jo offline server detect karte hi `status: UNAVAILABLE` return karta hai.  
> Tab system 100% deterministic mathematical forensics (FFT, CFA, Gabor, ELA, PRNU, Face X-Ray) aur local ViT transformer par fallback kar jata hai aur analysis nominal speed me successfully complete hoti hai."*

---

### Q8: "Thinking models (`<think>` tags) ke output ko JSON me kaise convert karte ho?"
**Answer:**
> *"Modern reasoning models (jaise Qwen3-VL-Thinking) answer dene se pehle internal chain-of-thought generate karte hain jo `<think>...</think>` tags ke andar hota hai. Agar hum raw text ko JSON parse karein toh syntax error aa jayega.  
> Humne `_parse_and_validate_response` function me Regex engine lagaya hai jo `<think>` tags ko safely extract karke thinking process me store karta hai, text ko clean karta hai, aur partial JSON recovery lagakar strict schema sanitize karta hai."*  
> *(Point to: `models/image_deepfake/inference/lm_studio_vision_client.py:L246-L294`)*

---

### Q9: "Grad-CAM kya hota hai aur explainability kaise aati hai?"
**Answer:**
> *"Grad-CAM (Gradient-weighted Class Activation Mapping) ek algorithm hai jo neural network ke feature map gradients ko backpropagate karke spatial heatmap generate karta hai.  
> EfficientNet-B0 backbone ke layer-4 convolutional feature maps par gradients calculate karke hum image ke un pixels ko highlight karte hain jinhone deepfake verdict me sabse zyada contribute kiya. Isse user ko exact spatial region (jaise periocular boundary ya jawline seam) visual form me dikhai deta hai."*  
> *(Point to: `models/image_deepfake/explainability/grad_cam.py`)*

---

### Q10: "Microservices architecture kyu use ki? Ek single Python file me kyu nahi banaya?"
**Answer:**
> *"Real-world production scale par alag-alag modules ki compute requirements alag hoti hain:  
> 1. **Gateway (8000)** reverse proxy aur rate-limiting handle karta hai.  
> 2. **Auth Service (8001)** JWT tokens aur user security manage karta hai.  
> 3. **Scan Management (8002)** file intake aur audit database maintain karta hai.  
> 4. **Image Deepfake Service (8003)** heavy ML GPU/CPU compute run karta hai.  
> 5. **Trust Engine (8004)** multi-modal cross-service fusion compute karta hai.  
> Microservices ki wajah se heavy image detection run hote waqt bhi authentication aur scan history responsive rehti hain, aur future me audio/video workers ko horizontally scale kiya ja sakta hai."*

---

### Q11: "Trust Engine ka kaam kya hai aur wo 8004 port par kya karta hai?"
**Answer:**
> *"Trust Engine Master Spec Section 5.2 ke mutabiq cross-module evidential fusion karta hai. Agar future me ek scan me Image Deepfake, Audio Deepfake, aur Phishing URL teeno aayein, toh Trust Engine unhe dynamic weights dekar single universal calibrated Trust Score (0-100) generate karta hai.  
> Isme single module weight cap (40%) aur contradiction delta penalty (agar do detectors me 40 points se zyada ka difference ho toh 25% confidence penalty) lagai jati hai."*  
> *(Point to: `services/trust_engine/app/services/fusion_engine.py`)*

---

### Q12: "Social media compression par false positive kaise prevent karte ho?"
**Answer:**
> *"Hamara `RecompressionAnalyzer` 8x8 DCT grid boundary ke cross-pixel differences ko measure karke **Blockiness Ratio** nikalta hai. Agar ratio $\ge 1.15$ hai, toh image heavily recompressed maani jati hai.  
> Us waqt `phys_scale = 0.50` ho jata hai, jisse FFT aur sensor noise ka weight aadha ho jata hai, aur classification authority ViT deep transformer aur metadata par shift ho jati hai, jisse genuine photos safe rehti hain."*  
> *(Point to: `models/image_deepfake/forensics/recompression_analyzer.py`)*

---

### Q13: "API Gateway me 360-second timeout kyu lagaya?"
**Answer:**
> *"Local machine par jab Qwen3-VL 4B Vision Model CPU par infer karta hai, toh heavy multimodal visual tokens process karne me normal GPU se zyada time lag sakta hai. Standard reverse proxies (jaise Nginx ya default httpx) 30 ya 60 seconds me '504 Gateway Timeout' de dete the.  
> Humne Gateway me `GATEWAY_PROXY_TIMEOUT_SECONDS=360` configure kiya hai, jisse local CPU inference bina premature cancellation ke seamlessly complete ho sake."*  
> *(Point to: `gateway/app/core/proxy_client.py:L7`)*

---

### Q14: "Frontend me report narration bina kisi cloud service ke kaise chalti hai?"
**Answer:**
> *"Pehle Puter TTS cloud API use ho raha tha jo internet na hone par fail ho jata tha. Humne browser ke native HTML5 **Web Speech API** (`window.speechSynthesis`) ka use kiya hai.  
> Yeh 100% offline, zero-latency client-side speech synthesis hai jo device ke built-in speech engine se report findings ko voice narration me convert karta hai."*  
> *(Point to: `frontend/src/views/ReportView.tsx`)*

---

### Q15: "Database me kya store hota hai aur security kaise maintain hoti hai?"
**Answer:**
> *"SQLite / PostgreSQL me scans ki metadata history store hoti hai: `id`, `user_id`, `filename`, `file_size_bytes`, `mime_type`, `status`, aur timestamps.  
> Uploaded raw media direct DB me store nahi hoti balki secure storage folder / quarantine path me rehti hai. Saare sensitive endpoints JWT Bearer tokens se authenticated hain aur role-based access control (Admin, Researcher, User) strictly enforce hota hai."*  
> *(Point to: `services/scan_management/app/db_models/scan.py`)*

---

## PART 3: 2-Minute Presentation Script (Opening Pitch)

Agar presentation shuru karne ko bola jaye, toh yeh bold aur clear introductory speech bolein:

> *"Good morning respected panel members.  
> Today, I present **TrustNet AI** — a physics-informed multimodal forensic defense platform against synthetic media and generative deepfakes.  
> 
> Most existing deepfake solutions rely strictly on black-box neural networks, which suffer from high false-positive rates on real photos and break under compression.  
> 
> TrustNet solves this through **Physics-Informed Evidential Fusion**. We combine deep convolutional and Vision Transformer representations with 12 deterministic physical and mathematical invariants:  
> - We inspect **2D Fourier optical lens roll-off**,  
> - **Sub-pixel Bayer CFA demosaicing residuals**,  
> - **Error Level Analysis (ELA)** compression disparity,  
> - **Corneal specular reflection vectors** in human pupils,  
> - And **AI provenance metadata signatures**.  
> 
> In addition, we have integrated a local-first **LM Studio Vision Reasoning Engine** (`Qwen3-VL`) that performs explainable visual analysis 100% locally with zero cloud dependencies and zero data privacy leakage.  
> 
> The platform is built on an enterprise-grade **Microservices Architecture** with an asynchronous FastAPI Gateway, Kafka event workers, and a dedicated Trust Engine for calibrated multi-vector scoring.  
> 
> I am now ready to demonstrate the live system and walk you through the codebase."*
