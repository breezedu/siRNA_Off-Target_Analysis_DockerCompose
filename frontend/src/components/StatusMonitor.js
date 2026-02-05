import React from 'react';
import { Loader } from 'lucide-react';

function StatusMonitor({ jobId }) {
  return (
    <div className="status-monitor">
      <div className="status-content">
        <Loader size={48} className="spinner" />
        <h2>Analyzing Off-Targets</h2>
        <p className="job-id">Job ID: {jobId}</p>
        
        <div className="progress-steps">
          <div className="step active">
            <div className="step-number">1</div>
            <div className="step-label">Extracting seed region</div>
          </div>
          <div className="step active">
            <div className="step-number">2</div>
            <div className="step-label">Searching transcriptome</div>
          </div>
          <div className="step active">
            <div className="step-number">3</div>
            <div className="step-label">Calculating binding energies</div>
          </div>
          <div className="step">
            <div className="step-number">4</div>
            <div className="step-label">Scoring risk factors</div>
          </div>
        </div>

        <p className="status-message">
          This typically takes 30-60 seconds. Please wait...
        </p>
      </div>
    </div>
  );
}

export default StatusMonitor;
