import React, { useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';

function ResultsDisplay({ offtargets, sirnaName }) {
  const [sortBy, setSortBy] = useState('risk_score');
  const [sortOrder, setSortOrder] = useState('desc');
  const [filterRisk, setFilterRisk] = useState('all');

  // Filter and sort
  let filtered = [...offtargets];
  
  if (filterRisk !== 'all') {
    filtered = filtered.filter(ot => {
      if (filterRisk === 'high') return ot.risk_score > 0.7;
      if (filterRisk === 'moderate') return ot.risk_score >= 0.5 && ot.risk_score <= 0.7;
      if (filterRisk === 'low') return ot.risk_score < 0.5;
      return true;
    });
  }

  filtered.sort((a, b) => {
    const aVal = a[sortBy];
    const bVal = b[sortBy];
    return sortOrder === 'desc' ? bVal - aVal : aVal - bVal;
  });

  const handleSort = (column) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc');
    } else {
      setSortBy(column);
      setSortOrder('desc');
    }
  };

  const getRiskColor = (score) => {
    if (score > 0.7) return '#ef4444';
    if (score >= 0.5) return '#f59e0b';
    return '#10b981';
  };

  const getRiskLabel = (score) => {
    if (score > 0.7) return 'High';
    if (score >= 0.5) return 'Moderate';
    return 'Low';
  };

  // Chart data
  const chartData = offtargets.slice(0, 20).map((ot, idx) => ({
    name: ot.gene_symbol,
    risk: ot.risk_score,
    energy: Math.abs(ot.delta_g)
  }));

  return (
    <div className="results-display">
      <div className="chart-section">
        <h3>Top 20 Off-Targets by Risk Score</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" angle={-45} textAnchor="end" height={100} />
            <YAxis label={{ value: 'Risk Score', angle: -90, position: 'insideLeft' }} />
            <Tooltip />
            <Bar dataKey="risk" fill="#8884d8">
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={getRiskColor(entry.risk)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="table-controls">
        <div className="filter-group">
          <label>Filter by Risk:</label>
          <select value={filterRisk} onChange={(e) => setFilterRisk(e.target.value)} className="form-select">
            <option value="all">All ({offtargets.length})</option>
            <option value="high">High Risk</option>
            <option value="moderate">Moderate Risk</option>
            <option value="low">Low Risk</option>
          </select>
        </div>
        <div className="showing-count">
          Showing {filtered.length} of {offtargets.length} off-targets
        </div>
      </div>

      <div className="table-container">
        <table className="results-table">
          <thead>
            <tr>
              <th>Rank</th>
              <th onClick={() => handleSort('gene_symbol')} className="sortable">
                Gene {sortBy === 'gene_symbol' && (sortOrder === 'desc' ? '↓' : '↑')}
              </th>
              <th>Transcript ID</th>
              <th onClick={() => handleSort('position')} className="sortable">
                Position {sortBy === 'position' && (sortOrder === 'desc' ? '↓' : '↑')}
              </th>
              <th onClick={() => handleSort('delta_g')} className="sortable">
                ΔG (kcal/mol) {sortBy === 'delta_g' && (sortOrder === 'desc' ? '↓' : '↑')}
              </th>
              <th onClick={() => handleSort('risk_score')} className="sortable">
                Risk Score {sortBy === 'risk_score' && (sortOrder === 'desc' ? '↓' : '↑')}
              </th>
              <th>Seed Matches</th>
              <th>Mismatches</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((ot, idx) => (
              <tr key={idx}>
                <td>{idx + 1}</td>
                <td className="gene-cell">
                  <strong>{ot.gene_symbol}</strong>
                </td>
                <td className="transcript-cell">{ot.transcript_id}</td>
                <td>{ot.position}</td>
                <td className="energy-cell">{ot.delta_g}</td>
                <td>
                  <div className="risk-badge" style={{ backgroundColor: getRiskColor(ot.risk_score) }}>
                    {ot.risk_score.toFixed(3)}
                    <span className="risk-label">{getRiskLabel(ot.risk_score)}</span>
                  </div>
                </td>
                <td>{ot.seed_matches}</td>
                <td>{ot.mismatches}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default ResultsDisplay;
