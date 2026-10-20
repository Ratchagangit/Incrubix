import React from 'react';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          padding: '24px',
          margin: '20px',
          background: '#1e293b',
          border: '1px solid #ef4444',
          borderRadius: '8px',
          color: '#f8fafc',
          textAlign: 'center'
        }}>
          <h2>⚠️ An interface rendering error occurred</h2>
          <p style={{ color: '#94a3b8', margin: '12px 0' }}>
            {this.state.error?.message || 'Component failed to render.'}
          </p>
          <button
            onClick={() => {
              this.setState({ hasError: false, error: null });
              window.location.reload();
            }}
            style={{
              padding: '8px 16px',
              background: '#3b82f6',
              color: '#fff',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer'
            }}
          >
            🔄 Reload Workspace
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
