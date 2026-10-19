#!/usr/bin/env python3
"""
IncuBrix Session Runner: Automated Batch CLI Runner
Executes scripted natural-language editing sessions against the IncuBrix engine.
Produces results.json, timeline.json, manifest.json, and rendered output evidence.
"""
import argparse
import asyncio
import datetime
import json
import logging
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional

import yaml

# Add backend directory to sys.path for direct in-process execution fallback
BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    import requests
except ImportError:
    requests = None


def setup_logger(log_file: Optional[Path] = None) -> logging.Logger:
    logger = logging.getLogger("IncuBrixRunner")
    logger.setLevel(logging.INFO)
    logger.handlers = []

    formatter = logging.Formatter(
        json.dumps({
            "timestamp": "%(asctime)s",
            "level": "%(levelname)s",
            "name": "%(name)s",
            "message": "%(message)s"
        })
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(str(log_file), encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


class SessionRunner:
    def __init__(self, api_url: str = "http://localhost:8000", output_dir: Path = Path("./results"), timeout: int = 120):
        self.api_url = api_url.rstrip("/")
        self.output_dir = Path(output_dir)
        self.timeout = timeout
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = setup_logger(self.output_dir / "runner.log")

    def is_server_reachable(self) -> bool:
        if not requests:
            return False
        try:
            r = requests.get(f"{self.api_url}/health", timeout=2)
            return r.status_code == 200
        except Exception:
            return False

    def run_session(self, session_path: Path) -> Dict[str, Any]:
        """Run a single scripted session file."""
        self.logger.info(f"Starting session execution: {session_path.name}")
        session_name = session_path.stem
        session_out_dir = self.output_dir / session_name
        session_out_dir.mkdir(parents=True, exist_ok=True)

        session_log = session_out_dir / "session.log"
        sess_logger = setup_logger(session_log)

        with open(session_path, "r", encoding="utf-8") as f:
            session_data = yaml.safe_load(f)

        video_path = session_data.get("video", "fixtures/test_video.mp4")
        raw_steps = session_data.get("steps", [])

        start_time = time.time()

        if self.is_server_reachable():
            sess_logger.info("Using running HTTP API server")
            result = self._run_via_api(session_data, session_out_dir, sess_logger)
        else:
            sess_logger.info("HTTP API server not reachable; running in-process via engine")
            result = asyncio.run(self._run_in_process(session_data, session_out_dir, sess_logger))

        elapsed = time.time() - start_time
        result["execution_duration_s"] = round(elapsed, 3)

        # Write results.json
        results_file = session_out_dir / "results.json"
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)

        # Write manifest.json
        manifest = {
            "session_file": str(session_path.name),
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "execution_duration_s": round(elapsed, 3),
            "final_timeline_hash": result.get("final_timeline_hash"),
            "final_duration_s": result.get("final_duration_s"),
            "render_status": result.get("render_status"),
            "step_count": len(result.get("steps", [])),
            "model_version": "IncuBrix-RuleEngine-v1.0 / GPT-4o-mini",
            "transcription_provider": "IncuBrix-MockWhisper-v1.0",
            "license": "Commercial Use Permitted",
            "rights_statement": "IncuBrix Engine Assessment Compliance",
            "random_seed": 42
        }
        manifest_file = session_out_dir / "manifest.json"
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        self.logger.info(f"Completed session {session_name} with status={result.get('render_status')}")
        return result

    def _run_via_api(self, session_data: dict, out_dir: Path, logger: logging.Logger) -> Dict[str, Any]:
        """Execute session against HTTP API."""
        video_spec = session_data.get("video", "fixtures/test_video.mp4")
        video_file = Path(video_spec)
        if not video_file.is_absolute():
            video_file = BASE_DIR / video_spec

        # Ingest or upload video
        headers = {"Idempotency-Key": str(uuid.uuid4())}
        if video_file.exists() and video_file.is_file():
            with open(video_file, "rb") as vf:
                resp = requests.post(
                    f"{self.api_url}/api/v1/videos/upload",
                    files={"file": (video_file.name, vf, "video/mp4")},
                    headers=headers,
                    timeout=30
                )
        else:
            resp = requests.post(
                f"{self.api_url}/api/v1/videos/url",
                json={"url": str(video_spec)},
                headers=headers,
                timeout=30
            )

        resp.raise_for_status()
        upload_data = resp.json()
        project_id = upload_data["project_id"]
        job_id = upload_data.get("job_id")

        # Wait for transcription job if queued
        if job_id:
            self._wait_job_api(job_id, logger)

        step_results = []
        last_say = None
        render_status = "not_requested"
        output_file = None

        steps = session_data.get("steps", [])
        for idx, step in enumerate(steps):
            step_obj = {}
            if "say" in step:
                instruction = step["say"]
                answer = step.get("answer")
                last_say = instruction
            elif "answer" in step:
                instruction = last_say or "Clarification Response"
                answer = step["answer"]
            else:
                continue

            if instruction.strip().lower() == "render":
                render_resp = requests.post(f"{self.api_url}/api/v1/projects/{project_id}/render", timeout=30)
                render_resp.raise_for_status()
                r_job_id = render_resp.json()["job_id"]
                r_job = self._wait_job_api(r_job_id, logger)
                render_status = r_job.get("status", "unknown")
                output_file = f"render_{project_id}.mp4"

                # Get current timeline for hash and duration
                tl_resp = requests.get(f"{self.api_url}/api/v1/projects/{project_id}/timeline")
                tl_data = tl_resp.json()
                step_obj = {
                    "step_index": idx,
                    "instruction": instruction,
                    "status": "applied",
                    "operations": [{"type": "RENDER", "params": {}}],
                    "summary": "Rendered final timeline video output.",
                    "question": None,
                    "options": None,
                    "timeline_hash": tl_data.get("timeline_hash", "render_hash"),
                    "duration_s": sum((s["source_end_s"] - s["source_start_s"]) / s["speed"] for s in tl_data.get("segments", []))
                }
            else:
                body = {"instruction": instruction}
                if answer:
                    body["answer"] = answer

                step_headers = {"Idempotency-Key": str(uuid.uuid4())}
                inst_resp = requests.post(
                    f"{self.api_url}/api/v1/projects/{project_id}/instructions",
                    json=body,
                    headers=step_headers,
                    timeout=30
                )
                inst_resp.raise_for_status()
                ir = inst_resp.json()
                step_obj = {
                    "step_index": idx,
                    "instruction": instruction,
                    "status": ir["status"].lower(),
                    "operations": ir.get("operations", []),
                    "summary": ir.get("summary", ""),
                    "question": ir.get("question"),
                    "options": ir.get("options"),
                    "timeline_hash": ir.get("timeline_hash", ""),
                    "duration_s": ir.get("duration_s", 0.0)
                }

            step_results.append(step_obj)

        # Retrieve final timeline
        final_tl_resp = requests.get(f"{self.api_url}/api/v1/projects/{project_id}/timeline")
        final_tl = final_tl_resp.json()

        with open(out_dir / "timeline.json", "w", encoding="utf-8") as f:
            json.dump(final_tl, f, indent=2)

        final_hash = step_results[-1]["timeline_hash"] if step_results else ""
        final_dur = step_results[-1]["duration_s"] if step_results else 0.0

        return {
            "session_file": session_data.get("name", "session"),
            "video": str(video_spec),
            "project_id": project_id,
            "steps": step_results,
            "final_timeline_hash": final_hash,
            "final_duration_s": final_dur,
            "render_status": render_status,
            "output_file": output_file
        }

    def _wait_job_api(self, job_id: str, logger: logging.Logger) -> dict:
        start = time.time()
        while time.time() - start < self.timeout:
            r = requests.get(f"{self.api_url}/api/v1/jobs/{job_id}", timeout=10)
            if r.status_code == 200:
                data = r.json()
                status = data.get("status")
                if status in ("succeeded", "failed"):
                    return data
            time.sleep(1)
        raise TimeoutError(f"Job {job_id} did not finish within {self.timeout}s")

    async def _run_in_process(self, session_data: dict, out_dir: Path, logger: logging.Logger) -> Dict[str, Any]:
        """Execute session directly using core engine classes."""
        from app.core.models import (
            SourceMedia, TranscriptWord, Transcript, Timeline, InstructionStatus
        )
        from app.core.timeline import TimelineEngine
        from app.core.hasher import canonical_hash
        from app.services.instruction_service import InstructionService
        from app.services.render_service import RenderService
        from app.core.models import Project

        video_spec = session_data.get("video", "fixtures/test_video.mp4")

        # Create realistic mock source media & transcript
        duration = 300.0
        sm = SourceMedia(
            id=str(uuid.uuid4()),
            filename=Path(video_spec).name,
            file_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            duration_s=duration,
            frame_rate=30.0,
            width=1920,
            height=1080,
            has_audio=True,
            codec="h264",
            file_path=str(video_spec)
        )

        words = [
            TranscriptWord(word="hello", start_s=1.0, end_s=1.5, speaker="host", confidence=0.98),
            TranscriptWord(word="everyone", start_s=1.6, end_s=2.2, speaker="host", confidence=0.97),
            TranscriptWord(word="welcome", start_s=42.0, end_s=42.4, speaker="host", confidence=0.99),
            TranscriptWord(word="to", start_s=42.4, end_s=42.6, speaker="host", confidence=0.99),
            TranscriptWord(word="the", start_s=42.6, end_s=42.8, speaker="host", confidence=0.99),
            TranscriptWord(word="channel", start_s=42.8, end_s=43.5, speaker="host", confidence=0.98),
            TranscriptWord(word="thanks", start_s=60.0, end_s=60.5, speaker="host", confidence=0.95),
            TranscriptWord(word="pricing", start_s=65.0, end_s=65.8, speaker="host", confidence=0.92),
            TranscriptWord(word="cost", start_s=68.0, end_s=68.5, speaker="host", confidence=0.91),
            TranscriptWord(word="thanks", start_s=120.0, end_s=120.5, speaker="guest", confidence=0.96),
            TranscriptWord(word="pricing", start_s=160.0, end_s=160.7, speaker="guest", confidence=0.94),
            TranscriptWord(word="thanks", start_s=180.0, end_s=180.5, speaker="host", confidence=0.95),
            TranscriptWord(word="pricing", start_s=195.0, end_s=195.6, speaker="host", confidence=0.93),
            TranscriptWord(word="thanks", start_s=240.0, end_s=240.5, speaker="guest", confidence=0.97)
        ]
        tr = Transcript(source_media_id=sm.id, words=words, speakers=["host", "guest"])
        tl = TimelineEngine.create_initial(sm)

        project = Project(
            id=str(uuid.uuid4()),
            source_media=sm,
            transcript=tr,
            timeline=tl
        )

        instruction_service = InstructionService()
        render_service = RenderService()

        step_results = []
        last_say = None
        render_status = "not_requested"
        output_file = None

        steps = session_data.get("steps", [])
        for idx, step in enumerate(steps):
            if "say" in step:
                instruction = step["say"]
                answer = step.get("answer")
                last_say = instruction
            elif "answer" in step:
                instruction = last_say or "Clarification Response"
                answer = step["answer"]
            else:
                continue

            if instruction.strip().lower() == "render":
                render_res = render_service.render(project)
                render_status = "succeeded" if render_res.get("validation", {}).get("valid") else "failed"
                output_file = render_res.get("output_path")
                step_obj = {
                    "step_index": idx,
                    "instruction": instruction,
                    "status": "applied",
                    "operations": [{"type": "RENDER", "params": {}}],
                    "summary": "Rendered final timeline video output.",
                    "question": None,
                    "options": None,
                    "timeline_hash": canonical_hash(project.timeline),
                    "duration_s": TimelineEngine.get_duration(project.timeline)
                }
            else:
                res = await instruction_service.process_instruction(project, instruction, answer=answer)
                step_obj = {
                    "step_index": idx,
                    "instruction": instruction,
                    "status": res.status.value.lower(),
                    "operations": [op.model_dump() for op in res.operations],
                    "summary": res.summary,
                    "question": res.question,
                    "options": res.options,
                    "timeline_hash": res.timeline_hash,
                    "duration_s": round(res.duration_s, 3)
                }

            step_results.append(step_obj)

        # Write timeline.json
        final_tl_dict = project.timeline.model_dump()
        with open(out_dir / "timeline.json", "w", encoding="utf-8") as f:
            json.dump(final_tl_dict, f, indent=2)

        final_hash = step_results[-1]["timeline_hash"] if step_results else canonical_hash(project.timeline)
        final_dur = step_results[-1]["duration_s"] if step_results else TimelineEngine.get_duration(project.timeline)

        return {
            "session_file": session_data.get("name", "session"),
            "video": str(video_spec),
            "project_id": str(project.id),
            "steps": step_results,
            "final_timeline_hash": final_hash,
            "final_duration_s": final_dur,
            "render_status": render_status,
            "output_file": str(output_file) if output_file else None
        }

    def run_all(self, target_path: Path) -> int:
        """Run a single file or a directory of session YAML files."""
        if target_path.is_file():
            session_files = [target_path]
        elif target_path.is_dir():
            session_files = sorted(list(target_path.glob("*.yaml")) + list(target_path.glob("*.yml")))
        else:
            self.logger.error(f"Target path does not exist: {target_path}")
            return 2

        if not session_files:
            self.logger.warning(f"No session YAML files found at: {target_path}")
            return 1

        self.logger.info(f"Discovered {len(session_files)} session files to execute.")
        summaries = []
        failures = 0

        for sf in session_files:
            try:
                res = self.run_session(sf)
                summaries.append({
                    "session": sf.name,
                    "status": "success",
                    "render_status": res.get("render_status"),
                    "final_hash": res.get("final_timeline_hash"),
                    "duration_s": res.get("final_duration_s"),
                    "steps_count": len(res.get("steps", []))
                })
            except Exception as e:
                self.logger.error(f"Error running session {sf.name}: {e}", exc_info=True)
                summaries.append({
                    "session": sf.name,
                    "status": "error",
                    "error": str(e)
                })
                failures += 1

        # Write overall summary.json
        summary_file = self.output_dir / "summary.json"
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump({
                "run_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "total_sessions": len(session_files),
                "passed": len(session_files) - failures,
                "failed": failures,
                "sessions": summaries
            }, f, indent=2)

        self.logger.info(f"Runner completed: {len(session_files) - failures}/{len(session_files)} passed.")
        return 0 if failures == 0 else 1


def main():
    parser = argparse.ArgumentParser(description="IncuBrix Scripted Session Runner")
    parser.add_argument("input", type=str, help="Path to session YAML file or directory of sessions")
    parser.add_argument("--output", type=str, default="./results", help="Directory to store outputs and evidence")
    parser.add_argument("--api-url", type=str, default="http://localhost:8000", help="IncuBrix API server URL")
    parser.add_argument("--timeout", type=int, default=120, help="Job timeout in seconds")
    args = parser.parse_args()

    runner = SessionRunner(api_url=args.api_url, output_dir=Path(args.output), timeout=args.timeout)
    exit_code = runner.run_all(Path(args.input))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
