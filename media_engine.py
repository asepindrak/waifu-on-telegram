import os
import time
import json
import uuid
import random
import urllib.parse
import logging
import requests
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)

class MediaEngine:
    """Generates images and videos via local ComfyUI with cloud fallback."""

    def __init__(self, comfyui_url: str = "http://127.0.0.1:8188", allow_cloud_fallback: bool = True):
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
                    "checkpoints": ckpts
                }
        except Exception:
            pass

        return {
            "online": False,
            "backend": "Cloud Fallback (Pollinations)" if self.allow_cloud_fallback else "Disabled",
            "device": "Remote CPU/GPU"
        }

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
                "9:16": (512, 910),  # Smartphone story/wallpaper
                "16:9": (910, 512),  # Widescreen
                "1:1": (512, 512)    # Square avatar
            }
            return table.get(ar, (576, 768))

    @staticmethod
    def get_quality_params(quality: str = "high") -> Tuple[int, float]:
        """Returns (steps, cfg) based on desired quality preset."""
        q = quality.lower().strip()
        if q in ("ultra", "best", "very_high"):
            return 32, 8.0
        elif q in ("fast", "low", "standard"):
            return 20, 7.0
        else: # high (MeinaMix sweet spot)
            return 28, 7.5

    def generate_image_comfyui(
        self,
        prompt: str,
        negative_prompt: str = "(worst quality, low quality:1.4), bad anatomy, deformed eyes, extra limbs, bad hands, missing fingers, blurry",
        aspect_ratio: Optional[str] = None,
        quality: Optional[str] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        steps: Optional[int] = None,
        cfg: Optional[float] = None
    ) -> Optional[bytes]:
        """Runs standard Text-to-Image workflow on local ComfyUI with optimal anime settings."""
        ckpts = self.get_available_checkpoints()
        if not ckpts:
            logger.warning("No ComfyUI checkpoints found for T2I.")
            return None

        # Smart Checkpoint Selection:
        # 1. Environment variable if user configured specific model
        env_ckpt = os.environ.get("COMFYUI_CHECKPOINT", "").strip()
        chosen_ckpt = None
        if env_ckpt:
            matched = [c for c in ckpts if env_ckpt.lower() in c.lower()]
            if matched:
                chosen_ckpt = matched[0]

        # 2. Prefer MeinaMix if present in folder
        if not chosen_ckpt:
            for c in ckpts:
                if "meina" in c.lower():
                    chosen_ckpt = c
                    break

        # 3. Prefer AOM3 / OrangeMix if present
        if not chosen_ckpt:
            for c in ckpts:
                if any(k in c.lower() for k in ["aom", "orange"]):
                    chosen_ckpt = c
                    break

        # 4. Fallback to first available checkpoint
        if not chosen_ckpt:
            chosen_ckpt = ckpts[0]

        is_sdxl = any(k in chosen_ckpt.lower() for k in ["xl", "sdxl", "pony", "illustrious"])

        # Determine Aspect Ratio & Dimensions
        ar = aspect_ratio or os.environ.get("IMAGE_ASPECT_RATIO", "3:4")
        if width is None or height is None:
            width, height = self.get_dimensions(ar, is_sdxl=is_sdxl)

        # Determine Quality Parameters (steps & cfg)
        qual = quality or os.environ.get("IMAGE_QUALITY", "high")
        def_steps, def_cfg = self.get_quality_params(qual)
        if steps is None:
            steps = def_steps
        if cfg is None:
            cfg = def_cfg

        # Optimal sampler: DPM++ 2M Karras for MeinaMix / Anime SD 1.5
        sampler_name = "euler_ancestral" if is_sdxl else "dpmpp_2m"
        scheduler_name = "normal" if is_sdxl else "karras"

        seed = random.randint(10000000, 99999999)

        # Detect optional external VAE (e.g. orangemix.vae.pt)
        available_vaes = self.get_available_vaes()
        chosen_vae = None
        for v in available_vaes:
            if any(k in v.lower() for k in ["orangemix", "anime", "vae-ft", "kl-f8"]):
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
                return None

            prompt_id = res.json().get("prompt_id")
            if not prompt_id:
                return None

            # Poll history for completion
            for _ in range(120):  # Wait up to 120 seconds
                time.sleep(1.5)
                h_res = requests.get(f"{self.comfyui_url}/history/{prompt_id}", timeout=5)
                if h_res.status_code == 200:
                    h_data = h_res.json()
                    if prompt_id in h_data:
                        task = h_data[prompt_id]
                        status = task.get("status", {})
                        if status.get("status_str") == "error":
                            logger.error(f"ComfyUI node execution error: {status.get('messages')}")
                            return None

                        outputs = task.get("outputs", {})
                        if "9" in outputs and "images" in outputs["9"]:
                            img_info = outputs["9"]["images"][0]
                            img_name = img_info["filename"]
                            subfolder = img_info.get("subfolder", "")
                            img_type = img_info.get("type", "output")

                            # Fetch image binary
                            view_url = f"{self.comfyui_url}/view?filename={img_name}&subfolder={subfolder}&type={img_type}"
                            img_resp = requests.get(view_url, timeout=30)
                            if img_resp.status_code == 200:
                                return img_resp.content

        except Exception as e:
            logger.error(f"ComfyUI generation error: {e}")

        return None

    def generate_image_cloud_fallback(
        self,
        prompt: str,
        width: int = 768,
        height: int = 1024
    ) -> Optional[bytes]:
        """Free, ultra-fast cloud fallback via Pollinations AI (0 local VRAM required)."""
        clean_p = urllib.parse.quote(prompt)
        seed = random.randint(1000, 999999)
        url = f"https://image.pollinations.ai/prompt/{clean_p}?width={width}&height={height}&seed={seed}&nologo=true&enhance=true"

        try:
            r = requests.get(url, timeout=40)
            if r.status_code == 200 and r.content:
                return r.content
        except Exception as e:
            logger.error(f"Cloud image fallback error: {e}")

        return None

    def generate_photo(
        self,
        visual_prompt: str,
        negative_prompt: Optional[str] = None,
        aspect_ratio: Optional[str] = None,
        quality: Optional[str] = None
    ) -> Tuple[Optional[bytes], str]:
        """
        Main entry for photo generation.
        Tries local ComfyUI first; if offline or fails, falls back to cloud.
        Returns: (image_bytes, source_label)
        """
        # 1. Try local ComfyUI
        if self.comfyui_url:
            local_img = self.generate_image_comfyui(
                visual_prompt,
                negative_prompt=negative_prompt or "(worst quality, low quality:1.4), bad anatomy, deformed eyes, extra limbs, bad hands, missing fingers, blurry",
                aspect_ratio=aspect_ratio,
                quality=quality
            )
            if local_img:
                return local_img, "ComfyUI Local"

        # 2. Cloud Fallback
        if self.allow_cloud_fallback:
            w, h = self.get_dimensions(aspect_ratio or "3:4", is_sdxl=False)
            cloud_img = self.generate_image_cloud_fallback(visual_prompt, width=w, height=h)
            if cloud_img:
                return cloud_img, "Cloud Engine (Free GPU)"

        return None, "Failed"
