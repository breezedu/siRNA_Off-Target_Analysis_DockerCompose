import React from 'react';
import { AlertCircle } from 'lucide-react';

function SequenceInput({
  sirnaName,
  setSirnaName,
  sirnaSequence,
  setSirnaSequence,
  maxMismatches,
  setMaxMismatches,
  energyThreshold,
  setEnergyThreshold,
  onSubmit,
  isSubmitting
}) {
  const validateSequence = (seq) => {
    const cleaned = seq.toUpperCase().replace(/\s/g, '');
    const isValid = /^[ACGTU]+$/.test(cleaned);
    const validLength = cleaned.length >= 19 && cleaned.length <= 23;
    return { isValid: isValid && validLength, cleaned };
  };

  const handleSequenceChange = (e) => {
    const value = e.target.value;
    const { cleaned } = validateSequence(value);
    setSirnaSequence(cleaned);
  };

  const { isValid } = validateSequence(sirnaSequence);
  const canSubmit = isValid && sirnaSequence.length >= 19 && !isSubmitting;

  return (
    <form onSubmit={onSubmit} className="sequence-form">
      <div className="form-header">
        <h2>Enter siRNA Sequence</h2>
        <p>Guide strand sequence (19-23 nucleotides)</p>
      </div>

      <div className="form-group">
        <label htmlFor="sirna-name">siRNA Name (optional)</label>
        <input
          id="sirna-name"
          type="text"
          value={sirnaName}
          onChange={(e) => setSirnaName(e.target.value)}
          placeholder="e.g., siRNA_BRCA1_001"
          className="form-input"
        />
      </div>

      <div className="form-group">
        <label htmlFor="sirna-sequence">
          siRNA Sequence *
          <span className="sequence-length">
            {sirnaSequence.length > 0 && `(${sirnaSequence.length} nt)`}
          </span>
        </label>
        <textarea
          id="sirna-sequence"
          value={sirnaSequence}
          onChange={handleSequenceChange}
          placeholder="Enter guide strand sequence (e.g., GUGAUGUAGCCUAUGACACAA)"
          className={`form-textarea ${sirnaSequence && !isValid ? 'invalid' : ''}`}
          rows="3"
          required
        />
        {sirnaSequence && !isValid && (
          <div className="validation-error">
            <AlertCircle size={16} />
            <span>Invalid sequence. Use only A, C, G, T, U (19-23 nucleotides)</span>
          </div>
        )}
      </div>

      <div className="form-row">
        <div className="form-group">
          <label htmlFor="max-mismatches">
            Max Seed Mismatches
            <span className="label-hint">Higher = more permissive</span>
          </label>
          <select
            id="max-mismatches"
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
          <label htmlFor="energy-threshold">
            Energy Threshold (kcal/mol)
            <span className="label-hint">More negative = stronger binding</span>
          </label>
          <select
            id="energy-threshold"
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
          <strong>Note:</strong> Analysis typically takes 30-60 seconds for human transcriptome.
          Seed region (positions 2-8) is the primary determinant of off-target binding.
        </div>
      </div>

      <button
        type="submit"
        disabled={!canSubmit}
        className="btn-primary btn-large"
      >
        {isSubmitting ? 'Submitting...' : 'Analyze Off-Targets'}
      </button>
    </form>
  );
}

export default SequenceInput;
