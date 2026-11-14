import os
import re
import time
import json
import uuid
import random
import io
import urllib.parse
import logging
import requests
from resource_lock import acquire_gpu_heavy_lock
from typing import Optional, Dict, Any, Tuple, Callable, List

try:
    import photo_vault
except ImportError:
    photo_vault = None

logger = logging.getLogger(__name__)

def format_comfy_validation_error(res: requests.Response) -> str:
    """Parses ComfyUI validation or execution errors into a clear, readable message."""
    try:
        data = res.json()
        node_errors = data.get("node_errors", {})
        err_messages = []
        for node_id, node_info in node_errors.items():
            class_type = node_info.get("class_type", f"Node {node_id}")
            errors = node_info.get("errors", [])
            for err in errors:
                detail = err.get("details") or err.get("message") or err.get("type")
                if detail:
                    if "not in []" in str(detail) or "not in" in str(detail):
                        err_messages.append(f"{class_type} (#{node_id}): Model/File belum terpasang ({detail})")
                    else:
                        err_messages.append(f"{class_type} (#{node_id}): {detail}")
        if err_messages:
            return f"ComfyUI validation error: {'; '.join(err_messages)}"

        err_obj = data.get("error", {})
        if isinstance(err_obj, dict):
            msg = err_obj.get("message") or err_obj.get("type")
            details = err_obj.get("details")
            if details:
                return f"ComfyUI error: {msg} ({details})"
            if msg:
                return f"ComfyUI error: {msg}"
        elif isinstance(err_obj, str):
            return f"ComfyUI error: {err_obj}"
    except Exception:
        pass
    return f"ComfyUI menolak prompt (HTTP {res.status_code}): {res.text[:250]}"

def format_agy_error(raw_err: Optional[str]) -> str:
    """Formats a concise, user-friendly explanation of why AGY image generation failed."""
    if not raw_err:
        return "Layanan Google Antigravity (AGY) tidak memberikan respon gambar."
    raw_lower = raw_err.lower()
    if "429" in raw_err or "quota exhausted" in raw_lower or "resource_exhausted" in raw_lower or "capacity on the underlying" in raw_lower:
        return "Batas kuota model gambar Google Antigravity habis (429 RESOURCE_EXHAUSTED). Model sedang cooldown."
    if "dispatched the generation request" in raw_lower or "waiting for the image" in raw_lower or "delegated the image generation" in raw_lower:
        return "Subagent AGY sedang dalam antrean atau kuota API gambar sedang cooldown. Mengalihkan otomatis ke generator cadangan..."
    if "connection refused" in raw_lower or "10061" in raw_err or "failed to establish a new connection" in raw_lower:
        return "Koneksi ke AGY Bridge (port 8001) terputus atau service sedang offline."
    if "timeout" in raw_lower or "timed out" in raw_lower:
        return "Waktu tunggu generasi gambar AGY habis (Timeout > 120 detik)."
    if "tidak ditemukan di path" in raw_lower:
        return "Executable Antigravity CLI ('agy') tidak ditemukan di PATH sistem PC."
    clean = re.sub(r'^(?:AGY CLI selesai namun tidak menemukan file gambar output:\s*|Failed to generate image:\s*|AGY Bridge error:\s*)', '', raw_err).strip()
    return clean[:160] if clean else raw_err[:160]

def extract_combo_choices(raw_field: Any) -> List[str]:
    """Safely extracts list of string choices from ComfyUI node input definitions."""
    if not raw_field:
        return []
    if isinstance(raw_field, list):
        if len(raw_field) > 0 and isinstance(raw_field[0], list):
            return [str(x) for x in raw_field[0] if isinstance(x, (str, int, float)) and len(str(x)) > 0]
        if len(raw_field) > 1 and isinstance(raw_field[1], dict) and "choices" in raw_field[1]:
            return [str(x) for x in raw_field[1]["choices"] if isinstance(x, (str, int, float)) and len(str(x)) > 0]
        if len(raw_field) > 1 and isinstance(raw_field[1], list):
            return [str(x) for x in raw_field[1] if isinstance(x, (str, int, float)) and len(str(x)) > 0]
        strings = [str(x) for x in raw_field if isinstance(x, str) and x.upper() not in ("COMBO", "STRING", "FLOAT", "INT", "BOOLEAN")]
        if strings:
            return strings
    return []

