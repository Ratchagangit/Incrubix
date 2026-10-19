import React, { useState } from 'react';
import { uploadVideo, ingestUrl } from '../api';

export default function VideoUpload({ onVideoUploaded }) {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [dragActive, setDragActive] = useState(false);

  const handleFile = async (file) => {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const data = await uploadVideo(file);
      onVideoUploaded(data);
    } catch (err) {
      setError(err.response?.data?.error?.message || err.message || 'Upload failed');
    } finally {
      setLoading(false);
    }
  };

  const handleUrlSubmit = async (e) => {
    e.preventDefault();
    if (!url.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await ingestUrl(url.trim());
      onVideoUploaded(data);
    } catch (err) {
      setError(err.response?.data?.error?.message || err.message || 'Ingestion failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="upload-container">
      <h2>1. Load Source Video</h2>
      <p className="subtitle">Upload talking-head MP4/MOV or supply a public URL.</p>

      {error && <div className="error-banner">{error}</div>}

      <div
        className={`dropzone ${dragActive ? 'active' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
        onDragLeave={() => setDragActive(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragActive(false);
          if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            handleFile(e.dataTransfer.files[0]);
          }
        }}
      >
        <span className="upload-icon">📁</span>
        <p>Drag & drop talking-head video file here</p>
        <label className="btn btn-secondary">
          Browse File
          <input
            type="file"
            accept="video/mp4,video/quicktime,video/webm"
            hidden
            onChange={(e) => handleFile(e.target.files[0])}
            disabled={loading}
          />
        </label>
      </div>

      <div className="divider"><span>OR</span></div>

      <form className="url-form" onSubmit={handleUrlSubmit}>
        <input
          type="url"
          className="input-field"
          placeholder="https://example.com/interview.mp4"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          disabled={loading}
        />
        <button type="submit" className="btn btn-primary" disabled={loading || !url.trim()}>
          {loading ? 'Ingesting...' : 'Ingest URL'}
        </button>
      </form>

      {loading && <div className="loading-spinner">Uploading & probing video metadata...</div>}
    </div>
  );
}
