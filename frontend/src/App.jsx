import React, { useState, useEffect } from 'react';
import VideoUpload from './components/VideoUpload';
import VideoPlayer from './components/VideoPlayer';
import TranscriptView from './components/TranscriptView';
import TimelineView from './components/TimelineView';
import InstructionInput from './components/InstructionInput';
import EditHistory from './components/EditHistory';
import RenderStatus from './components/RenderStatus';
import ErrorBoundary from './components/ErrorBoundary';
import {
  checkHealth,
  getVideo,
  getTranscript,
  getTimeline,
  getHistory,
  sendInstruction,
  undo,
  redo,
  restore
} from './api';

export default function App() {
  const [health, setHealth] = useState({ status: 'connecting' });
  const [projectId, setProjectId] = useState(null);
  const [videoId, setVideoId] = useState(null);
  const [videoMeta, setVideoMeta] = useState(null);
  const [transcript, setTranscript] = useState(null);
  const [timeline, setTimeline] = useState(null);
  const [timelineHash, setTimelineHash] = useState('');
  const [history, setHistory] = useState([]);
  const [currentTime, setCurrentTime] = useState(0);
  const [loading, setLoading] = useState(false);
  const [lastResult, setLastResult] = useState(null);

  // Poll backend health
  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const data = await checkHealth();
        setHealth(data);
      } catch (err) {
        setHealth({ status: 'unreachable' });
      }
    };
    fetchHealth();
    const timer = setInterval(fetchHealth, 10000);
    return () => clearInterval(timer);
  }, []);

  // When a video is ingested/uploaded
  const handleVideoUploaded = async (data) => {
    setProjectId(data.project_id);
    setVideoId(data.video_id);

    // Refresh each project resource independently to prevent cascading failures
    try {
      const v = await getVideo(data.video_id);
      setVideoMeta(v);
    } catch (e) {
      console.warn('Video metadata fetch notice:', e);
    }

    try {
      const t = await getTranscript(data.video_id);
      setTranscript(t);
    } catch (e) {
      try {
        const t = await getTranscript(data.project_id);
        setTranscript(t);
      } catch (e2) {
        console.warn('Transcript not ready yet:', e2);
      }
    }

    try {
      const tl = await getTimeline(data.project_id);
      setTimeline(tl);
    } catch (e) {
      console.warn('Timeline fetch notice:', e);
    }

    try {
      const h = await getHistory(data.project_id);
      setHistory(Array.isArray(h) ? h : (h?.history || []));
    } catch (e) {
      console.warn('History fetch notice:', e);
    }
  };

  const handleSendInstruction = async (instText, answer = null) => {
    if (!projectId) return;
    setLoading(true);
    try {
      const res = await sendInstruction(projectId, instText, answer);
      setLastResult(res);
      if (res.timeline_hash) {
        setTimelineHash(res.timeline_hash);
      }
      // Refresh timeline and history
      const tl = await getTimeline(projectId);
      setTimeline(tl);
      const h = await getHistory(projectId);
      setHistory(Array.isArray(h) ? h : (h?.history || []));
    } catch (err) {
      setLastResult({
        status: 'REJECTED',
        summary: err.response?.data?.error?.message || err.message || 'Instruction evaluation failed',
        warnings: []
      });
    } finally {
      setLoading(false);
    }
  };

  const handleUndo = async () => {
    if (!projectId) return;
    setLoading(true);
    try {
      const res = await undo(projectId);
      setLastResult(res);
      setTimelineHash(res.timeline_hash);
      const tl = await getTimeline(projectId);
      setTimeline(tl);
      const h = await getHistory(projectId);
      setHistory(Array.isArray(h) ? h : (h?.history || []));
    } catch (err) {
      console.error('Undo failed', err);
    } finally {
      setLoading(false);
    }
  };

  const handleRedo = async () => {
    if (!projectId) return;
    setLoading(true);
    try {
      const res = await redo(projectId);
      setLastResult(res);
      setTimelineHash(res.timeline_hash);
      const tl = await getTimeline(projectId);
      setTimeline(tl);
      const h = await getHistory(projectId);
      setHistory(Array.isArray(h) ? h : (h?.history || []));
    } catch (err) {
      console.error('Redo failed', err);
    } finally {
      setLoading(false);
    }
  };

  const handleRestore = async (stepIndex) => {
    if (!projectId) return;
    setLoading(true);
    try {
      const res = await restore(projectId, stepIndex);
      setLastResult(res);
      setTimelineHash(res.timeline_hash);
      const tl = await getTimeline(projectId);
      setTimeline(tl);
      const h = await getHistory(projectId);
      setHistory(Array.isArray(h) ? h : (h?.history || []));
    } catch (err) {
      console.error('Restore failed', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-layout">
      <header className="app-header">
        <div className="header-brand">
          <span className="logo-icon">🎬</span>
          <h1>IncuBrix Video Editor</h1>
          <span className="version-pill">v1.0.0</span>
        </div>
        <div className="header-meta">
          <span className={`status-indicator ${health.status}`}>
            ● Backend: {health.status}
          </span>
          {projectId && <span className="project-badge">Project: {projectId.substring(0, 8)}...</span>}
        </div>
      </header>

      <main className="main-content">
        <ErrorBoundary>
          {!projectId ? (
            <div className="onboarding-card">
              <VideoUpload onVideoUploaded={handleVideoUploaded} />
            </div>
          ) : (
            <div className="workspace-grid">
              {/* Left Column: Video Preview and Transcript */}
              <div className="left-column">
                <VideoPlayer videoId={videoId} onTimeUpdate={setCurrentTime} />
                <TranscriptView transcript={transcript} currentTime={currentTime} />
              </div>

              {/* Right Column: Prompt Input, History, and Render */}
              <div className="right-column">
                <InstructionInput
                  onSendInstruction={handleSendInstruction}
                  loading={loading}
                  lastResult={lastResult}
                />
                <EditHistory
                  history={history}
                  onUndo={handleUndo}
                  onRedo={handleRedo}
                  onRestore={handleRestore}
                  canUndo={history.length > 0}
                  canRedo={true}
                />
                <RenderStatus projectId={projectId} />
              </div>

              {/* Bottom Row: Timeline Visualizer */}
              <div className="bottom-row">
                <TimelineView timeline={timeline} timelineHash={timelineHash} />
              </div>
            </div>
          )}
        </ErrorBoundary>
      </main>

      <footer className="app-footer">
        <span>IncuBrix Prompt-Based Video Editing Engine — Engineering Assessment 2 (PS2)</span>
        <span>Content-Anchored Timeline Architecture</span>
      </footer>
    </div>
  );
}
