import React, { useRef, useEffect } from 'react';

export default function VideoPlayer({ videoId, onTimeUpdate }) {
  const videoRef = useRef(null);
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
        <video
          ref={videoRef}
          className="video-element"
          controls
          src={srcUrl}
          onTimeUpdate={handleTime}
        />
      ) : (
        <div className="placeholder-video">
          <span>🎬 Load or select a video to begin editing</span>
        </div>
      )}
    </div>
  );
}
