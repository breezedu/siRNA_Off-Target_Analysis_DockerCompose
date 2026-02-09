import React, { useState } from 'react';
import axios from 'axios';
import {
  AlertCircle,
  CheckCircle,
  Loader,
  Upload,
  Search,
  Download,
  BarChart3
} from 'lucide-react';
import './App.css';
import ResultsDisplay from './components/ResultsDisplay';
import SequenceInput from './components/SequenceInput';
import StatusMonitor from './components/StatusMonitor';
import CsvUpload from './components/CsvUpload';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8100';

function App() {
  // Input mode: 'single' or 'csv'
  const [inputMode, setInputMode] = useState('single');

  // Single-sequence state
  const [sirnaSequence, setSirnaSequence] = useState('');
  const [sirnaName, setSirnaName] = useState('');

  // CSV batch state
  const [csvSequences, setCsvSequences] = useState([]);

  // Shared parameters
  const [maxMismatches, setMaxMismatches] = useState(1);
  const [energyThreshold, setEnergyThreshold] = useState(-10.0);

  // Single-job state
  const [jobId, setJobId] = useState(null);
  const [status, setStatus] = useState('idle'); // idle, submitting, processing, completed, failed
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  // Batch-job state
  const [batchJobs, setBatchJobs] = useState([]);  // [{job_id, sirna_name}]
  const [batchResults, setBatchResults] = useState([]); // completed results
  const [batchProgress, setBatchProgress] = useState({ total: 0, completed: 0, failed: 0 });
  const [selectedBatchIdx, setSelectedBatchIdx] = useState(0);

  // ========== Single sequence submit ==========
  const handleSubmit = async (e) => {
    e.preventDefault();
    setStatus('submitting');
    setError(null);
    setResults(null);

    try {
      const response = await axios.post(`${API_URL}/api/analyze`, {
        sirnas: [
          {
            name: sirnaName || 'Query siRNA',
            sequence: sirnaSequence
          }
        ],
        max_seed_mismatches: maxMismatches,
        energy_threshold: energyThreshold,
        include_structure: true
      });

      setJobId(response.data.job_id);
      setStatus('processing');
      pollJobStatus(response.data.job_id);
    } catch (err) {
      setStatus('failed');
      setError(err.response?.data?.detail || err.message || 'Failed to submit analysis');
    }
  };

  const pollJobStatus = async (jobId) => {
    const maxAttempts = 120;
    let attempts = 0;

    const poll = setInterval(async () => {
      attempts++;

      try {
        const statusResponse = await axios.get(`${API_URL}/api/status/${jobId}`);

        if (statusResponse.data.status === 'completed') {
          clearInterval(poll);
          fetchResults(jobId);
        } else if (statusResponse.data.status === 'failed') {
          clearInterval(poll);
          setStatus('failed');
          setError(statusResponse.data.message || 'Analysis failed');
        } else if (attempts >= maxAttempts) {
          clearInterval(poll);
          setStatus('failed');
          setError('Analysis timed out after 10 minutes');
        }
      } catch (err) {
        if (attempts >= maxAttempts) {
          clearInterval(poll);
          setStatus('failed');
          setError('Failed to check job status - network error');
        }
      }
    }, 5000);
  };

  const fetchResults = async (jobId) => {
    try {
      const response = await axios.get(`${API_URL}/api/results/${jobId}`);
      setResults(response.data);
      setStatus('completed');
    } catch (err) {
      setStatus('failed');
      setError(err.response?.data?.detail || err.message || 'Failed to fetch results');
    }
  };

  // ========== Batch CSV submit ==========
  const handleBatchSubmit = async (e) => {
    e.preventDefault();
    if (csvSequences.length === 0) return;

    setStatus('submitting');
    setError(null);
    setResults(null);
    setBatchResults([]);
    setSelectedBatchIdx(0);

    try {
      const response = await axios.post(`${API_URL}/api/analyze/batch`, {
        sirnas: csvSequences.map(s => ({
          name: s.name,
          sequence: s.sequence
        })),
        max_seed_mismatches: maxMismatches,
        energy_threshold: energyThreshold,
        include_structure: true
      });

      setBatchJobs(response.data.jobs);
      setBatchProgress({ total: response.data.total, completed: 0, failed: 0 });
      setStatus('processing');
      pollBatchStatus(response.data.jobs);
    } catch (err) {
      setStatus('failed');
      setError(err.response?.data?.detail || err.message || 'Failed to submit batch analysis');
    }
  };

  const pollBatchStatus = async (jobs) => {
    const jobIds = jobs.map(j => j.job_id);
    const maxAttempts = 240; // 20 min for batch
    let attempts = 0;

    const poll = setInterval(async () => {
      attempts++;

      try {
        const response = await axios.post(`${API_URL}/api/batch/status`, {
          job_ids: jobIds
        });

        const { summary } = response.data;
        setBatchProgress({
          total: summary.total,
          completed: summary.completed,
          failed: summary.failed
        });

        if (summary.all_done) {
          clearInterval(poll);
          fetchBatchResults(jobs);
        } else if (attempts >= maxAttempts) {
          clearInterval(poll);
          // Still fetch whatever completed
          fetchBatchResults(jobs);
        }
      } catch (err) {
        if (attempts >= maxAttempts) {
          clearInterval(poll);
          setStatus('failed');
          setError('Failed to check batch status - network error');
        }
      }
    }, 5000);
  };

  const fetchBatchResults = async (jobs) => {
    const allResults = [];

    for (const job of jobs) {
      try {
        const response = await axios.get(`${API_URL}/api/results/${job.job_id}`);
        allResults.push({
          sirna_name: job.sirna_name,
          job_id: job.job_id,
          status: 'completed',
          data: response.data
        });
      } catch {
        allResults.push({
          sirna_name: job.sirna_name,
          job_id: job.job_id,
          status: 'failed',
          data: null
        });
      }
    }

    setBatchResults(allResults);
    setStatus('completed');
  };

  // ========== Download ==========
  const downloadResults = () => {
    if (!results) return;
    const csv = convertToCSV(results.offtargets);
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${results.sirna_name}_offtargets.csv`;
    a.click();
  };

  const downloadBatchResults = () => {
    const completedResults = batchResults.filter(r => r.status === 'completed' && r.data);
    if (completedResults.length === 0) return;

    const headers = [
      'siRNA Name',
      'Gene Symbol',
      'Transcript ID',
      'Position',
      'Delta G (kcal/mol)',
      'Risk Score',
      'Seed Matches',
      'Mismatches',
      'AU Content (%)',
      'Structure Accessibility'
    ];

    const rows = [];
    for (const result of completedResults) {
      if (!result.data.offtargets) continue;
      for (const ot of result.data.offtargets) {
        rows.push([
          result.sirna_name,
          ot.gene_symbol,
          ot.transcript_id,
          ot.position,
          ot.delta_g,
          ot.risk_score,
          ot.seed_matches,
          ot.mismatches,
          ot.au_content,
          ot.structure_accessibility
        ]);
      }
    }

    const csv = [headers, ...rows].map(row => row.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'batch_offtargets.csv';
    a.click();
  };

  const convertToCSV = (offtargets) => {
    const headers = [
      'Gene Symbol',
      'Transcript ID',
      'Position',
      'Delta G (kcal/mol)',
      'Risk Score',
      'Seed Matches',
      'Mismatches',
      'AU Content (%)',
      'Structure Accessibility'
    ];

    const rows = offtargets.map(ot => [
      ot.gene_symbol,
      ot.transcript_id,
      ot.position,
      ot.delta_g,
      ot.risk_score,
      ot.seed_matches,
      ot.mismatches,
      ot.au_content,
      ot.structure_accessibility
    ]);

    return [headers, ...rows].map(row => row.join(',')).join('\n');
  };

  // ========== Reset ==========
  const resetAnalysis = () => {
    setSirnaSequence('');
    setSirnaName('');
    setCsvSequences([]);
    setJobId(null);
    setStatus('idle');
    setResults(null);
    setError(null);
    setBatchJobs([]);
    setBatchResults([]);
    setBatchProgress({ total: 0, completed: 0, failed: 0 });
    setSelectedBatchIdx(0);
  };

  // ========== Helpers for batch results view ==========
  const isBatchMode = inputMode === 'csv' && batchResults.length > 0;
  const currentBatchResult = isBatchMode ? batchResults[selectedBatchIdx] : null;
  const currentResultData = isBatchMode
    ? currentBatchResult?.data
    : results;

  return (
    <div className="App">
      <header className="App-header">
        <div className="header-content">
          <h1>siRNA Off-Target Analysis Tool</h1>
          <p className="subtitle">Comprehensive seed-based off-target prediction</p>
        </div>
      </header>

      <main className="App-main">
        <div className="container">
          {status === 'idle' || status === 'submitting' ? (
            <div className="input-section">
              <div className="input-mode-toggle">
                <button
                  type="button"
                  className={`mode-btn ${inputMode === 'single' ? 'active' : ''}`}
                  onClick={() => setInputMode('single')}
                  disabled={status === 'submitting'}
                >
                  <Search size={18} />
                  Single Sequence
                </button>
                <button
                  type="button"
                  className={`mode-btn ${inputMode === 'csv' ? 'active' : ''}`}
                  onClick={() => setInputMode('csv')}
                  disabled={status === 'submitting'}
                >
                  <Upload size={18} />
                  CSV Batch Upload
                </button>
              </div>

              {inputMode === 'single' ? (
                <SequenceInput
                  sirnaName={sirnaName}
                  setSirnaName={setSirnaName}
                  sirnaSequence={sirnaSequence}
                  setSirnaSequence={setSirnaSequence}
                  maxMismatches={maxMismatches}
                  setMaxMismatches={setMaxMismatches}
                  energyThreshold={energyThreshold}
                  setEnergyThreshold={setEnergyThreshold}
                  onSubmit={handleSubmit}
                  isSubmitting={status === 'submitting'}
                />
              ) : (
                <form onSubmit={handleBatchSubmit} className="sequence-form">
                  <div className="form-header">
                    <h2>Upload CSV File</h2>
                    <p>Upload a CSV with siRNA sequences for batch analysis</p>
                  </div>

                  <CsvUpload
                    onSequencesParsed={setCsvSequences}
                    isSubmitting={status === 'submitting'}
                  />

                  <div className="form-row" style={{ marginTop: '1.5rem' }}>
                    <div className="form-group">
                      <label htmlFor="batch-max-mismatches">
                        Max Seed Mismatches
                        <span className="label-hint">Higher = more permissive</span>
                      </label>
                      <select
                        id="batch-max-mismatches"
                        value={maxMismatches}
                        onChange={(e) => setMaxMismatches(parseInt(e.target.value))}
                        className="form-select"
                      >
                        <option value="0">0 (Exact match only)</option>
                        <option value="1">1 (Recommended)</option>
                        <option value="2">2 (Very permissive)</option>
                      </select>
                    </div>

                    <div className="form-group">
                      <label htmlFor="batch-energy-threshold">
                        Energy Threshold (kcal/mol)
                        <span className="label-hint">More negative = stronger binding</span>
                      </label>
                      <select
                        id="batch-energy-threshold"
                        value={energyThreshold}
                        onChange={(e) => setEnergyThreshold(parseFloat(e.target.value))}
                        className="form-select"
                      >
                        <option value="-15">-15 (Stringent)</option>
                        <option value="-10">-10 (Recommended)</option>
                        <option value="-5">-5 (Permissive)</option>
                      </select>
                    </div>
                  </div>

                  <div className="info-box">
                    <AlertCircle size={18} />
                    <div>
                      <strong>CSV Format:</strong> Include a header row with <code>name</code> and <code>sequence</code> columns.
                      Each sequence should be 19-23 nucleotides (A, C, G, T, U). Max 100 sequences per batch.
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={csvSequences.length === 0 || status === 'submitting'}
                    className="btn-primary btn-large"
                  >
                    {status === 'submitting'
                      ? 'Submitting...'
                      : `Analyze ${csvSequences.length} Sequence${csvSequences.length !== 1 ? 's' : ''}`
                    }
                  </button>
                </form>
              )}
            </div>
          ) : status === 'processing' ? (
            inputMode === 'csv' ? (
              <div className="status-monitor">
                <div className="status-content">
                  <Loader size={48} className="spinner" />
                  <h2>Batch Analysis in Progress</h2>
                  <p className="batch-progress-text">
                    {batchProgress.completed + batchProgress.failed} / {batchProgress.total} sequences processed
                  </p>
                  <div className="batch-progress-bar">
                    <div
                      className="batch-progress-fill"
                      style={{
                        width: batchProgress.total > 0
                          ? `${((batchProgress.completed + batchProgress.failed) / batchProgress.total) * 100}%`
                          : '0%'
                      }}
                    />
                  </div>
                  {batchProgress.failed > 0 && (
                    <p className="batch-failed-note">{batchProgress.failed} failed</p>
                  )}
                  <p className="status-message">
                    Analyzing each siRNA sequence. This may take a few minutes for large batches...
                  </p>
                </div>
              </div>
            ) : (
              <StatusMonitor jobId={jobId} />
            )
          ) : status === 'completed' && (currentResultData || batchResults.length > 0) ? (
            <div className="results-section">
              <div className="results-header">
                <div className="results-title">
                  <CheckCircle size={28} color="#10b981" />
                  <h2>Analysis Complete</h2>
                </div>
                <div className="results-actions">
                  <button
                    onClick={isBatchMode ? downloadBatchResults : downloadResults}
                    className="btn-secondary"
                  >
                    <Download size={18} />
                    {isBatchMode ? 'Download All CSV' : 'Download CSV'}
                  </button>
                  <button onClick={resetAnalysis} className="btn-primary">
                    New Analysis
                  </button>
                </div>
              </div>

              {isBatchMode && (
                <div className="batch-selector">
                  <label>Select siRNA:</label>
                  <div className="batch-tabs">
                    {batchResults.map((r, idx) => (
                      <button
                        key={idx}
                        className={`batch-tab ${idx === selectedBatchIdx ? 'active' : ''} ${r.status === 'failed' ? 'failed' : ''}`}
                        onClick={() => setSelectedBatchIdx(idx)}
                      >
                        {r.sirna_name}
                        {r.status === 'completed' ? (
                          <CheckCircle size={14} />
                        ) : (
                          <AlertCircle size={14} />
                        )}
                      </button>
                    ))}
                  </div>
                  <div className="batch-summary-line">
                    {batchResults.filter(r => r.status === 'completed').length} of {batchResults.length} completed successfully
                  </div>
                </div>
              )}

              {currentResultData ? (
                <>
                  <div className="summary-cards">
                    <div className="summary-card high-risk">
                      <div className="card-label">High Risk</div>
                      <div className="card-value">{currentResultData.high_risk_count}</div>
                      <div className="card-desc">Risk Score &gt; 0.7</div>
                    </div>
                    <div className="summary-card moderate-risk">
                      <div className="card-label">Moderate Risk</div>
                      <div className="card-value">{currentResultData.moderate_risk_count}</div>
                      <div className="card-desc">Risk Score 0.5-0.7</div>
                    </div>
                    <div className="summary-card low-risk">
                      <div className="card-label">Low Risk</div>
                      <div className="card-value">{currentResultData.low_risk_count}</div>
                      <div className="card-desc">Risk Score &lt; 0.5</div>
                    </div>
                    <div className="summary-card total">
                      <div className="card-label">Total Off-Targets</div>
                      <div className="card-value">{currentResultData.total_offtargets}</div>
                      <div className="card-desc">&Delta;G &le; {energyThreshold} kcal/mol</div>
                    </div>
                  </div>

                  <ResultsDisplay
                    offtargets={currentResultData.offtargets}
                    sirnaName={currentResultData.sirna_name}
                  />
                </>
              ) : (
                <div className="error-section">
                  <AlertCircle size={48} color="#ef4444" />
                  <h2>Analysis Failed</h2>
                  <p>Analysis for "{currentBatchResult?.sirna_name}" did not complete successfully.</p>
                </div>
              )}
            </div>
          ) : status === 'failed' ? (
            <div className="error-section">
              <AlertCircle size={48} color="#ef4444" />
              <h2>Analysis Failed</h2>
              <p>{error}</p>
              {jobId && (
                <p className="error-details">Job ID: {jobId}</p>
              )}
              <button onClick={resetAnalysis} className="btn-primary">
                Try Again
              </button>
            </div>
          ) : null}
        </div>
      </main>

      <footer className="App-footer">
        <p>&copy; 2024 siRNA Off-Target Analysis Tool | Bioinformatics Research</p>
      </footer>
    </div>
  );
}

export default App;
