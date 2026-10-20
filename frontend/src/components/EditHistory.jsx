import React from 'react';

export default function EditHistory({ history, onUndo, onRedo, onRestore, canUndo, canRedo }) {
  const items = Array.isArray(history) ? history : (history?.history || []);

  if (!items || items.length === 0) {
    return (
      <div className="history-panel empty">
        <h3>Edit History</h3>
        <p className="dimmed">No edit operations recorded yet.</p>
      </div>
    );
  }

  return (
    <div className="history-panel">
      <div className="panel-header">
        <h3>Edit History & Reversibility</h3>
        <div className="history-controls">
          <button
            className="btn btn-sm btn-secondary"
            onClick={onUndo}
            disabled={!canUndo}
            title="Undo last edit (one instruction = one undo)"
          >
            ↩ Undo
          </button>
          <button
            className="btn btn-sm btn-secondary"
            onClick={onRedo}
            disabled={!canRedo}
            title="Redo previously undone edit"
          >
            ↪ Redo
          </button>
        </div>
      </div>

      <div className="history-list">
        {items.map((tx, idx) => (
          <div key={tx.id || idx} className="history-item">
            <div className="step-num">#{tx.step_index ?? idx + 1}</div>
            <div className="step-info">
              <span className="step-instruction">"{tx.instruction || 'Edit'}"</span>
              <span className="step-summary">{tx.result?.summary || ''}</span>
              <code className="step-hash">
                {tx.timeline_after_hash ? tx.timeline_after_hash.substring(0, 10) : ''}
              </code>
            </div>
            {onRestore && (
              <button
                className="btn btn-xs btn-outline"
                onClick={() => onRestore(tx.step_index)}
                title="Restore this specific earlier state as a new edit"
              >
                Restore
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
