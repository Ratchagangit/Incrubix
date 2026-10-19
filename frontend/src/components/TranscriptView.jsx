import React from 'react';

export default function TranscriptView({ transcript, currentTime }) {
  if (!transcript || !transcript.words || transcript.words.length === 0) {
    return (
      <div className="transcript-panel empty">
        <h3>Transcript</h3>
        <p className="dimmed">No transcript generated yet. Words with timestamps will appear here.</p>
      </div>
    );
  }

  const formatTime = (secs) => {
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  return (
    <div className="transcript-panel">
      <div className="panel-header">
        <h3>Aligned Word Transcript</h3>
        <span className="badge-pill">{transcript.words.length} Words</span>
      </div>
      <div className="words-stream">
        {transcript.words.map((w, idx) => {
          const isCurrent = currentTime >= w.start_s && currentTime <= w.end_s;
          const isLowConf = w.confidence < 0.7;
          return (
            <span
              key={idx}
              className={`word-chip ${isCurrent ? 'current' : ''} ${w.is_filler ? 'filler' : ''} ${isLowConf ? 'low-confidence' : ''} speaker-${w.speaker || 'unknown'}`}
              title={`[${formatTime(w.start_s)} - ${formatTime(w.end_s)}] Speaker: ${w.speaker || 'N/A'}, Conf: ${(w.confidence * 100).toFixed(0)}%`}
            >
              {w.word}
              {w.is_filler && <span className="filler-badge">filler</span>}
              {isLowConf && <span className="warn-badge">?</span>}
            </span>
          );
        })}
      </div>
    </div>
  );
}
