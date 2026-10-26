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
                    "checkpoints": ckpts
                }
        except Exception:
            pass

        return {
            "online": False,
            "backend": "Cloud Fallback (Pollinations)" if self.allow_cloud_fallback else "ComfyUI Offline",
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

        # Filter out incomplete / UNet-only checkpoints that lack CLIP or VAE (e.g. BASNSFW...baseV10)
        valid_ckpts = [c for c in ckpts if not ("basnsfw" in c.lower() and "base" in c.lower())]
        if not valid_ckpts:
            valid_ckpts = ckpts

        # 2. Prefer MeinaMix if present in folder (SD 1.5 anime model with CLIP & VAE, handles SFW & NSFW)
        if not chosen_ckpt:
            for c in valid_ckpts:
                if "meina" in c.lower():
                    chosen_ckpt = c
                    break

        # 3. Prefer AOM3 / OrangeMix if present
        if not chosen_ckpt:
            for c in valid_ckpts:
                if any(k in c.lower() for k in ["aom", "orange"]):
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
                self.last_error = f"ComfyUI menolak prompt (HTTP {res.status_code}): {res.text[:120]}"
                return None

            prompt_id = res.json().get("prompt_id")
            if not prompt_id:
                self.last_error = "ComfyUI tidak mengembalikan prompt_id."
                return None

            # Poll history for completion
            for _ in range(120):  # Wait up to 120 seconds
                time.sleep(1.5)
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
                self.last_error = "ComfyUI timeout: waktu rendering melebihi 120 detik (antrean sibuk atau VRAM terbatas)."

        except requests.exceptions.ConnectionError:
            self.last_error = f"Tidak dapat terhubung ke ComfyUI di {self.comfyui_url}. Pastikan ComfyUI sudah aktif."
            logger.error(self.last_error)
        except Exception as e:
            logger.error(f"ComfyUI generation error: {e}")
            self.last_error = f"Error komunikasi ComfyUI: {e}"

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
        visual_prompt: str = "",
        prompt: Optional[str] = None,
        negative_prompt: Optional[str] = None,
        aspect_ratio: Optional[str] = None,
        quality: Optional[str] = None
    ) -> Tuple[Optional[bytes], str]:
        """
        Main entry for photo generation.
        Tries local ComfyUI first; if offline or fails, returns (None, 'Failed').
        Cloud fallback is disabled unless explicitly enabled.
        Returns: (image_bytes, source_label)
        """
        self.last_error = None
        effective_prompt = prompt or visual_prompt

        # 1. Try local ComfyUI
        if self.comfyui_url:
            local_img = self.generate_image_comfyui(
                effective_prompt,
                negative_prompt=negative_prompt or "(worst quality, low quality:1.4), bad anatomy, deformed eyes, extra limbs, bad hands, missing fingers, blurry",
                aspect_ratio=aspect_ratio,
                quality=quality
            )
            if local_img:
                return local_img, "ComfyUI Local"
        else:
            self.last_error = "ComfyUI URL belum dikonfigurasi (pastikan ComfyUI lokal aktif)."

        # 2. Cloud Fallback (Disabled by default)
        if self.allow_cloud_fallback:
            w, h = self.get_dimensions(aspect_ratio or "3:4", is_sdxl=False)
            cloud_img = self.generate_image_cloud_fallback(effective_prompt, width=w, height=h)
            if cloud_img:
                return cloud_img, "Cloud Engine (Free GPU)"

        return None, "Failed"

    def generate_video(
        self,
        visual_prompt: str,
        negative_prompt: Optional[str] = None,
        aspect_ratio: Optional[str] = None,
        quality: Optional[str] = None,
        duration: float = 3.0,
        fps: int = 24
    ) -> Tuple[Optional[bytes], str]:
        """
        Generates smooth dynamic video animation clip (H.264 MP4) featuring the waifu.
        Renders character visual first, then constructs cinematic parallax camera motion,
        breathing oscillation, and ambient sparkling particle overlay.
        Returns: (video_bytes, source_label)
        """
        import io
        import math
        import tempfile
        from PIL import Image, ImageDraw
        try:
            import imageio
            import numpy as np
        except ImportError:
            logger.error("imageio not installed. Cannot render video.")
            return None, "Failed (Missing imageio)"

        # 1. Generate base character frame with full visual prompt
        img_bytes, source = self.generate_photo(
            visual_prompt=visual_prompt,
            negative_prompt=negative_prompt,
            aspect_ratio=aspect_ratio or "3:4",
            quality=quality
        )
        if not img_bytes:
            return None, "Failed (Photo Generation)"

        try:
            base_image = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            w, h = base_image.size

            # Ensure even dimensions for H.264 libx264 compatibility
            if w % 2 != 0:
                w -= 1
            if h % 2 != 0:
                h -= 1
            if (w, h) != base_image.size:
                base_image = base_image.crop((0, 0, w, h))

            total_frames = int(duration * fps)

            # Generate ambient floating particle seeds
            particles = [
                {
                    "x": random.uniform(20, w - 20),
                    "y": random.uniform(20, h - 20),
                    "r": random.uniform(2.0, 5.0),
                    "speed_y": random.uniform(-0.8, -1.8),
                    "drift_x": random.uniform(-0.5, 0.5),
                    "color": random.choice([
                        (255, 230, 240, 160),  # Pink cherry sparkle
                        (255, 255, 220, 150),  # Golden sunshine dust
                        (220, 240, 255, 140)   # Celestial blue sparkle
                    ])
                }
                for _ in range(16)
            ]

            # Temporary MP4 file
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_file:
                tmp_path = tmp_file.name

            writer = imageio.get_writer(
                tmp_path,
                fps=fps,
                codec="libx264",
                pixelformat="yuv420p",
                quality=8
            )

            for i in range(total_frames):
                # Smooth cosine normalized time (0 to 2*pi for seamless loop)
                t = (i / total_frames) * 2 * math.pi

                # Subtle smooth zoom: 1.0 to 1.045
                zoom = 1.0 + 0.045 * ((1 - math.cos(t)) / 2)

                # Gentle vertical breathing motion: -3 to +3 pixels
                y_shift = int(3.5 * math.sin(t))

                # Crop zoom
                crop_w = int(w / zoom)
                crop_h = int(h / zoom)
                crop_left = (w - crop_w) // 2
                crop_top = max(0, min(h - crop_h, (h - crop_h) // 2 + y_shift))

                frame_img = base_image.crop((crop_left, crop_top, crop_left + crop_w, crop_top + crop_h))
                frame_img = frame_img.resize((w, h), Image.Resampling.BILINEAR)

                # Overlay soft glowing particles
                overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
                draw = ImageDraw.Draw(overlay)

                for p in particles:
                    px = (p["x"] + p["drift_x"] * i) % w
                    py = (p["y"] + p["speed_y"] * i) % h
                    pr = p["r"] * (0.8 + 0.3 * math.sin(t + px))
                    rgba = p["color"]
                    draw.ellipse([px - pr, py - pr, px + pr, py + pr], fill=rgba)

                frame_rgba = frame_img.convert("RGBA")
                frame_combined = Image.alpha_composite(frame_rgba, overlay).convert("RGB")

                writer.append_data(np.array(frame_combined))

            writer.close()

            with open(tmp_path, "rb") as f:
                video_bytes = f.read()

            try:
                os.remove(tmp_path)
            except Exception:
                pass

            return video_bytes, f"{source} (Motion Rendered)"

        except Exception as e:
            logger.error(f"Error rendering video animation: {e}")
            return None, "Failed (Video Render)"
