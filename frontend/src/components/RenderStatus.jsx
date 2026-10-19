import React, { useState, useEffect } from 'react';
import { renderVideo, getJob } from '../api';

export default function RenderStatus({ projectId, onRenderCompleted }) {
  const [jobId, setJobId] = useState(null);
  const [job, setJob] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const startRender = async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await renderVideo(projectId);
      setJobId(resp.job_id);
    } catch (err) {
      setError(err.response?.data?.error?.message || err.message || 'Render failed to start');
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!jobId) return;

    const interval = setInterval(async () => {
      try {
        const j = await getJob(jobId);
        setJob(j);
        if (j.status === 'succeeded' || j.status === 'failed') {
          clearInterval(interval);
          setLoading(false);
          if (j.status === 'succeeded' && onRenderCompleted) {
            onRenderCompleted(j);
          }
        }
      } catch (err) {
        clearInterval(interval);
        setLoading(false);
        setError('Failed to poll render job status');
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [jobId]);

  return (
    <div className="render-panel">
      <div className="render-header">
        <div>
          <h3>Export & Render Output</h3>
          <p className="subtitle">Compiles edits into a single-pass FFmpeg filter graph with &plusmn;1 frame validation.</p>
        </div>
        <button
          className="btn btn-success"
          onClick={startRender}
          disabled={loading || !projectId}
        >
          {loading ? 'Rendering...' : '🎬 Render Video'}
        </button>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {job && (
        <div className={`job-status-card status-${job.status}`}>
          <div className="job-info-row">
            <span>Job ID: <code>{job.id}</code></span>
            <span className={`status-pill ${job.status}`}>{job.status.toUpperCase()}</span>
          </div>

          <div className="progress-bar-bg">
            <div className="progress-bar-fill" style={{ width: `${job.progress}%` }}></div>
          </div>
          <span className="progress-label">{job.progress}% Complete</span>

          {job.status === 'succeeded' && (
            <div className="render-success-box">
              <p>✅ Media rendering verified and synchronized within &le; 1 frame.</p>
              <a
                href={`/api/v1/jobs/${job.id}/download`}
                className="btn btn-primary btn-download"
                target="_blank"
                rel="noreferrer"
                download
              >
                ⬇️ Download Verified Render (.mp4)
              </a>
            </div>
          )}

          {job.status === 'failed' && (
            <div className="error-banner">
              Render failed: {job.error || 'Unknown rendering error'}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
