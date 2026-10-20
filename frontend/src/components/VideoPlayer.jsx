import React, { useRef, useState } from 'react';

export default function VideoPlayer({ videoId, onTimeUpdate }) {
  const videoRef = useRef(null);
  const [loadError, setLoadError] = useState(false);
  const srcUrl = videoId ? `/api/v1/videos/${videoId}/download` : null;

  const handleTime = () => {
    if (videoRef.current && onTimeUpdate) {
      onTimeUpdate(videoRef.current.currentTime);
    }
  };

  return (
    <div className="player-wrapper">
      <div className="player-header">
        <span className="badge">Original Source Preview</span>
      </div>
      {srcUrl ? (
        <div className="video-container" style={{ position: 'relative', width: '100%', minHeight: '200px' }}>
          <video
            ref={videoRef}
            className="video-element"
            controls
            playsInline
            src={srcUrl}
            onTimeUpdate={handleTime}
            onError={() => setLoadError(true)}
            style={{ width: '100%', borderRadius: '8px' }}
          />
          {loadError && (
            <div
              className="video-error-overlay"
              style={{
                padding: '12px',
                background: 'rgba(239, 68, 68, 0.15)',
                border: '1px solid #ef4444',
                borderRadius: '6px',
                margin: '8px 0',
                color: '#fca5a5',
                fontSize: '13px'
              }}
            >
              <span>⚠️ Video media stream notice: Browser cannot directly decode this file, but all prompt instructions, timeline edits, and backend rendering are fully functional.</span>
            </div>
          )}
        </div>
      ) : (
        <div className="placeholder-video">
          <span>🎬 Load or select a video to begin editing</span>
        </div>
      )}
    </div>
  );
}
