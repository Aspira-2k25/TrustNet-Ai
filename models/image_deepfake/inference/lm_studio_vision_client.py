import os
import io
import re
import json
import base64
import logging
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, List
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("trustnet.lm_studio_vision")


class LMStudioVisionClient:
    """
    Local Vision Model Client connecting to LM Studio's OpenAI-compatible API.
    Designed specifically for local vision models such as Qwen3-VL (e.g. unsloth/Qwen3-VL-4B-Thinking-GGUF).
    
    Responsibilities:
    - Analyzes visual semantic inconsistencies, texture boundaries, lighting, and scene structure.
    - Correlates visible features with deterministic forensic layers without hallucinating pixel math.
    - Strips <think>...</think> reasoning blocks from thinking models.
    - Emits strict structured JSON with robust schema validation and fallback handling.
    - Preprocesses images into an optimized, resolution-capped copy (<150KB) to minimize latency.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout: Optional[int] = None
    ):
        self.base_url = (base_url or os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")).rstrip("/")
        self.configured_model = model_name or os.getenv("LM_STUDIO_MODEL", "")
        self.timeout = int(timeout or os.getenv("LM_STUDIO_TIMEOUT_SECONDS", "1800"))
        self.max_tokens = int(os.getenv("LM_STUDIO_MAX_TOKENS", "350"))
        self._cached_discovered_model: Optional[str] = None

    def get_active_model_name(self) -> str:
        """
        Returns the configured model name, or queries LM Studio GET /v1/models
        to dynamically auto-detect whatever vision model is currently loaded in memory.
        """
        if self.configured_model:
            return self.configured_model
            
        if self._cached_discovered_model:
            return self._cached_discovered_model

        try:
            req = urllib.request.Request(
                f"{self.base_url}/models",
                headers={"User-Agent": "TrustNet-Forensics/1.0"}
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models_list = data.get("data", [])
                if models_list and isinstance(models_list, list):
                    discovered = models_list[0].get("id")
                    if discovered:
                        self._cached_discovered_model = discovered
                        logger.info(f"[VISION] Discovered loaded LM Studio model: {discovered}")
                        return discovered
        except Exception as e:
            logger.debug(f"[VISION] Could not auto-discover LM Studio model: {e}")

        return "unsloth/Qwen3-VL-4B-Thinking-GGUF"

    def optimize_image_for_vision(self, image_bytes: bytes, max_dim: int = 256) -> str:
        """
        Optimizes the image for LM Studio vision input without modifying the original:
        - Downscales to max dimension (default 256px) keeping aspect ratio to minimize vision tokens and latency on local hardware.
        - Converts to standard RGB JPEG with quality 80 to keep payload under 50KB.
        - Returns a base64 data URL: data:image/jpeg;base64,...
        """
        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                orig_w, orig_h = img.size
                scale = min(1.0, max_dim / max(orig_w, orig_h))
                new_w = max(1, int(orig_w * scale))
                new_h = max(1, int(orig_h * scale))

                if scale < 1.0:
                    resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                else:
                    resized = img.copy()

                if resized.mode != "RGB":
                    resized = resized.convert("RGB")

                buf = io.BytesIO()
                resized.save(buf, format="JPEG", quality=80, optimize=True)
                b64_bytes = base64.b64encode(buf.getvalue()).decode("utf-8")
                return f"data:image/jpeg;base64,{b64_bytes}"
        except Exception as e:
            logger.warning(f"[VISION] Image preprocessing fallback: {e}")
            b64_bytes = base64.b64encode(image_bytes).decode("utf-8")
            return f"data:image/jpeg;base64,{b64_bytes}"

    def analyze(
        self,
        image_bytes: bytes,
        forensic_evidence: Dict[str, Any],
        scene_type: str = "general_photo"
    ) -> Dict[str, Any]:
        """
        Executes a single, structured visual inspection request to the LM Studio model.
        Fuses the supplied deterministic forensic measurements with visual reasoning.
        """
        model_name = self.get_active_model_name()
        logger.info(f"[VISION] Sending image to LM Studio ({model_name}) at {self.base_url}")

        # 1. Optimize image copy for vision reasoning
        image_data_url = self.optimize_image_for_vision(image_bytes)

        # 2. High-efficiency balanced system prompt
        system_prompt = (
            "You are an expert image-forensics visual reasoning assistant.\n"
            "Carefully evaluate whether this image is an authentic real camera photograph or an AI-generated/manipulated image.\n"
            "Authentic camera photos show natural skin pores, realistic depth of field, coherent indoor architecture, and legible real signage.\n"
            "AI-generated images show plastic doll skin, melted background signage, impossible anatomy, or mismatched ear/eye reflections.\n"
            "If the subject shows natural human facial features in a real physical setting (e.g. restaurant, home, street), classify visual_verdict as 'authentic'.\n"
            "Keep internal reasoning very brief (under 15 words) and output strict JSON:\n"
            "{\n"
            '  "visual_verdict": "authentic" | "suspicious" | "inconclusive",\n'
            '  "confidence": <float between 0.0 and 1.0>,\n'
            '  "observations": [<string>, ...],\n'
            '  "suspicious_regions": [{"region": "<name>", "reason": "<string>"}],\n'
            '  "supporting_evidence": [<string>, ...],\n'
            '  "contradicting_evidence": [<string>, ...],\n'
            '  "uncertainties": [<string>, ...],\n'
            '  "simple_explanation": "<concise 1-2 sentence plain-English summary for non-experts>"\n'
            "}"
        )

        # 3. Compact evidence context string
        evidence_summary_str = (
            f"Scene: {scene_type}, Faces: {forensic_evidence.get('face_count', 0)}, "
            f"Boundary score: {forensic_evidence.get('face_boundary_anomaly_score', 0.0):.2f}, "
            f"Reflection anomaly: {forensic_evidence.get('physics_anomaly_score', 0.0):.2f}, "
            f"Compression ELA: {forensic_evidence.get('ela_anomaly_score', 0.0):.2f}, "
            f"Noise PRNU: {forensic_evidence.get('noise_anomaly_score', 0.0):.2f}, "
            f"Watermark: {forensic_evidence.get('is_watermark_found', False)}"
        )

        user_content = [
            {
                "type": "text",
                "text": (
                    f"Forensic Context: {evidence_summary_str}\n"
                    "Inspect this image: distinguish authentic real camera capture from synthetic AI generation. Output strict JSON only."
                )
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": image_data_url
                }
            }
        ]

        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            "temperature": 0.1,
            "max_tokens": self.max_tokens,
            "stream": True
        }

        try:
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{self.base_url}/chat/completions",
                data=req_data,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "TrustNet-Forensics/1.0"
                }
            )

            accumulated_chunks: List[str] = []
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                status_code = resp.status
                if status_code != 200:
                    raise RuntimeError(f"LM Studio returned HTTP {status_code}")
                
                accumulated_reasoning: List[str] = []
                for line in resp:
                    line_str = line.decode("utf-8").strip()
                    if not line_str:
                        continue
                    if line_str == "data: [DONE]":
                        break
                    if line_str.startswith("data: "):
                        try:
                            chunk = json.loads(line_str[6:])
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                accumulated_chunks.append(content)
                            reasoning = delta.get("reasoning_content", "")
                            if reasoning:
                                accumulated_reasoning.append(reasoning)
                        except Exception:
                            pass

            raw_content = "".join(accumulated_chunks)
            reasoning_str = "".join(accumulated_reasoning)
            
            # If model put JSON inside reasoning or finished reasoning with JSON
            if not raw_content and reasoning_str:
                raw_content = reasoning_str

            logger.info(f"[VISION] Model response received ({len(raw_content)} chars, {len(reasoning_str)} reasoning chars)")

            # Parse and validate the response
            parsed_result = self._parse_and_validate_response(raw_content, model_name, reasoning_str=reasoning_str)
            if parsed_result.get("status") != "UNAVAILABLE":
                parsed_result["status"] = "APPLIED"
            parsed_result["model_name"] = model_name
            return parsed_result

        except urllib.error.URLError as e:
            logger.warning(f"[VISION] LM Studio offline or connection refused ({e})")
            return self._build_unavailable_response(
                model_name=model_name,
                reason="LM Studio local server is offline or unreachable on http://localhost:1234."
            )
        except TimeoutError:
            logger.warning(f"[VISION] LM Studio request timed out after {self.timeout}s")
            return self._build_unavailable_response(
                model_name=model_name,
                reason=f"LM Studio inference timed out after {self.timeout}s."
            )
        except Exception as e:
            logger.error(f"[VISION] Failed during LM Studio vision analysis: {e}")
            return self._build_unavailable_response(
                model_name=model_name,
                reason=f"Vision analysis unavailable: {str(e)}"
            )

    def _parse_and_validate_response(self, raw_content: str, model_name: str, reasoning_str: str = "") -> Dict[str, Any]:
        """
        Robustly extracts structured JSON from the model response.
        Handles:
        - <think>...</think> reasoning tags (from Qwen3-VL-Thinking models).
        - streaming reasoning_content delta fields.
        - Markdown code fences (```json ... ```).
        - Trailing commas and slight JSON syntax anomalies.
        """
        # 1. Extract and preserve reasoning thoughts if present
        thinking_process = reasoning_str.strip() if reasoning_str else ""
        think_match = re.search(r"<think>(.*?)</think>", raw_content, flags=re.DOTALL)
        if think_match:
            thinking_process = think_match.group(1).strip()
            # Strip the thinking block so it doesn't pollute the JSON parser
            clean_text = re.sub(r"<think>.*?</think>", "", raw_content, flags=re.DOTALL).strip()
        else:
            clean_text = raw_content.strip()

        # 2. Extract JSON block
        json_str = ""
        fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", clean_text, flags=re.DOTALL)
        if fence_match:
            json_str = fence_match.group(1).strip()
        else:
            brace_match = re.search(r"(\{.*\})", clean_text, flags=re.DOTALL)
            if brace_match:
                json_str = brace_match.group(1).strip()
            else:
                json_str = clean_text

        # 3. Clean common JSON syntax defects (trailing commas)
        json_str = re.sub(r",\s*([\]}])", r"\1", json_str)

        try:
            data = json.loads(json_str)
        except Exception as e:
            salvaged = self._salvage_partial_json(clean_text)
            if salvaged is not None:
                logger.info("[VISION] Successfully salvaged partial JSON from model response")
                data = salvaged
            else:
                logger.warning(f"[VISION] Failed to parse model JSON: {e}. Raw content: {clean_text[:200]}")
                return self._build_unavailable_response(
                    model_name=model_name,
                    reason="Vision model returned malformed output format."
                )

        # 4. Strict Schema Validation & Sanitization
        raw_verdict = str(data.get("visual_verdict", "inconclusive")).lower()
        if raw_verdict in ["suspicious", "fake", "manipulated"]:
            visual_verdict = "suspicious"
        elif raw_verdict in ["authentic", "real", "genuine"]:
            visual_verdict = "authentic"
        else:
            visual_verdict = "inconclusive"

        try:
            confidence = float(data.get("confidence", 0.5))
            confidence = max(0.0, min(1.0, confidence))
        except (ValueError, TypeError):
            confidence = 0.5

        observations = [str(o) for o in data.get("observations", []) if o]
        suspicious_regions = []
        for r in data.get("suspicious_regions", []):
            if isinstance(r, dict) and "region" in r:
                suspicious_regions.append({
                    "region": str(r.get("region", "unspecified")),
                    "reason": str(r.get("reason", "Anomaly observed"))
                })

        supporting_evidence = [str(s) for s in data.get("supporting_evidence", []) if s]
        contradicting_evidence = [str(c) for c in data.get("contradicting_evidence", []) if c]
        uncertainties = [str(u) for u in data.get("uncertainties", []) if u]
        simple_explanation = str(data.get("simple_explanation", "")).strip()

        if not simple_explanation:
            if visual_verdict == "suspicious":
                simple_explanation = "Visual inspection detected subtle inconsistencies in texture, lighting, or structural boundaries."
            elif visual_verdict == "authentic":
                simple_explanation = "Visual inspection confirms coherent lighting, natural texture transitions, and anatomical symmetry."
            else:
                simple_explanation = "Visual inspection found mixed or ambiguous visual details requiring physical forensic verification."

        return {
            "visual_verdict": visual_verdict,
            "confidence": float(round(confidence, 3)),
            "observations": observations[:6],
            "suspicious_regions": suspicious_regions[:4],
            "supporting_evidence": supporting_evidence[:5],
            "contradicting_evidence": contradicting_evidence[:5],
            "uncertainties": uncertainties[:4],
            "simple_explanation": simple_explanation,
            "thinking_process": thinking_process
        }

    def _build_unavailable_response(self, model_name: str, reason: str) -> Dict[str, Any]:
        """Builds a deterministic unavailable structure without crashing or hallucinating."""
        return {
            "status": "UNAVAILABLE",
            "model_name": model_name,
            "visual_verdict": "inconclusive",
            "confidence": 0.0,
            "observations": [],
            "suspicious_regions": [],
            "supporting_evidence": [],
            "contradicting_evidence": [],
            "uncertainties": [reason],
            "simple_explanation": "Vision analysis unavailable. Result is based on available physical forensic checks.",
            "thinking_process": "",
            "reason": reason
        }

    def _salvage_partial_json(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Attempts to salvage key forensic fields if the model's JSON output
        was truncated by token limits before the closing bracket.
        """
        verdict_match = re.search(r'"visual_verdict":\s*"([^"]+)"', text)
        if not verdict_match:
            return None
        
        visual_verdict = verdict_match.group(1).lower()
        
        conf_match = re.search(r'"confidence":\s*([0-9.]+)', text)
        confidence = float(conf_match.group(1)) if conf_match else 0.75
        
        observations = []
        obs_match = re.search(r'"observations":\s*\[(.*?)\]', text, flags=re.DOTALL)
        if obs_match:
            items = re.findall(r'"([^"]+)"', obs_match.group(1))
            observations = [item for item in items if item]
        else:
            obs_start = re.search(r'"observations":\s*\[(.*)', text, flags=re.DOTALL)
            if obs_start:
                items = re.findall(r'"([^"]+)"', obs_start.group(1))
                observations = [item for item in items if item]

        exp_match = re.search(r'"simple_explanation":\s*"([^"]+)"', text)
        simple_explanation = exp_match.group(1) if exp_match else ""

        return {
            "visual_verdict": visual_verdict,
            "confidence": confidence,
            "observations": observations,
            "suspicious_regions": [],
            "supporting_evidence": [],
            "contradicting_evidence": [],
            "uncertainties": [],
            "simple_explanation": simple_explanation
        }
