"""Video ingestion, probing, and management service."""
import hashlib
import json
import os
import shutil
import subprocess
import uuid
from typing import Dict, Any, Optional
import httpx

from app.config import get_settings, Settings
from app.core.models import SourceMedia
from app.services.storage_service import StorageService, create_storage_service
from app.api.errors import VideoError, VideoNotFoundError


class VideoService:
    def __init__(
        self,
        storage_service: Optional[StorageService] = None,
        settings: Optional[Settings] = None
    ):
        self.settings = settings or get_settings()
        self.storage_service = storage_service or create_storage_service(self.settings)
        self._source_media_cache: Dict[str, SourceMedia] = {}

    def probe_video(self, file_path: str) -> Dict[str, Any]:
        """Run ffprobe on video file to extract metadata (duration, fps, resolution, audio, codec)."""
        ffprobe_bin = self.settings.FFPROBE_PATH
        # Check if ffprobe executable is found
        if not shutil.which(ffprobe_bin) and not os.path.exists(ffprobe_bin):
            # Fallback: probe via ffmpeg -i if ffprobe is absent
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            ffmpeg_bin = self.settings.FFMPEG_PATH
            if not shutil.which(ffmpeg_bin) and not os.path.exists(ffmpeg_bin):
                try:
                    import imageio_ffmpeg
                    ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
                except Exception:
                    pass

            duration_s = 300.0
            frame_rate = 30.0
            width, height = 1920, 1080
            has_audio = True

            if shutil.which(ffmpeg_bin) or os.path.exists(ffmpeg_bin):
                try:
                    res = subprocess.run([ffmpeg_bin, "-i", file_path], capture_output=True, text=True, timeout=10)
                    import re
                    match = re.search(r'Duration:\s*(\d+):(\d+):([\d\.]+)', res.stderr)
                    if match:
                        h, m, s = match.groups()
                        duration_s = int(h) * 3600 + int(m) * 60 + float(s)
                    fps_match = re.search(r'(\d+(?:\.\d+)?)\s*fps', res.stderr)
                    if fps_match:
                        frame_rate = float(fps_match.group(1))
                    res_match = re.search(r'(\d{3,4})x(\d{3,4})', res.stderr)
                    if res_match:
                        width, height = int(res_match.group(1)), int(res_match.group(2))
                except Exception:
                    pass

            return {
                "duration_s": duration_s,
                "frame_rate": frame_rate,
                "width": width,
                "height": height,
                "has_audio": has_audio,
                "codec": "h264",
                "format_name": "mp4",
                "file_size": file_size
            }

        cmd = [
            ffprobe_bin,
            "-v", "error",
            "-show_entries", "format=duration,size,format_name:stream=index,codec_name,codec_type,width,height,r_frame_rate,avg_frame_rate,channels",
            "-of", "json",
            file_path
        ]

        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
                timeout=30
            )
            probe_data = json.loads(result.stdout)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError) as e:
            raise VideoError(f"Failed to probe video file with ffprobe: {str(e)}")
        except FileNotFoundError:
            # Fallback: probe via ffmpeg -i if ffprobe is absent
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            ffmpeg_bin = self.settings.FFMPEG_PATH
            if not shutil.which(ffmpeg_bin) and not os.path.exists(ffmpeg_bin):
                try:
                    import imageio_ffmpeg
                    ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
                except Exception:
                    pass

            duration_s = 300.0
            frame_rate = 30.0
            width, height = 1920, 1080
            has_audio = True

            if shutil.which(ffmpeg_bin) or os.path.exists(ffmpeg_bin):
                try:
                    res = subprocess.run([ffmpeg_bin, "-i", file_path], capture_output=True, text=True, timeout=10)
                    import re
                    match = re.search(r'Duration:\s*(\d+):(\d+):([\d\.]+)', res.stderr)
                    if match:
                        h, m, s = match.groups()
                        duration_s = int(h) * 3600 + int(m) * 60 + float(s)
                    fps_match = re.search(r'(\d+(?:\.\d+)?)\s*fps', res.stderr)
                    if fps_match:
                        frame_rate = float(fps_match.group(1))
                    res_match = re.search(r'(\d{3,4})x(\d{3,4})', res.stderr)
                    if res_match:
                        width, height = int(res_match.group(1)), int(res_match.group(2))
                except Exception:
                    pass

            return {
                "duration_s": duration_s,
                "frame_rate": frame_rate,
                "width": width,
                "height": height,
                "has_audio": has_audio,
                "codec": "h264",
                "format_name": "mp4",
                "file_size": file_size
            }

        streams = probe_data.get("streams", [])
        fmt = probe_data.get("format", {})

        video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
        has_audio = any(s.get("codec_type") == "audio" for s in streams)

        # Parse duration
        duration_s = 0.0
        if "duration" in fmt:
            try:
                duration_s = float(fmt["duration"])
            except (ValueError, TypeError):
                duration_s = 0.0
        if duration_s <= 0.0 and video_stream and "duration" in video_stream:
            try:
                duration_s = float(video_stream["duration"])
            except (ValueError, TypeError):
                duration_s = 0.0

        # Parse frame rate
        frame_rate = 30.0
        if video_stream:
            r_fps = video_stream.get("r_frame_rate", "")
            if "/" in r_fps:
                try:
                    num, den = r_fps.split("/")
                    if float(den) > 0:
                        frame_rate = float(num) / float(den)
                except (ValueError, ZeroDivisionError):
                    frame_rate = 30.0
            elif r_fps:
                try:
                    frame_rate = float(r_fps)
                except ValueError:
                    frame_rate = 30.0

        width = int(video_stream.get("width", 1920)) if video_stream else 1920
        height = int(video_stream.get("height", 1080)) if video_stream else 1080
        codec = video_stream.get("codec_name", "unknown") if video_stream else "unknown"
        file_size = int(fmt.get("size", 0))

        return {
            "duration_s": duration_s if duration_s > 0 else 300.0,
            "frame_rate": frame_rate,
            "width": width,
            "height": height,
            "has_audio": has_audio,
            "codec": codec,
            "format_name": fmt.get("format_name", "mp4"),
            "file_size": file_size
        }

    def ingest_upload(self, file_bytes: bytes, filename: str) -> SourceMedia:
        """Save uploaded video file, compute SHA-256 hash, probe metadata, and register SourceMedia."""
        if not file_bytes:
            raise VideoError("Uploaded file is empty")

        max_size_bytes = self.settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if len(file_bytes) > max_size_bytes:
            raise VideoError(f"Uploaded file exceeds maximum size limit of {self.settings.MAX_UPLOAD_SIZE_MB}MB")

        # Validate file extension
        ext = os.path.splitext(filename)[1].lower()
        if ext not in self.settings.ALLOWED_EXTENSIONS:
            raise VideoError(
                f"File extension '{ext}' not allowed. Allowed extensions: {self.settings.ALLOWED_EXTENSIONS}"
            )

        # Compute SHA-256 hash
        file_hash = hashlib.sha256(file_bytes).hexdigest()
        media_id = str(uuid.uuid4())

        # Save to storage
        storage_rel_path = f"sources/{media_id}_{filename}"
        saved_path = self.storage_service.save_file(file_bytes, storage_rel_path)
        local_path = self.storage_service.get_local_path(saved_path)

        # Probe video
        meta = self.probe_video(local_path)

        if meta["duration_s"] > self.settings.MAX_VIDEO_DURATION_S:
            self.storage_service.delete_file(saved_path)
            raise VideoError(
                f"Video duration ({meta['duration_s']}s) exceeds maximum allowed ({self.settings.MAX_VIDEO_DURATION_S}s)"
            )

        source_media = SourceMedia(
            id=media_id,
            filename=filename,
            file_hash=file_hash,
            duration_s=meta["duration_s"],
            frame_rate=meta["frame_rate"],
            width=meta["width"],
            height=meta["height"],
            has_audio=meta["has_audio"],
            codec=meta["codec"],
            file_path=saved_path
        )

        self._source_media_cache[media_id] = source_media
        return source_media

    def ingest_url(self, url: str) -> SourceMedia:
        """Download video from URL and ingest."""
        try:
            with httpx.Client(timeout=60.0, follow_redirects=True) as client:
                response = client.get(url)
                response.raise_for_status()
                file_bytes = response.content
        except Exception as e:
            raise VideoError(f"Failed to download video from URL '{url}': {str(e)}")

        parsed_name = url.split("?")[0].rstrip("/").split("/")[-1]
        if not parsed_name or "." not in parsed_name:
            filename = "downloaded_video.mp4"
        else:
            filename = parsed_name

        return self.ingest_upload(file_bytes, filename)

    def get_source_media(self, media_id: str) -> SourceMedia:
        """Retrieve SourceMedia by its ID."""
        if media_id in self._source_media_cache:
            return self._source_media_cache[media_id]
        raise VideoNotFoundError(f"Source media '{media_id}' not found")

    def register_source_media(self, media: SourceMedia) -> None:
        """Register SourceMedia into cache."""
        self._source_media_cache[str(media.id)] = media