class MediaEngine:
    """Generates images and videos via local ComfyUI with cloud fallback."""

    def __init__(self, comfyui_url: str = "http://127.0.0.1:8188", allow_cloud_fallback: bool = False):
        self.last_error = None
        self.comfyui_url = comfyui_url.rstrip("/")
        self.allow_cloud_fallback = allow_cloud_fallback
        self.client_id = str(uuid.uuid4())

    def check_status(self) -> Dict[str, Any]:
        """Checks if local ComfyUI server is reachable and lists checkpoints."""
        try:
            r = requests.get(f"{self.comfyui_url}/system_stats", timeout=3)
            if r.status_code == 200:
                stats = r.json()
                vram_info = stats.get("devices", [{}])[0].get("name", "GPU")
                ckpts = self.get_available_checkpoints()
                return {
                    "online": True,
                    "backend": "ComfyUI Local",
                    "device": vram_info,
                    "checkpoints": ckpts,
                    "active_checkpoint": self.get_active_checkpoint()
                }
        except Exception:
            pass

        return {
            "online": False,
            "backend": "Cloud Fallback (Pollinations)" if self.allow_cloud_fallback else "ComfyUI Offline",
            "device": "Remote CPU/GPU",
            "active_checkpoint": self.get_active_checkpoint()
        }

    def get_active_checkpoint(self, is_nude: bool = False) -> str:
        """Determines the active image checkpoint model currently selected/available for SFW or NSFW."""
        ckpts = self.get_available_checkpoints()
        img_mode = os.environ.get("IMAGE_ENGINE_MODE", "unified").lower().strip()
        if img_mode in ("split", "hybrid"):
            if is_nude:
                env_ckpt = os.environ.get("NSFW_COMFYUI_CHECKPOINT", "").strip() or os.environ.get("COMFYUI_CHECKPOINT", "").strip()
            else:
                env_ckpt = os.environ.get("SFW_COMFYUI_CHECKPOINT", "").strip() or os.environ.get("COMFYUI_CHECKPOINT", "").strip()
        else:
            env_ckpt = (
                os.environ.get("COMFYUI_CHECKPOINT", "").strip()
                or os.environ.get("NSFW_COMFYUI_CHECKPOINT" if is_nude else "SFW_COMFYUI_CHECKPOINT", "").strip()
            )
        if env_ckpt and ckpts:
            matched = [c for c in ckpts if env_ckpt.lower() in c.lower()]
            if matched:
                return matched[0]
        if ckpts:
            valid_ckpts = [c for c in ckpts if not ("basnsfw" in c.lower() and "base" in c.lower())] or ckpts
            for c in valid_ckpts:
                if any(k in c.lower() for k in ["aom", "orange"]):
                    return c
            for c in valid_ckpts:
                if "meina" in c.lower():
                    return c
            for c in valid_ckpts:
                if any(k in c.lower() for k in ["anything", "xl"]):
                    return c
            return valid_ckpts[0]
        if env_ckpt:
            return env_ckpt
        try:
            import asset_manager
            info = asset_manager.get_asset_info("aom3")
            if info and info.get("installed") and info.get("target_path"):
                return os.path.basename(info["target_path"])
            info = asset_manager.get_asset_info("anything_xl")
            if info and info.get("installed") and info.get("target_path"):
                return os.path.basename(info["target_path"])
            info = asset_manager.get_asset_info("meinamix")
            if info and info.get("installed") and info.get("target_path"):
                return os.path.basename(info["target_path"])
        except Exception:
            pass
        return "AOM3A1B_orangemixs.safetensors"

    def get_available_checkpoints(self) -> list:
        """Queries ComfyUI for available checkpoint models."""
        try:
            r = requests.get(f"{self.comfyui_url}/object_info/CheckpointLoaderSimple", timeout=4)
            if r.status_code == 200:
                data = r.json()
                return data["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]
        except Exception:
            pass
        return []

    def get_available_vaes(self) -> list:
        """Queries ComfyUI for available VAE models."""
        try:
            r = requests.get(f"{self.comfyui_url}/object_info/VAELoader", timeout=4)
            if r.status_code == 200:
                data = r.json()
                return data["VAELoader"]["input"]["required"]["vae_name"][0]
        except Exception:
            pass
        return []

    def get_available_clips(self) -> list:
        """Queries ComfyUI for available CLIP text encoder models."""
        try:
            r = requests.get(f"{self.comfyui_url}/object_info/CLIPLoader", timeout=4)
            if r.status_code == 200:
                data = r.json()
                return data["CLIPLoader"]["input"]["required"]["clip_name"][0]
        except Exception:
            pass
        return []

    def get_available_unets(self) -> list:
        """Queries ComfyUI for available diffusion models (UNET)."""
        try:
            r = requests.get(f"{self.comfyui_url}/object_info/UNETLoader", timeout=4)
            if r.status_code == 200:
                data = r.json()
                return data["UNETLoader"]["input"]["required"]["unet_name"][0]
        except Exception:
            pass
        return []

    def _get_animatediff_loader_info(self) -> Optional[Dict[str, Any]]:
        """Inspects ComfyUI for available AnimateDiff motion module loader nodes and model files.
        Returns dictionary with loader configuration or None.
        """
        try:
            r = requests.get(f"{self.comfyui_url}/object_info", timeout=4)
            if r.status_code != 200:
                return None
            data = r.json()

            # Priority 1: Modern Gen2 Pipeline (ADE_LoadAnimateDiffModel + ADE_ApplyAnimateDiffModel / Simple)
            if "ADE_LoadAnimateDiffModel" in data and ("ADE_ApplyAnimateDiffModelSimple" in data or "ADE_ApplyAnimateDiffModel" in data):
                apply_class = "ADE_ApplyAnimateDiffModelSimple" if "ADE_ApplyAnimateDiffModelSimple" in data else "ADE_ApplyAnimateDiffModel"
                load_def = data["ADE_LoadAnimateDiffModel"]
                raw_models = load_def.get("input", {}).get("required", {}).get("model_name", [])
                choices = extract_combo_choices(raw_models)
                chosen_m = "mm_sd_v15_v2.ckpt"
                if choices:
                    for m in choices:
                        if "v15_v2" in m.lower():
                            chosen_m = m
                            break
                        elif "v15" in m.lower() or "mm" in m.lower():
                            chosen_m = m
                    if chosen_m not in choices:
                        chosen_m = choices[0]
                return {
                    "mode": "gen2",
                    "load_class": "ADE_LoadAnimateDiffModel",
                    "apply_class": apply_class,
                    "model_name": chosen_m
                }

            # Priority 2: All-in-One Gen1 Loaders (ADE_AnimateDiffLoaderWithContext, AnimateDiffLoader, ADE_AnimateDiffLoaderGen1)
            loader_candidates = [
                "ADE_AnimateDiffLoaderWithContext",
                "AnimateDiffLoader",
                "ADE_AnimateDiffLoaderGen1"
            ]
            for class_name in loader_candidates:
                if class_name in data:
                    node_def = data[class_name]
                    req_inputs = node_def.get("input", {}).get("required", {})
                    raw_models = req_inputs.get("model_name", [])
                    choices = extract_combo_choices(raw_models)
                    chosen_m = "mm_sd_v15_v2.ckpt"
                    if choices:
                        for m in choices:
                            if "v15_v2" in m.lower():
                                chosen_m = m
                                break
                            elif "v15" in m.lower() or "mm" in m.lower():
                                chosen_m = m
                        if chosen_m not in choices:
                            chosen_m = choices[0]

                    # Resolve beta_schedule if present
                    chosen_beta = None
                    if "beta_schedule" in req_inputs:
                        raw_beta = req_inputs.get("beta_schedule", [])
                        beta_choices = extract_combo_choices(raw_beta)
                        chosen_beta = "autoselect"
                        if beta_choices:
                            if "autoselect" in beta_choices:
                                chosen_beta = "autoselect"
                            elif "sqrt_linear (AnimateDiff)" in beta_choices:
                                chosen_beta = "sqrt_linear (AnimateDiff)"
                            elif "sqrt_linear" in beta_choices:
                                chosen_beta = "sqrt_linear"
                            else:
                                chosen_beta = beta_choices[0]

                    needs_context = "context_options" in req_inputs
                    has_uniform_context = "ADE_AnimateDiffUniformContextOptions" in data

                    return {
                        "mode": "gen1",
                        "loader_class": class_name,
                        "model_name": chosen_m,
                        "beta_schedule": chosen_beta,
                        "needs_context": needs_context,
                        "has_uniform_context": has_uniform_context
                    }
        except Exception as e:
            logger.debug(f"Error checking AnimateDiff loader in ComfyUI: {e}")
        return None

    @staticmethod
    def get_dimensions(aspect_ratio: str = "3:4", is_sdxl: bool = False) -> Tuple[int, int]:
        """Calculates optimal (width, height) tailored for SD 1.5 or SDXL based on aspect ratio."""
        ar = aspect_ratio.strip().replace(" ", "")
        if is_sdxl:
            table = {
                "3:4": (896, 1152),
                "4:3": (1152, 896),
                "9:16": (720, 1280),
                "16:9": (1280, 720),
                "1:1": (1024, 1024)
            }
            return table.get(ar, (896, 1152))
        else: # SD 1.5 (MeinaMix, AOM3)
            table = {
                "3:4": (576, 768),   # 3:4 portrait (576/768 = 0.75)
                "4:3": (768, 576),   # 4:3 landscape
                "9:16": (448, 768),  # Smartphone story/wallpaper (Height <= 768 prevents leg/body duplication in SD 1.5)
                "16:9": (768, 448),  # Widescreen
                "1:1": (512, 512)    # Square avatar
            }
            return table.get(ar, (576, 768))

    @staticmethod
    def get_quality_params(quality: str = "high", is_sdxl: bool = False) -> Tuple[int, float]:
        """Returns (steps, cfg) tailored for SD 1.5 vs SDXL."""
        q = quality.lower().strip()
        if is_sdxl:
            # SDXL (Anything XL) sweet spots: lower CFG (5.5-6.5) prevents oversaturation and lowers VRAM/steps
            if q in ("ultra", "best", "very_high"):
                return 26, 6.5
            elif q in ("fast", "low", "standard"):
                return 18, 5.5
            else: # high (SDXL optimal speed & fidelity)
                return 22, 6.0
        else:
            # SD 1.5 (MeinaMix)
            if q in ("ultra", "best", "very_high"):
                return 32, 8.0
            elif q in ("fast", "low", "standard"):
                return 20, 7.0
            else: # high (MeinaMix sweet spot)
                return 28, 7.5

    def generate_image_comfyui(
        self,
        prompt: str,
        negative_prompt: str = "(worst quality, low quality:1.4), bad anatomy, deformed eyes, (missing arm:1.5), (missing hand:1.5), (amputation:1.5), (amputee:1.5), (severed arm:1.5), (stump:1.5), (disappearing arm:1.4), (floating arms:1.4), (fused arms:1.4), (bad arms:1.4), (extra arms:1.4), extra limbs, bad hands, (missing fingers:1.4), (extra fingers:1.4), bad legs, extra legs, long legs, elongated limbs, poorly drawn legs, fused legs, multiple legs, folded legs, mutated, deformed, duplicate body, (2girls:1.5), (3girls:1.5), (multiple girls:1.5), (2people:1.5), (multiple persons:1.5), (group:1.5), (extra characters:1.5), (duplicate:1.4), blurry",
        aspect_ratio: Optional[str] = None,
        quality: Optional[str] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        steps: Optional[int] = None,
        cfg: Optional[float] = None,
        is_nude: bool = False,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> Optional[bytes]:
        """Runs standard Text-to-Image workflow on local ComfyUI with optimal anime settings."""
        with acquire_gpu_heavy_lock("ComfyUI Image Generation"):
            return self._execute_generate_image_comfyui(
                prompt=prompt,
                negative_prompt=negative_prompt,
                aspect_ratio=aspect_ratio,
                quality=quality,
                width=width,
                height=height,
                steps=steps,
                cfg=cfg,
                is_nude=is_nude,
                progress_callback=progress_callback
            )

    def _execute_generate_image_comfyui(
        self,
        prompt: str,
        negative_prompt: str = "(worst quality, low quality:1.4), bad anatomy, deformed eyes, (missing arm:1.5), (missing hand:1.5), (amputation:1.5), (amputee:1.5), (severed arm:1.5), (stump:1.5), (disappearing arm:1.4), (floating arms:1.4), (fused arms:1.4), (bad arms:1.4), (extra arms:1.4), extra limbs, bad hands, (missing fingers:1.4), (extra fingers:1.4), bad legs, extra legs, long legs, elongated limbs, poorly drawn legs, fused legs, multiple legs, folded legs, mutated, deformed, duplicate body, (2girls:1.5), (3girls:1.5), (multiple girls:1.5), (2people:1.5), (multiple persons:1.5), (group:1.5), (extra characters:1.5), (duplicate:1.4), blurry",
        aspect_ratio: Optional[str] = None,
        quality: Optional[str] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        steps: Optional[int] = None,
        cfg: Optional[float] = None,
        is_nude: bool = False,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> Optional[bytes]:
        ckpts = self.get_available_checkpoints()
        if not ckpts:
            logger.warning("No ComfyUI checkpoints found for T2I.")
            return None

        # Smart Checkpoint Selection for SFW vs NSFW:
        chosen_ckpt = self.get_active_checkpoint(is_nude=is_nude)
        if chosen_ckpt and ckpts:
            matched = [c for c in ckpts if chosen_ckpt.lower() in c.lower()]
            if matched:
                chosen_ckpt = matched[0]

        # Filter out incomplete / UNet-only checkpoints that lack CLIP or VAE (e.g. BASNSFW...baseV10)
        valid_ckpts = [c for c in ckpts if not ("basnsfw" in c.lower() and "base" in c.lower())]
        if not valid_ckpts:
            valid_ckpts = ckpts

        # 2. Prefer AbyssOrangeMix3 (AOM3 / OrangeMix) if present (Default SD 1.5 anime uncensored model)
        if not chosen_ckpt:
            for c in valid_ckpts:
                if any(k in c.lower() for k in ["aom", "orange"]):
                    chosen_ckpt = c
                    break

        # 3. Prefer MeinaMix if present in folder (SD 1.5 anime model with CLIP & VAE, handles SFW & NSFW)
        if not chosen_ckpt:
            for c in valid_ckpts:
                if "meina" in c.lower():
                    chosen_ckpt = c
                    break

        # 4. Prefer Anything XL if present
        if not chosen_ckpt:
            for c in valid_ckpts:
                if any(k in c.lower() for k in ["anything", "xl"]):
                    chosen_ckpt = c
                    break

        # 4. Check if dedicated uncensored hentai/NSFW model requested & available
        is_explicit_nsfw = any(k in prompt.lower() for k in ["completely nude", "bare body", "full body nude", "nipples", "bare skin", "sensual lace lingerie", "lingerie"])
        if is_explicit_nsfw and not chosen_ckpt:
            for c in valid_ckpts:
                if any(k in c.lower() for k in ["hentai", "nsfw"]):
                    chosen_ckpt = c
                    logger.info(f"Auto-selected dedicated uncensored anime model: {chosen_ckpt}")
                    break

        # 5. Fallback to first available valid checkpoint
        if not chosen_ckpt:
            chosen_ckpt = valid_ckpts[0]

        is_sdxl = any(k in chosen_ckpt.lower() for k in ["xl", "sdxl", "pony", "illustrious"])

        # Determine Aspect Ratio & Dimensions
        ar = aspect_ratio or os.environ.get("IMAGE_ASPECT_RATIO", "3:4")
        if width is None or height is None:
            width, height = self.get_dimensions(ar, is_sdxl=is_sdxl)

        # Determine Quality Parameters (steps & cfg)
        qual = quality or os.environ.get("IMAGE_QUALITY", "high")
        def_steps, def_cfg = self.get_quality_params(qual, is_sdxl=is_sdxl)
        if steps is None:
            steps = def_steps
        if cfg is None:
            cfg = def_cfg

        # Optimal sampler: DPM++ 2M Karras for MeinaMix / Anime SD 1.5
        sampler_name = "euler_ancestral" if is_sdxl else "dpmpp_2m"
        scheduler_name = "normal" if is_sdxl else "karras"

        seed = random.randint(10000000, 99999999)

        # Detect optional external VAE (e.g. orangemix.vae.pt for SD 1.5)
        available_vaes = self.get_available_vaes()
        chosen_vae = None
        if not is_sdxl:
            for v in available_vaes:
                if any(k in v.lower() for k in ["orangemix", "anime", "vae-ft", "kl-f8"]):
                    chosen_vae = v
                    break
        else:
            # For SDXL, only use external VAE if explicitly matching sdxl
            for v in available_vaes:
                if "sdxl" in v.lower():
                    chosen_vae = v
                    break

        workflow = {
            "4": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": chosen_ckpt}
            },
            # Clip Skip 2 for anime models (MeinaMix & AOM3)
            "11": {
                "class_type": "CLIPSetLastLayer",
                "inputs": {"stop_at_clip_layer": -2, "clip": ["4", 1]}
            },
            "5": {
                "class_type": "EmptyLatentImage",
                "inputs": {"width": width, "height": height, "batch_size": 1}
            },
            "6": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": prompt, "clip": ["11", 0]}
            },
            "7": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": negative_prompt, "clip": ["11", 0]}
            },
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": seed,
                    "steps": steps,
                    "cfg": cfg,
                    "sampler_name": sampler_name,
                    "scheduler": scheduler_name,
                    "denoise": 1.0,
                    "model": ["4", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["5", 0]
                }
            },
            "8": {
                "class_type": "VAEDecode",
                "inputs": {"samples": ["3", 0], "vae": ["10", 0] if chosen_vae else ["4", 2]}
            },
            "9": {
                "class_type": "SaveImage",
                "inputs": {"filename_prefix": "WaifuSelfie", "images": ["8", 0]}
            }
        }

        # If a dedicated anime VAE exists in models/vae, wire it in
        if chosen_vae:
            workflow["10"] = {
                "class_type": "VAELoader",
                "inputs": {"vae_name": chosen_vae}
            }

        try:
            # Queue prompt
            res = requests.post(
                f"{self.comfyui_url}/prompt",
                json={"prompt": workflow, "client_id": self.client_id},
                timeout=10
            )
            if res.status_code != 200:
                logger.warning(f"ComfyUI rejected prompt: {res.text}")
                self.last_error = format_comfy_validation_error(res)
                return None

            prompt_id = res.json().get("prompt_id")
            if not prompt_id:
                self.last_error = "ComfyUI tidak mengembalikan prompt_id."
                return None

            m_label = "Anything XL (SDXL)" if is_sdxl else ("AbyssOrangeMix3 (SD 1.5)" if any(k in chosen_ckpt.lower() for k in ["aom", "orange"]) else "MeinaMix (SD 1.5)")
            start_poll = time.time()
            last_cb_time = 0.0

            # Poll history for completion
            for _ in range(160):  # Wait up to 240 seconds
                time.sleep(1.5)
                elapsed_sec = int(time.time() - start_poll)

                if progress_callback and (time.time() - last_cb_time >= 3.0):
                    last_cb_time = time.time()
                    if elapsed_sec < 10:
                        progress_callback(f"Memuat model {m_label} ke GPU... ({elapsed_sec}s)")
                    else:
                        progress_callback(f"Merender gambar waifu ({m_label}, {elapsed_sec}s)...")

                try:
                    h_res = requests.get(f"{self.comfyui_url}/history/{prompt_id}", timeout=5)
                except Exception:
                    continue
                if h_res.status_code == 200:
                    h_data = h_res.json()
                    if prompt_id in h_data:
                        task = h_data[prompt_id]
                        status = task.get("status", {})
                        if status.get("status_str") == "error":
                            messages = status.get("messages", [])
                            err_detail = "Node error"
                            for m in messages:
                                if isinstance(m, list) and len(m) > 1 and m[0] == "execution_error":
                                    info = m[1]
                                    err_detail = f"{info.get('node_type')}: {info.get('exception_message', '').strip()}"
                                    break
                            logger.error(f"ComfyUI node execution error: {status.get('messages')}")
                            self.last_error = f"ComfyUI execution error ({err_detail})"
                            return None

                        outputs = task.get("outputs", {})
                        if "9" in outputs and "images" in outputs["9"]:
                            if progress_callback:
                                progress_callback("Mendekode gambar & menyempurnakan hasil... ✨")
                            img_info = outputs["9"]["images"][0]
                            img_name = img_info["filename"]
                            subfolder = img_info.get("subfolder", "")
                            img_type = img_info.get("type", "output")

                            # Fetch image binary
                            view_url = f"{self.comfyui_url}/view?filename={img_name}&subfolder={subfolder}&type={img_type}"
                            img_resp = requests.get(view_url, timeout=30)
                            if img_resp.status_code == 200:
                                return img_resp.content

            if not self.last_error:
                self.last_error = "ComfyUI timeout: waktu rendering melebihi 240 detik (antrean sibuk atau VRAM terbatas)."

        except requests.exceptions.ConnectionError:
            self.last_error = f"Tidak dapat terhubung ke ComfyUI di {self.comfyui_url}. Pastikan ComfyUI sudah aktif."
            logger.error(self.last_error)
        except Exception as e:
            logger.error(f"ComfyUI generation error: {e}")
            self.last_error = f"Error komunikasi ComfyUI: {e}"
        finally:
            self._free_comfyui_vram()

        return None

    def _free_comfyui_vram(self, unload_models: bool = True, free_memory: bool = True) -> bool:
        """Requests ComfyUI to unload cached model weights from VRAM/RAM after rendering."""
        if not self.comfyui_url:
            return False
        enabled = os.environ.get("COMFYUI_FREE_VRAM_AFTER_GEN", "true").strip().lower() in ("1", "true", "yes", "on")
        if not enabled:
            return False
        try:
            r = requests.post(
                f"{self.comfyui_url}/free",
                json={"unload_models": bool(unload_models), "free_memory": bool(free_memory)},
                timeout=3
            )
            return r.status_code == 200
        except Exception:
            return False

    def generate_image_cloud_fallback(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        width: int = 768,
        height: int = 1024,
        aspect_ratio: Optional[str] = None
    ) -> Optional[bytes]:
        """Free, ultra-fast cloud fallback via Pollinations AI (0 local VRAM required)."""
        clean_p = urllib.parse.quote(prompt)
        seed = random.randint(1000, 999999)
        url = f"https://image.pollinations.ai/prompt/{clean_p}?width={width}&height={height}&seed={seed}&nologo=true&enhance=true"
        if negative_prompt:
            clean_neg = urllib.parse.quote(negative_prompt)
            url += f"&negative={clean_neg}"

        try:
            r = requests.get(url, timeout=40)
            if r.status_code == 200 and r.content:
                return r.content
        except Exception as e:
            logger.error(f"Cloud image fallback error: {e}")

        return None

    generate_image_cloud = generate_image_cloud_fallback

    def generate_photo(
        self,
        visual_prompt: str = "",
        prompt: Optional[str] = None,
        negative_prompt: Optional[str] = None,
        aspect_ratio: Optional[str] = None,
        quality: Optional[str] = None,
        persona: str = "runa",
        scene: str = "",
        outfit_label: str = "",
        is_nude: bool = False,
        user_query: str = "",
        progress_callback: Optional[Callable[[str], None]] = None,
        user_id: Optional[Any] = None
    ) -> Tuple[Optional[bytes], str]:
        """
        Main entry for photo generation.
        1. Tries local ComfyUI or external engine (AGY / Cloud).
        2. On success: archives photo into Photo Vault with semantic metadata.
        3. On failure / offline: searches Photo Vault for unseen matching persona & scene.
        4. If Photo Vault has no unseen photos: invokes live Cloud fallback so photos are ALWAYS unique.
        Returns: (image_bytes, source_label)
        """
        self.last_error = None
        self.last_fallback_notice = None
        effective_prompt = prompt or visual_prompt

        # SFW External Engine Routing (Independent of local ComfyUI state)
        sfw_engine = os.environ.get("SFW_IMAGE_ENGINE", "comfyui").lower().strip()
        if not is_nude and sfw_engine == "agy":
            from agy_quota_manager import (
                is_agy_image_quota_exhausted,
                record_agy_image_quota_exhausted,
                is_agy_quota_error,
                has_local_image_models
            )
            if is_agy_image_quota_exhausted():
                logger.info("Smart Fallback: Kuota gambar AGY habis hari ini. Langsung menggunakan smart fallback.")
                self.last_fallback_notice = {
                    "primary_engine": "Google Antigravity (AGY)",
                    "error": "Batas kuota model gambar Google Antigravity habis untuk hari ini (Smart Fallback aktif otomatis hingga besok)."
                }
                agy_img = None
            else:
                agy_img = self.generate_image_agy(effective_prompt, negative_prompt=negative_prompt, aspect_ratio=aspect_ratio, progress_callback=progress_callback)
                if agy_img:
                    if photo_vault:
                        try:
                            ent = photo_vault.save_photo_to_vault(
                                agy_img,
                                persona=persona,
                                scene=scene or user_query,
                                outfit_label=outfit_label,
                                is_nude=is_nude,
                                visual_prompt=effective_prompt,
                                user_query=user_query,
                                aspect_ratio=aspect_ratio or "3:4"
                            )
                            if ent and user_id and hasattr(photo_vault, "mark_photo_seen_by_user"):
                                photo_vault.mark_photo_seen_by_user(user_id, ent.get("filename", ""))
                        except Exception:
                            pass
                    return agy_img, "Google Antigravity (AGY Image Generator)"
                else:
                    if is_agy_quota_error(self.last_error):
                        record_agy_image_quota_exhausted(reason=self.last_error)
                    self.last_fallback_notice = {
                        "primary_engine": "Google Antigravity (AGY)",
                        "error": format_agy_error(self.last_error)
                    }
        elif not is_nude and sfw_engine == "cloud":
            cloud_img = self.generate_image_cloud(effective_prompt, negative_prompt=negative_prompt, aspect_ratio=aspect_ratio)
            if cloud_img:
                return cloud_img, "Cloud Engine (SFW Pollinations)"
            else:
                self.last_fallback_notice = {
                    "primary_engine": "Cloud Engine",
                    "error": self.last_error or "Layanan cloud Pollinations tidak merespons."
                }

        # Local ComfyUI (Used for NSFW and for SFW when engine is comfyui or as fallback when primary fails)
        from agy_quota_manager import has_local_image_models
        local_models_available = has_local_image_models()

        if is_nude or sfw_engine == "comfyui" or self.last_fallback_notice:
            # If user has local image models, ensure ComfyUI is awake and ready
            if local_models_available:
                if not self.comfyui_url:
                    self.comfyui_url = "http://127.0.0.1:8188"
                from idle_engine import is_port_listening
                if not is_port_listening(8188):
                    try:
                        import bot
                        if hasattr(bot, "idle_engine") and bot.idle_engine:
                            if progress_callback:
                                progress_callback("Membangunkan studio foto lokal ComfyUI... ⏳")
                            bot.idle_engine.wake_comfyui()
                    except Exception as e_wake:
                        logger.warning(f"Could not wake ComfyUI on-demand: {e_wake}")

            if self.comfyui_url:
                local_img = self.generate_image_comfyui(
                    effective_prompt,
                    negative_prompt=negative_prompt or "(worst quality, low quality:1.4), bad anatomy, deformed eyes, (missing arm:1.5), (missing hand:1.5), (amputation:1.5), (amputee:1.5), (severed arm:1.5), (stump:1.5), (disappearing arm:1.4), (floating arms:1.4), (fused arms:1.4), (bad arms:1.4), (extra arms:1.4), extra limbs, bad hands, (missing fingers:1.4), (extra fingers:1.4), bad legs, extra legs, long legs, elongated limbs, poorly drawn legs, fused legs, multiple legs, folded legs, mutated, deformed, duplicate body, (2girls:1.5), (3girls:1.5), (multiple girls:1.5), (2people:1.5), (multiple persons:1.5), (group:1.5), (extra characters:1.5), (duplicate:1.4), blurry",
                    aspect_ratio=aspect_ratio,
                    quality=quality,
                    is_nude=is_nude,
                    progress_callback=progress_callback
                )
                if local_img:
                    # Automatically save high-quality local render to Photo Vault
                    if photo_vault:
                        try:
                            ent = photo_vault.save_photo_to_vault(
                                local_img,
                                persona=persona,
                                scene=scene or user_query,
                                outfit_label=outfit_label,
                                is_nude=is_nude,
                                visual_prompt=effective_prompt,
                                user_query=user_query,
                                aspect_ratio=aspect_ratio or "3:4"
                            )
                            if ent and user_id and hasattr(photo_vault, "mark_photo_seen_by_user"):
                                photo_vault.mark_photo_seen_by_user(user_id, ent.get("filename", ""))
                        except Exception as e_save:
                            logger.warning(f"Failed to auto-archive photo to vault: {e_save}")
                    active_ckpt = self.get_active_checkpoint(is_nude=is_nude)
                    clean_name = os.path.splitext(active_ckpt)[0]
                    return local_img, f"Local ComfyUI ({clean_name})"
                else:
                    if not self.last_fallback_notice:
                        self.last_fallback_notice = {
                            "primary_engine": "Local ComfyUI",
                            "error": self.last_error or "Layanan ComfyUI di port 8188 tidak merespons atau model gagal dimuat."
                        }
            else:
                self.last_error = "ComfyUI URL belum dikonfigurasi (pastikan ComfyUI lokal aktif di port 8188)."
                if not self.last_fallback_notice:
                    self.last_fallback_notice = {
                        "primary_engine": "Local ComfyUI",
                        "error": self.last_error
                    }

        # 2. Smart Photo Vault Retrieval (Offline Semantic Fallback - strictly unique per user)
        use_vault = os.environ.get("MEDIA_VAULT_FALLBACK", "true").lower() in ("true", "1", "yes")
        if photo_vault and use_vault:
            try:
                matched = photo_vault.find_matching_photo(
                    persona=persona,
                    scene=scene or user_query,
                    outfit_label=outfit_label,
                    is_nude=is_nude,
                    user_query=user_query,
                    user_id=user_id
                )
                if matched:
                    vault_img, meta = matched
                    p_name = meta.get('persona', persona).title()
                    logger.info(f"Retrieved unique photo from vault: {meta.get('filename')} (Scene: {meta.get('scene')}, User: {user_id})")
                    return vault_img, f"Photo Vault (Arsip Lokal: {p_name})"
            except Exception as e_find:
                logger.warning(f"Error querying photo vault: {e_find}")

        # 3. Live Cloud Fallback (Pollinations)
        # CRITICAL USER RULE:
        # Jika user pilih AGY untuk generate image, maka fallback TIDAK BOLEH ke Pollinations
        # jika user sudah punya model lokal ComfyUI (hanya boleh ke Pollinations jika memang TIDAK punya model lokal).
        if sfw_engine == "agy" and local_models_available:
            allow_cloud = False
        else:
            allow_cloud = (os.environ.get("MEDIA_FALLBACK_CLOUD", "true").lower() in ("true", "1", "yes")) or (self.last_fallback_notice is not None)

        if not is_nude and allow_cloud:
            cloud_img = self.generate_image_cloud_fallback(effective_prompt, negative_prompt=negative_prompt)
            if cloud_img:
                if photo_vault:
                    try:
                        ent = photo_vault.save_photo_to_vault(
                            cloud_img,
                            persona=persona,
                            scene=scene or user_query,
                            outfit_label=outfit_label,
                            is_nude=is_nude,
                            visual_prompt=effective_prompt,
                            user_query=user_query,
                            aspect_ratio=aspect_ratio or "3:4"
                        )
                        if ent and user_id and hasattr(photo_vault, "mark_photo_seen_by_user"):
                            photo_vault.mark_photo_seen_by_user(user_id, ent.get("filename", ""))
                    except Exception:
                        pass
                return cloud_img, "Cloud Engine (SFW Fallback Unik)"

        return None, "Failed"

    def generate_image_agy(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        aspect_ratio: Optional[str] = None,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> Optional[bytes]:
        """
        Generates an image using Google Antigravity CLI (AGY) image-generator subagent.
        First attempts to query local AGY Bridge at http://127.0.0.1:8001/v1/images/generations.
        If Bridge is unreachable, invokes `agy` CLI directly.
        """
        from agy_quota_manager import (
            is_agy_image_quota_exhausted,
            record_agy_image_quota_exhausted,
            is_agy_quota_error
        )
        if is_agy_image_quota_exhausted():
            logger.info("Smart Fallback: Kuota gambar AGY hari ini habis. Menghindari request ke AGY.")
            self.last_error = "Batas kuota model gambar Google Antigravity habis untuk hari ini (Smart Fallback aktif otomatis hingga besok)."
            return None

        if progress_callback:
            progress_callback("Menghubungkan ke Google Antigravity (AGY Image Generator)... 🎨")

        agy_effective_prompt = prompt
        if negative_prompt:
            agy_effective_prompt = f"{prompt}. Negative constraints (strictly avoid): {negative_prompt}"

        agy_port = int(os.environ.get("AGY_BRIDGE_PORT", "8001"))
        bridge_url = f"http://127.0.0.1:{agy_port}/v1/images/generations"

        # Auto-wake / auto-run AGY Bridge if enabled and offline
        from idle_engine import is_port_listening
        if not is_port_listening(agy_port, timeout=1.5):
            try:
                import sys, subprocess
                proj_root = os.path.dirname(os.path.abspath(__file__))
                agy_script = os.path.join(proj_root, "agy_bridge.py")
                if os.path.exists(agy_script):
                    logger.info("AGY Bridge is offline. Auto-starting AGY OpenAI Bridge on port 8001...")
                    popen_kwargs = {"creationflags": 0x08000000 | 0x00000200} if sys.platform == "win32" else {"start_new_session": True}
                    spawn_env = os.environ.copy()
                    spawn_env["PYTHONIOENCODING"] = "utf-8"
                    spawn_env["PYTHONUTF8"] = "1"
                    subprocess.Popen([sys.executable, agy_script], cwd=proj_root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=spawn_env, **popen_kwargs)
                    for _ in range(12):
                        time.sleep(0.5)
                        if is_port_listening(agy_port, timeout=1.5):
                            break
            except Exception as e_start:
                logger.debug(f"Failed to auto-start AGY bridge: {e_start}")

        try:
            import bot
            if hasattr(bot, "idle_engine") and bot.idle_engine:
                bot.idle_engine.record_activity(is_agy=True)
        except Exception:
            pass

        # 1. Try via AGY OpenAI Bridge
        try:
            req_body = {
                "prompt": agy_effective_prompt,
                "n": 1,
                "size": "1024x1024",
                "response_format": "b64_json"
            }
            if progress_callback:
                progress_callback("AGY image-generator sedang merender gambar... ✨")
            res = requests.post(bridge_url, json=req_body, timeout=120)
            if res.status_code == 200:
                data = res.json()
                b64_data = data.get("data", [{}])[0].get("b64_json")
                if b64_data:
                    import base64
                    return base64.b64decode(b64_data)
            else:
                resp_text = res.text
                if res.status_code == 429 or is_agy_quota_error(resp_text):
                    record_agy_image_quota_exhausted(reason=f"HTTP {res.status_code}: {resp_text[:150]}")
                    self.last_error = f"Batas kuota model gambar Google Antigravity habis ({res.status_code}). Model sedang cooldown."
                    return None
        except Exception as e_bridge:
            logger.debug(f"AGY Bridge image generation call failed: {e_bridge}. Trying direct CLI...")

        # 2. Fallback to direct agy CLI invocation
        import shutil, subprocess, re
        agy_bin = shutil.which("agy") or shutil.which("agy.cmd")
        if not agy_bin:
            self.last_error = "Google Antigravity CLI ('agy') tidak ditemukan di PATH sistem."
            return None

        instruction = (
            "Task: Generate an anime character image.\n"
            "Instructions:\n"
            "1. Delegate directly to the image-generator subagent using invoke_subagent with Role='Anime Character Illustrator'.\n"
            f"2. Image description: {agy_effective_prompt}\n\n"
            "CRITICAL: Once the subagent finishes generating the image, your response MUST contain "
            "the absolute file path to the generated image file (e.g. C:\\...\\image.jpg or file:///C:/...image.jpg)."
        )
        t0 = time.time()
        try:
            if progress_callback:
                progress_callback("Menjalankan subagent image-generator via agy CLI... ✨")
            proc = subprocess.run(
                [agy_bin, "-p", instruction, "--dangerously-skip-permissions"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=180
            )
            out = proc.stdout or ""
            if is_agy_quota_error(out):
                record_agy_image_quota_exhausted(reason=out[:200])
                self.last_error = "Batas kuota model gambar Google Antigravity habis (429 RESOURCE_EXHAUSTED). Model sedang cooldown."
                return None

            cand_path = None
            try:
                from agy_bridge import extract_image_path_from_agy_output, find_recent_generated_image
                cand_path = extract_image_path_from_agy_output(out)
                if not cand_path:
                    cand_path = find_recent_generated_image(t0, timeout_seconds=15.0)
            except Exception:
                cand_path = None

            if cand_path and os.path.isfile(cand_path) and os.path.getsize(cand_path) > 100:
                with open(cand_path, "rb") as f:
                    return f.read()

            self.last_error = f"AGY CLI selesai namun tidak menemukan file gambar output: {out[:120]}"
            return None
        except Exception as e_cli:
            self.last_error = f"AGY CLI image generation exception: {e_cli}"
            return None

    def generate_video(
        self,
        visual_prompt: str = "",
        negative_prompt: Optional[str] = None,
        aspect_ratio: Optional[str] = None,
        quality: Optional[str] = None,
        duration: float = 3.0,
        fps: int = 16,
        base_image_bytes: Optional[bytes] = None
    ) -> Tuple[Optional[bytes], str]:
        """
        Renders AI video animation using neural ComfyUI Video Engines (Wan 2.1 or AnimateDiff).
        No simple 2.5D motion: pure AI neural video generation.
        Returns: (video_bytes, source_label)
        """
        engine = os.environ.get("VIDEO_ENGINE", "wan21").lower().strip()
        if engine not in ("wan21", "animatediff"):
            engine = "wan21"

        logger.info(f"Generating AI video with engine: {engine}")

        # Dispatch to neural engine
        if engine == "wan21":
            vid_bytes = self.generate_video_wan21(
                visual_prompt=visual_prompt,
                negative_prompt=negative_prompt,
                base_image_bytes=base_image_bytes
            )
            if vid_bytes:
                return vid_bytes, "🌟 Wan 2.1 AI Video Engine"
        else: # animatediff
            vid_bytes = self.generate_video_animatediff(
                visual_prompt=visual_prompt,
                negative_prompt=negative_prompt,
                base_image_bytes=base_image_bytes
            )
            if vid_bytes:
                return vid_bytes, "🌸 AnimateDiff Anime Video Engine"

        return None, "Failed (Video Generation)"

    def _upload_image_to_comfy(self, img_bytes: bytes, filename: str = "waifu_source.png") -> Optional[str]:
        """Uploads raw image bytes to ComfyUI's input directory."""
        try:
            files = {"image": (filename, io.BytesIO(img_bytes), "image/png")}
            data = {"overwrite": "true"}
            r = requests.post(f"{self.comfyui_url}/upload/image", files=files, data=data, timeout=10)
            if r.status_code == 200:
                return r.json().get("name", filename)
        except Exception as e:
            logger.warning(f"Error uploading image to ComfyUI: {e}")
        return None

    def generate_video_wan21(
        self,
        visual_prompt: str,
        negative_prompt: Optional[str] = None,
        base_image_bytes: Optional[bytes] = None
    ) -> Optional[bytes]:
        """Executes Wan 2.1 1.3B AI Video pipeline on ComfyUI."""
        # Check required models in ComfyUI before dispatching
        available_clips = self.get_available_clips()
        clip_name = "umt5_xxl_fp8_e4m3fn_scaled.safetensors"
        if available_clips:
            if clip_name not in available_clips:
                matched_c = [c for c in available_clips if "umt5" in c.lower()]
                if matched_c:
                    clip_name = matched_c[0]
                else:
                    self.last_error = f"Model Text Encoder Wan 2.1 ('{clip_name}') belum terpasang di ComfyUI (models/clip). Silakan unduh via /video atau gunakan AnimateDiff."
                    return None
        elif self.comfyui_url:
            self.last_error = f"Model Text Encoder Wan 2.1 ('{clip_name}') belum terpasang di ComfyUI (models/clip). Silakan unduh via /video atau gunakan AnimateDiff."
            return None

        available_unets = self.get_available_unets()
        unet_name = "wan2.1_t2v_1.3B_bf16.safetensors"
        if available_unets:
            if unet_name not in available_unets:
                matched_u = [u for u in available_unets if "wan" in u.lower() and "1.3b" in u.lower()]
                if matched_u:
                    unet_name = matched_u[0]
                else:
                    self.last_error = f"Model Diffusion Wan 2.1 ('{unet_name}') belum terpasang di ComfyUI (models/diffusion_models)."
                    return None
        elif self.comfyui_url:
            self.last_error = f"Model Diffusion Wan 2.1 ('{unet_name}') belum terpasang di ComfyUI (models/diffusion_models)."
            return None

        neg = negative_prompt or "bad anatomy, deformed, distorted, blurry, worst quality"
        seed = random.randint(1000000, 99999999)

        # Base workflow for Wan 2.1
        workflow = {
            "1": {
                "class_type": "UNETLoader",
                "inputs": {
                    "unet_name": unet_name,
                    "weight_dtype": "default"
                }
            },
            "2": {
                "class_type": "CLIPLoader",
                "inputs": {
                    "clip_name": clip_name,
                    "type": "wan"
                }
            },
            "3": {
                "class_type": "VAELoader",
                "inputs": {
                    "vae_name": "wan_2.1_vae.safetensors"
                }
            },
            "4": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": visual_prompt,
                    "clip": ["2", 0]
                }
            },
            "5": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": neg,
                    "clip": ["2", 0]
                }
            },
            "6": {
                "class_type": "WanImageToVideo",
                "inputs": {
                    "positive": ["4", 0],
                    "negative": ["5", 0],
                    "vae": ["3", 0],
                    "width": 640,
                    "height": 480,
                    "length": 25,
                    "batch_size": 1
                }
            },
            "7": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": seed,
                    "steps": 20,
                    "cfg": 6.0,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": 1.0,
                    "model": ["1", 0],
                    "positive": ["6", 0],
                    "negative": ["6", 1],
                    "latent_image": ["6", 2]
                }
            },
            "8": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["7", 0],
                    "vae": ["3", 0]
                }
            },
            "9": {
                "class_type": "CreateVideo",
                "inputs": {
                    "images": ["8", 0],
                    "fps": 16.0
                }
            },
            "10": {
                "class_type": "SaveVideo",
                "inputs": {
                    "video": ["9", 0],
                    "filename_prefix": "WaifuWan21Video",
                    "format": "auto"
                }
            }
        }

        # If base image is provided (e.g. from photo message), upload and feed as start_image
        if base_image_bytes:
            uploaded_name = self._upload_image_to_comfy(base_image_bytes, f"wan_in_{seed}.png")
            if uploaded_name:
                workflow["11"] = {
                    "class_type": "LoadImage",
                    "inputs": {"image": uploaded_name}
                }
                workflow["6"]["inputs"]["start_image"] = ["11", 0]

        return self._execute_video_workflow(workflow, output_node_id="10")

    def generate_video_animatediff(
        self,
        visual_prompt: str,
        negative_prompt: Optional[str] = None,
        base_image_bytes: Optional[bytes] = None
    ) -> Optional[bytes]:
        """Executes AnimateDiff SD 1.5 Anime video pipeline on ComfyUI with temporal motion cohesion."""
        # 1. Verify AnimateDiff loader node and motion models exist in ComfyUI
        ad_info = self._get_animatediff_loader_info()
        if not ad_info:
            self.last_error = (
                "Ekstensi AnimateDiff (ComfyUI-AnimateDiff-Evolved) atau motion module (mm_sd_v15_v2.ckpt) "
                "belum terpasang di ComfyUI. Tanpa modul animasi temporal, frame video hanya akan menghasilkan foto acak yang berkedip. "
                "Silakan unduh AnimateDiff melalui bot (/video) atau gunakan Wan 2.1 (1.3B AI Video)."
            )
            return None

        ckpts = self.get_available_checkpoints()
        chosen_ckpt = None
        for c in ckpts:
            if any(k in c.lower() for k in ["meina", "anime", "aom"]):
                chosen_ckpt = c
                break
        if not chosen_ckpt and ckpts:
            chosen_ckpt = ckpts[0]

        if not chosen_ckpt:
            self.last_error = "Checkpoint anime (AOM3 / MeinaMix) tidak ditemukan di ComfyUI."
            return None

        seed = random.randint(1000000, 99999999)
        neg = negative_prompt or "worst quality, low quality, bad anatomy, deformed eyes, extra limbs, static"

        # 2. Wire AnimateDiff Motion Module between Checkpoint and KSampler
        workflow = {
            "1": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": chosen_ckpt}
            }
        }

        if ad_info.get("mode") == "gen2":
            workflow["2"] = {
                "class_type": ad_info["load_class"],
                "inputs": {
                    "model_name": ad_info["model_name"]
                }
            }
            workflow["2b"] = {
                "class_type": ad_info["apply_class"],
                "inputs": {
                    "model": ["1", 0],
                    "motion_model": ["2", 0]
                }
            }
            sampler_model_target = ["2b", 0]
        else:
            inputs_dict = {
                "model": ["1", 0],
                "model_name": ad_info["model_name"]
            }
            if ad_info.get("beta_schedule"):
                inputs_dict["beta_schedule"] = ad_info["beta_schedule"]
            if ad_info.get("needs_context") and ad_info.get("has_uniform_context"):
                workflow["2_ctx"] = {
                    "class_type": "ADE_AnimateDiffUniformContextOptions",
                    "inputs": {
                        "context_length": 16,
                        "context_stride": 1,
                        "context_overlap": 4
                    }
                }
                inputs_dict["context_options"] = ["2_ctx", 0]

            workflow["2"] = {
                "class_type": ad_info["loader_class"],
                "inputs": inputs_dict
            }
            sampler_model_target = ["2", 0]

        workflow["3"] = {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": 512, "height": 768, "batch_size": 16}
        }
        workflow["4"] = {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": visual_prompt, "clip": ["1", 1]}
        }
        workflow["5"] = {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": neg, "clip": ["1", 1]}
        }
        workflow["6"] = {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed,
                "steps": 20,
                "cfg": 7.0,
                "sampler_name": "euler_ancestral",
                "scheduler": "karras",
                "denoise": 1.0,
                "model": sampler_model_target,
                "positive": ["4", 0],
                "negative": ["5", 0],
                "latent_image": ["3", 0]
            }
        }
        workflow["7"] = {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["6", 0], "vae": ["1", 2]}
        }
        workflow["8"] = {
            "class_type": "CreateVideo",
            "inputs": {"images": ["7", 0], "fps": 8.0}
        }
        workflow["9"] = {
            "class_type": "SaveVideo",
            "inputs": {
                "video": ["8", 0],
                "filename_prefix": "WaifuAnimateDiff",
                "format": "auto"
            }
        }

        # If base image is provided (e.g. from photo message), encode and repeat for image-to-video animation
        if base_image_bytes:
            uploaded_name = self._upload_image_to_comfy(base_image_bytes, f"anim_in_{seed}.png")
            if uploaded_name:
                workflow["10"] = {
                    "class_type": "LoadImage",
                    "inputs": {"image": uploaded_name}
                }
                workflow["11"] = {
                    "class_type": "VAEEncode",
                    "inputs": {
                        "pixels": ["10", 0],
                        "vae": ["1", 2]
                    }
                }
                workflow["12"] = {
                    "class_type": "RepeatLatentBatch",
                    "inputs": {
                        "samples": ["11", 0],
                        "amount": 16
                    }
                }
                workflow["6"]["inputs"]["latent_image"] = ["12", 0]
                workflow["6"]["inputs"]["denoise"] = 0.65

        return self._execute_video_workflow(workflow, output_node_id="9")

    def _execute_video_workflow(self, workflow: dict, output_node_id: str = "9") -> Optional[bytes]:
        """Submits video workflow to ComfyUI and polls for the resulting MP4 video binary."""
        try:
            res = requests.post(
                f"{self.comfyui_url}/prompt",
                json={"prompt": workflow, "client_id": self.client_id},
                timeout=12
            )
            if res.status_code != 200:
                logger.warning(f"ComfyUI video prompt rejected: {res.text}")
                self.last_error = format_comfy_validation_error(res)
                return None

            prompt_id = res.json().get("prompt_id")
            if not prompt_id:
                self.last_error = "ComfyUI tidak mengembalikan prompt_id untuk video."
                return None

            # Poll for video completion (up to 300 seconds for video diffusion)
            for _ in range(150):
                time.sleep(2.0)
                try:
                    h_res = requests.get(f"{self.comfyui_url}/history/{prompt_id}", timeout=6)
                except Exception:
                    continue

                if h_res.status_code == 200:
                    h_data = h_res.json()
                    if prompt_id in h_data:
                        task = h_data[prompt_id]
                        status = task.get("status", {})
                        if status.get("status_str") == "error":
                            messages = status.get("messages", [])
                            err_detail = "Node error"
                            for m in messages:
                                if isinstance(m, list) and len(m) > 1 and m[0] == "execution_error":
                                    info = m[1]
                                    err_detail = f"{info.get('node_type')}: {info.get('exception_message', '').strip()}"
                                    break
                            logger.error(f"ComfyUI video error: {status.get('messages')}")
                            self.last_error = f"ComfyUI video render error ({err_detail})"
                            return None

                        outputs = task.get("outputs", {})
                        # Search for video outputs in any returned node
                        for nid, node_out in outputs.items():
                            for media_key in ("videos", "gifs", "images"):
                                if media_key in node_out and len(node_out[media_key]) > 0:
                                    vinfo = node_out[media_key][0]
                                    fname = vinfo.get("filename")
                                    subfolder = vinfo.get("subfolder", "")
                                    mtype = vinfo.get("type", "output")

                                    view_url = f"{self.comfyui_url}/view?filename={fname}&subfolder={subfolder}&type={mtype}"
                                    vresp = requests.get(view_url, timeout=60)
                                    if vresp.status_code == 200:
                                        return vresp.content

            if not self.last_error:
                self.last_error = "Waktu render video melebihi batas (ComfyUI sibuk atau VRAM terbatas)."

        except Exception as e:
            logger.error(f"ComfyUI video workflow exception: {e}")
            self.last_error = f"Error rendering video ComfyUI: {e}"
        finally:
            self._free_comfyui_vram()

        return None
