"""Background job service with thread-based execution, progress tracking, and HMAC-signed webhook callbacks."""
import datetime
import hashlib
import hmac
import json
import threading
import time
import uuid
from typing import Dict, Any, Optional
import httpx

from app.config import get_settings, Settings
from app.core.models import Project
from app.api.errors import JobNotFoundError
from app.db.database import get_db, DataStore


class JobService:
    def __init__(
        self,
        db: Optional[DataStore] = None,
        settings: Optional[Settings] = None
    ):
        self.settings = settings or get_settings()
        self.db = db or get_db()

    def create_job(self, job_type: str, project_id: str, params: Optional[Dict[str, Any]] = None) -> str:
        """Create a job with status 'queued' and return job_id."""
        job_id = str(uuid.uuid4())
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        job = {
            "id": job_id,
            "type": job_type,
            "project_id": str(project_id),
            "status": "queued",  # queued, running, succeeded, failed
            "progress": 0,
            "params": params or {},
            "result": None,
            "result_url": None,
            "error": None,
            "created_at": now,
            "updated_at": now
        }
        self.db.save_job(job_id, job)
        return job_id

    def update_job(
        self,
        job_id: str,
        status: str,
        progress: int,
        result: Optional[Dict[str, Any]] = None,
        result_url: Optional[str] = None,
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update job status, progress, and result."""
        job = self.db.get_job(job_id)
        if not job:
            raise JobNotFoundError(f"Job '{job_id}' not found")

        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        job["status"] = status
        job["progress"] = max(0, min(100, progress))
        job["updated_at"] = now

        if result is not None:
            job["result"] = result
        if result_url is not None:
            job["result_url"] = result_url
        if error is not None:
            job["error"] = error

        self.db.save_job(job_id, job)

        # If job finished and callback_url is defined, trigger webhook callback
        if status in ("succeeded", "failed") and job["params"].get("callback_url"):
            self._send_callback(job)

        return job

    def get_job(self, job_id: str) -> Dict[str, Any]:
        """Retrieve job status and metadata."""
        job = self.db.get_job(job_id)
        if not job:
            raise JobNotFoundError(f"Job '{job_id}' not found")
        return job

    def _sign_payload(self, payload: Dict[str, Any], secret: str) -> str:
        """Generate HMAC-SHA256 signature for the callback payload."""
        payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
        signature = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
        return signature

    def _send_callback(self, job: Dict[str, Any]) -> None:
        """Send HMAC-signed webhook callback asynchronously in a daemon thread."""
        callback_url = job["params"].get("callback_url")
        if not callback_url:
            return

        def _do_post():
            secret = self.settings.CALLBACK_SECRET
            signature = self._sign_payload(job, secret)
            headers = {
                "Content-Type": "application/json",
                "X-IncuBrix-Signature": f"sha256={signature}"
            }
            try:
                with httpx.Client(timeout=10.0) as client:
                    client.post(callback_url, json=job, headers=headers)
            except Exception:
                pass

        threading.Thread(target=_do_post, daemon=True).start()

    def run_render_job(self, job_id: str, project: Project) -> None:
        """Execute render job in a background thread with progress simulation and output validation."""
        def _execute():
            from app.services.render_service import RenderService
            try:
                self.update_job(job_id, status="running", progress=10)
                render_service = RenderService(settings=self.settings)

                # Simulated progress steps during render
                time.sleep(0.05)
                self.update_job(job_id, status="running", progress=35)

                result = render_service.render(project)

                self.update_job(job_id, status="running", progress=85)
                time.sleep(0.05)

                result_url = f"/api/v1/jobs/{job_id}/download"
                self.update_job(
                    job_id,
                    status="succeeded",
                    progress=100,
                    result=result,
                    result_url=result_url
                )
            except Exception as e:
                self.update_job(
                    job_id,
                    status="failed",
                    progress=100,
                    error=str(e)
                )

        worker_thread = threading.Thread(target=_execute, daemon=True)
        worker_thread.start()

    def run_transcription_job(self, job_id: str, project_id: str, file_path: str) -> None:
        """Execute transcription job in background thread."""
        def _execute():
            import asyncio
            from app.adapters.transcription.mock_adapter import MockTranscriptionAdapter
            from app.adapters.transcription.whisper_adapter import WhisperTranscriptionAdapter
            try:
                self.update_job(job_id, status="running", progress=15)
                provider = self.settings.TRANSCRIPTION_PROVIDER.lower()
                if provider == "whisper":
                    adapter = WhisperTranscriptionAdapter(self.settings.WHISPER_MODEL_SIZE)
                else:
                    adapter = MockTranscriptionAdapter()

                self.update_job(job_id, status="running", progress=45)

                # Run async transcribe method synchronously in background worker
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                transcript = loop.run_until_complete(adapter.transcribe(file_path))
                loop.close()

                self.update_job(job_id, status="running", progress=80)

                # Update project with transcript
                project = self.db.get_project(project_id)
                if project:
                    transcript.source_media_id = str(project.source_media.id)
                    project.transcript = transcript
                    self.db.save_project(project)

                self.update_job(
                    job_id,
                    status="succeeded",
                    progress=100,
                    result={"transcript_words": len(transcript.words), "speakers": transcript.speakers}
                )
            except Exception as e:
                self.update_job(
                    job_id,
                    status="failed",
                    progress=100,
                    error=str(e)
                )

        worker_thread = threading.Thread(target=_execute, daemon=True)
        worker_thread.start()
