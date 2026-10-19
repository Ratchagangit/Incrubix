import React, { useState } from 'react';

export default function InstructionInput({ onSendInstruction, loading, lastResult }) {
  const [instruction, setInstruction] = useState('');
  const [clarificationAnswer, setClarificationAnswer] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!instruction.trim() || loading) return;
    onSendInstruction(instruction.trim(), null);
    setInstruction('');
  };

  const handleClarificationSelect = (opt) => {
    if (lastResult?.question) {
      onSendInstruction(instruction || lastResult.question, opt);
      setClarificationAnswer('');
    }
  };

  const handleClarificationSubmit = (e) => {
    e.preventDefault();
    if (!clarificationAnswer.trim() || loading) return;
    onSendInstruction(instruction || lastResult.question, clarificationAnswer.trim());
    setClarificationAnswer('');
  };

  return (
    <div className="instruction-box">
      <h3>Natural-Language Video Editing</h3>
      <p className="subtitle">
        Type an instruction like: <em>"Cut the first 30 seconds"</em> or <em>"Add a caption 'Welcome!' when I say welcome to the channel"</em>.
      </p>

      <form className="instruction-form" onSubmit={handleSubmit}>
        <input
          type="text"
          className="input-field main-prompt"
          placeholder="e.g. Remove the part about pricing, or Speed up from 1:00 to 1:30 by 2x..."
          value={instruction}
          onChange={(e) => setInstruction(e.target.value)}
          disabled={loading}
        />
        <button type="submit" className="btn btn-primary" disabled={loading || !instruction.trim()}>
          {loading ? 'Evaluating...' : 'Apply Edit'}
        </button>
      </form>

      {lastResult && (
        <div className={`result-card status-${lastResult.status?.toLowerCase()}`}>
          <div className="result-header">
            <span className={`status-pill ${lastResult.status?.toLowerCase()}`}>
              {lastResult.status}
            </span>
            <span className="duration-tag">
              Timeline: {lastResult.duration_s?.toFixed(2)}s
            </span>
          </div>

          <p className="result-summary">{lastResult.summary}</p>

          {lastResult.status === 'NEEDS_CLARIFICATION' && (
            <div className="clarification-dialog">
              <div className="clarification-question">
                <strong>Question:</strong> {lastResult.question}
              </div>
              {lastResult.options && lastResult.options.length > 0 && (
                <div className="options-grid">
                  {lastResult.options.map((opt, idx) => (
                    <button
                      key={idx}
                      type="button"
                      className="btn btn-option"
                      onClick={() => handleClarificationSelect(opt)}
                      disabled={loading}
                    >
                      {opt}
                    </button>
                  ))}
                </div>
              )}

              <form className="custom-answer-form" onSubmit={handleClarificationSubmit}>
                <input
                  type="text"
                  className="input-field"
                  placeholder="Or type custom clarification answer..."
                  value={clarificationAnswer}
                  onChange={(e) => setClarificationAnswer(e.target.value)}
                  disabled={loading}
                />
                <button type="submit" className="btn btn-secondary" disabled={loading || !clarificationAnswer.trim()}>
                  Submit Answer
                </button>
              </form>
            </div>
          )}

          {lastResult.warnings && lastResult.warnings.length > 0 && (
            <ul className="warnings-list">
              {lastResult.warnings.map((w, idx) => (
                <li key={idx}>⚠️ {w}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
