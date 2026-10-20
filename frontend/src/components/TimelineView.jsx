import React from 'react';

export default function TimelineView({ timeline, timelineHash }) {
  if (!timeline || !timeline.segments || timeline.segments.length === 0) {
    return null;
  }

  const segments = timeline.segments || [];
  const totalDuration = segments.reduce((sum, s) => sum + (s.duration_s || 0), 0);

  return (
    <div className="timeline-container">
      <div className="timeline-header">
        <div>
          <h3>Dynamic Presentation Timeline</h3>
          <span className="subtitle">
            Duration: <strong>{(totalDuration || 0).toFixed(2)}s</strong> | Segments: {segments.length} | Anchors: {timeline.anchors?.length || 0}
          </span>
        </div>
        {timelineHash && (
          <div className="hash-badge" title="Deterministic SHA-256 canonical hash of timeline state">
            <span className="hash-label">Hash:</span>
            <code>{timelineHash.substring(0, 16)}...</code>
          </div>
        )}
      </div>

      <div className="track-bar">
        {segments.map((seg, idx) => {
          const dur = seg.duration_s || 0;
          const widthPct = totalDuration > 0 ? (dur / totalDuration) * 100 : 0;
          const sStart = (seg.source_start_s ?? 0).toFixed(1);
          const sEnd = (seg.source_end_s ?? 0).toFixed(1);
          return (
            <div
              key={seg.id || idx}
              className={`track-segment segment-color-${idx % 5}`}
              style={{ width: `${widthPct}%` }}
              title={`Segment #${idx + 1}: Source [${sStart}s - ${sEnd}s] @ ${seg.speed || 1}x (Duration: ${dur.toFixed(1)}s)`}
            >
              <span className="seg-label">
                #{idx + 1} ({dur.toFixed(1)}s) {seg.speed && seg.speed !== 1 ? `[${seg.speed}x]` : ''}
              </span>
            </div>
          );
        })}
      </div>

      {timeline.anchors && timeline.anchors.length > 0 && (
        <div className="anchors-list">
          <h4>Active Semantic Content Anchors:</h4>
          <div className="anchor-tags">
            {timeline.anchors.map((anc, idx) => (
              <span
                key={anc.id || idx}
                className={`anchor-chip ${anc.active ? 'active' : 'inactive'} type-${anc.type || 'edit'}`}
                title={`Source: [${(anc.source_start_s ?? 0).toFixed(1)}s - ${(anc.source_end_s ?? 0).toFixed(1)}s] ${anc.warning ? `Warning: ${anc.warning}` : ''}`}
              >
                <strong>{(anc.type || 'ANCHOR').toUpperCase()}:</strong> {anc.properties?.text ? `"${anc.properties.text}"` : ''}
                {anc.active ? ' [Active]' : ' [Cut/Suppressed]'}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
