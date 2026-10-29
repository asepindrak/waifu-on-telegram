import os
import time
import json
import uuid
import random
import io
import urllib.parse
import logging
import requests
from typing import Optional, Dict, Any, Tuple

try:
    import photo_vault
except ImportError:
    photo_vault = None

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

    def get_active_checkpoint(self) -> str:
        """Determines the active image checkpoint model currently selected/available."""
        ckpts = self.get_available_checkpoints()
        env_ckpt = os.environ.get("COMFYUI_CHECKPOINT", "").strip()
        if env_ckpt and ckpts:
            matched = [c for c in ckpts if env_ckpt.lower() in c.lower()]
            if matched:
                return matched[0]
        if ckpts:
            valid_ckpts = [c for c in ckpts if not ("basnsfw" in c.lower() and "base" in c.lower())] or ckpts
            for c in valid_ckpts:
                if "meina" in c.lower():
                    return c
            for c in valid_ckpts:
                if any(k in c.lower() for k in ["anything", "xl"]):
                    return c
            for c in valid_ckpts:
                if any(k in c.lower() for k in ["aom", "orange"]):
                    return c
            return valid_ckpts[0]
        if env_ckpt:
            return env_ckpt
        try:
            import asset_manager
            info = asset_manager.get_asset_info("anything_xl")
            if info and info.get("installed") and info.get("target_path"):
                return os.path.basename(info["target_path"])
            info = asset_manager.get_asset_info("meinamix")
            if info and info.get("installed") and info.get("target_path"):
                return os.path.basename(info["target_path"])
        except Exception:
            pass
        return "meinamix_v12Final.safetensors"

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

        # 3. Prefer Anything XL if present
        if not chosen_ckpt:
            for c in valid_ckpts:
                if any(k in c.lower() for k in ["anything", "xl"]):
                    chosen_ckpt = c
                    break

        # 4. Prefer AOM3 / OrangeMix if present
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
            for _ in range(160):  # Wait up to 240 seconds
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
                self.last_error = "ComfyUI timeout: waktu rendering melebihi 240 detik (antrean sibuk atau VRAM terbatas)."

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
        quality: Optional[str] = None,
        persona: str = "runa",
        scene: str = "",
        outfit_label: str = "",
        is_nude: bool = False,
        user_query: str = ""
    ) -> Tuple[Optional[bytes], str]:
        """
        Main entry for photo generation.
        1. Tries local ComfyUI.
        2. On success: archives photo into Photo Vault with semantic metadata.
        3. On failure / offline: searches Photo Vault for matching persona & scene (No low-quality cloud!).
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
                # Automatically save high-quality local render to Photo Vault
                if photo_vault:
                    try:
                        photo_vault.save_photo_to_vault(
                            local_img,
                            persona=persona,
                            scene=scene or user_query,
                            outfit_label=outfit_label,
                            is_nude=is_nude,
                            visual_prompt=effective_prompt,
                            user_query=user_query,
                            aspect_ratio=aspect_ratio or "3:4"
                        )
                    except Exception as e_save:
                        logger.warning(f"Failed to auto-archive photo to vault: {e_save}")
                return local_img, "ComfyUI Local"
        else:
            self.last_error = "ComfyUI URL belum dikonfigurasi (pastikan ComfyUI lokal aktif di port 8188)."

        # 2. Smart Photo Vault Retrieval (Offline Semantic Fallback)
        if photo_vault:
            try:
                matched = photo_vault.find_matching_photo(
                    persona=persona,
                    scene=scene or user_query,
                    outfit_label=outfit_label,
                    is_nude=is_nude,
                    user_query=user_query
                )
                if matched:
                    vault_img, meta = matched
                    logger.info(f"Retrieved matching photo from vault: {meta.get('filename')} (Scene: {meta.get('scene')})")
                    return vault_img, "Vault Archive (Saved Photo)"
            except Exception as e_find:
                logger.warning(f"Error querying photo vault: {e_find}")

        # Cloud fallback is intentionally disabled per user request (bad quality)
        return None, "Failed"

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
        neg = negative_prompt or "bad anatomy, deformed, distorted, blurry, worst quality"
        seed = random.randint(1000000, 99999999)

        # Base workflow for Wan 2.1
        workflow = {
            "1": {
                "class_type": "UNETLoader",
                "inputs": {
                    "unet_name": "wan2.1_t2v_1.3B_bf16.safetensors",
                    "weight_dtype": "default"
                }
            },
            "2": {
                "class_type": "CLIPLoader",
                "inputs": {
                    "clip_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors",
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
        """Executes AnimateDiff SD 1.5 Anime video pipeline on ComfyUI."""
        ckpts = self.get_available_checkpoints()
        chosen_ckpt = None
        for c in ckpts:
            if any(k in c.lower() for k in ["meina", "anime", "aom"]):
                chosen_ckpt = c
                break
        if not chosen_ckpt and ckpts:
            chosen_ckpt = ckpts[0]

        if not chosen_ckpt:
            self.last_error = "Checkpoint anime MeinaMix tidak ditemukan di ComfyUI."
            return None

        seed = random.randint(1000000, 99999999)
        neg = negative_prompt or "worst quality, low quality, bad anatomy, deformed eyes"

        workflow = {
            "1": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": chosen_ckpt}
            },
            "2": {
                "class_type": "EmptyLatentImage",
                "inputs": {"width": 512, "height": 768, "batch_size": 16}
            },
            "3": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": visual_prompt, "clip": ["1", 1]}
            },
            "4": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": neg, "clip": ["1", 1]}
            },
            "5": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": seed,
                    "steps": 20,
                    "cfg": 7.0,
                    "sampler_name": "dpmpp_2m",
                    "scheduler": "karras",
                    "denoise": 1.0,
                    "model": ["1", 0],
                    "positive": ["3", 0],
                    "negative": ["4", 0],
                    "latent_image": ["2", 0]
                }
            },
            "6": {
                "class_type": "VAEDecode",
                "inputs": {"samples": ["5", 0], "vae": ["1", 2]}
            },
            "7": {
                "class_type": "CreateVideo",
                "inputs": {"images": ["6", 0], "fps": 12.0}
            },
            "8": {
                "class_type": "SaveVideo",
                "inputs": {
                    "video": ["7", 0],
                    "filename_prefix": "WaifuAnimateDiff",
                    "format": "auto"
                }
            }
        }

        return self._execute_video_workflow(workflow, output_node_id="8")

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
                self.last_error = f"ComfyUI menolak prompt video: {res.text[:120]}"
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

        return None
