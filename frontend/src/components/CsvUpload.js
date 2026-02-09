import React, { useRef, useState } from 'react';
import { Upload, AlertCircle, FileText, X, CheckCircle } from 'lucide-react';

function CsvUpload({ onSequencesParsed, isSubmitting }) {
  const fileInputRef = useRef(null);
  const [fileName, setFileName] = useState('');
  const [parseError, setParseError] = useState(null);
  const [sequences, setSequences] = useState([]);

  const validateSequence = (seq) => {
    const cleaned = seq.toUpperCase().replace(/\s/g, '');
    const isValid = /^[ACGTU]+$/.test(cleaned);
    const validLength = cleaned.length >= 19 && cleaned.length <= 23;
    return { isValid: isValid && validLength, cleaned };
  };

  const parseCsv = (text) => {
    const lines = text.trim().split(/\r?\n/);
    if (lines.length < 2) {
      setParseError('CSV must have a header row and at least one data row.');
      return [];
    }

    const header = lines[0].split(',').map(h => h.trim().toLowerCase());
    const seqIdx = header.findIndex(h => ['sequence', 'seq', 'sirna_sequence', 'sirna'].includes(h));
    const nameIdx = header.findIndex(h => ['name', 'sirna_name', 'id', 'identifier'].includes(h));

    if (seqIdx === -1) {
      setParseError(
        'CSV must contain a "sequence" column. Accepted headers: sequence, seq, sirna_sequence, sirna'
      );
      return [];
    }

    const parsed = [];
    const errors = [];

    for (let i = 1; i < lines.length; i++) {
      const line = lines[i].trim();
      if (!line) continue;

      const cols = line.split(',').map(c => c.trim());
      const rawSeq = cols[seqIdx] || '';
      const name = nameIdx !== -1 && cols[nameIdx] ? cols[nameIdx] : `siRNA_${i}`;
      const { isValid, cleaned } = validateSequence(rawSeq);

      parsed.push({
        row: i + 1,
        name,
        sequence: cleaned || rawSeq.toUpperCase().replace(/\s/g, ''),
        valid: isValid,
      });

      if (!isValid) {
        errors.push(`Row ${i + 1}: invalid sequence "${rawSeq}" (need 19-23 nt of A/C/G/T/U)`);
      }
    }

    if (parsed.length === 0) {
      setParseError('No data rows found in CSV.');
      return [];
    }

    if (errors.length > 0 && errors.length === parsed.length) {
      setParseError(`All sequences are invalid. ${errors[0]}`);
      return parsed;
    }

    setParseError(null);
    return parsed;
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (!file.name.endsWith('.csv')) {
      setParseError('Please upload a .csv file.');
      return;
    }

    setFileName(file.name);
    const reader = new FileReader();
    reader.onload = (event) => {
      const parsed = parseCsv(event.target.result);
      setSequences(parsed);
      const validSeqs = parsed.filter(s => s.valid);
      onSequencesParsed(validSeqs);
    };
    reader.readAsText(file);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    const file = e.dataTransfer.files[0];
    if (file) {
      const input = fileInputRef.current;
      const dt = new DataTransfer();
      dt.items.add(file);
      input.files = dt.files;
      handleFileChange({ target: input });
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const clearFile = () => {
    setFileName('');
    setSequences([]);
    setParseError(null);
    onSequencesParsed([]);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const validCount = sequences.filter(s => s.valid).length;
  const invalidCount = sequences.filter(s => !s.valid).length;

  return (
    <div className="csv-upload">
      <div
        className={`csv-dropzone ${fileName ? 'has-file' : ''}`}
        onClick={() => !fileName && fileInputRef.current?.click()}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv"
          onChange={handleFileChange}
          style={{ display: 'none' }}
          disabled={isSubmitting}
        />

        {!fileName ? (
          <>
            <Upload size={36} className="upload-icon" />
            <p className="dropzone-title">Drop CSV file here or click to browse</p>
            <p className="dropzone-hint">
              CSV with columns: <code>name</code>, <code>sequence</code>
            </p>
          </>
        ) : (
          <div className="file-info">
            <FileText size={24} />
            <span className="file-name">{fileName}</span>
            <button
              type="button"
              className="btn-clear-file"
              onClick={(e) => { e.stopPropagation(); clearFile(); }}
              disabled={isSubmitting}
            >
              <X size={18} />
            </button>
          </div>
        )}
      </div>

      {parseError && (
        <div className="validation-error csv-error">
          <AlertCircle size={16} />
          <span>{parseError}</span>
        </div>
      )}

      {sequences.length > 0 && (
        <div className="csv-preview">
          <div className="csv-preview-header">
            <h4>
              Parsed Sequences
              <span className="csv-counts">
                {validCount > 0 && (
                  <span className="count-valid">
                    <CheckCircle size={14} /> {validCount} valid
                  </span>
                )}
                {invalidCount > 0 && (
                  <span className="count-invalid">
                    <AlertCircle size={14} /> {invalidCount} invalid
                  </span>
                )}
              </span>
            </h4>
          </div>
          <div className="csv-preview-table-wrapper">
            <table className="csv-preview-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Name</th>
                  <th>Sequence</th>
                  <th>Length</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {sequences.map((s, idx) => (
                  <tr key={idx} className={s.valid ? '' : 'row-invalid'}>
                    <td>{idx + 1}</td>
                    <td>{s.name}</td>
                    <td className="seq-cell">{s.sequence}</td>
                    <td>{s.sequence.length} nt</td>
                    <td>
                      {s.valid ? (
                        <CheckCircle size={16} color="#10b981" />
                      ) : (
                        <AlertCircle size={16} color="#ef4444" />
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

export default CsvUpload;
