# siRNA_Off-Target_Analysis_DockerCompose
# siRNA Off-Target Analysis Tool - Implementation Specification

## Overview
This tool identifies potential off-target effects of siRNA sequences by performing seed-based matching against transcriptome databases and scoring predicted binding affinities. It prioritizes analysis of the seed region (positions 2-8 from the 5' end of the guide strand) which is critical for target recognition.

## Core Algorithm

### 1. Input Processing
- **Input format**: FASTA or plain text with siRNA sequences (19-23 nt, typically 21 nt)
- **Strand identification**: Accept either guide strand only or duplex (sense/antisense)
- **Validation**: Check sequence composition (only ACGTU allowed), length constraints

### 2. Seed Region Definition
The seed region is the most critical determinant of siRNA specificity:
- **Primary seed**: Nucleotides 2-8 from 5' end of guide strand (7-mer)
- **Extended seed**: Nucleotides 2-7 (6-mer) for relaxed analysis
- **Supplementary pairing**: Positions 13-16 can compensate for seed mismatches

### 3. Transcriptome Database Search

#### Database Requirements
- **Source**: Human transcriptome (or relevant organism)
  - RefSeq mRNA sequences
  - Ensembl transcript sequences
  - Include 3' UTR sequences (primary siRNA target site)
  
#### Search Strategy
1. **Exact seed matching**: 
   - Convert seed region to reverse complement
   - Search for exact 7-mer matches in 3' UTR sequences
   - Use efficient string matching (Boyer-Moore or suffix array)

2. **Mismatch tolerance**:
   - Allow 0-1 mismatches in seed region for comprehensive analysis
   - Wobble pairs (G:U) treated as 0.5 penalty

3. **Extended matching**:
   - For seed matches found, extend alignment to full siRNA length
   - Score complementarity across positions 1-19

### 4. Binding Energy Calculation

Use nearest-neighbor thermodynamic parameters for RNA-RNA duplexes:

#### Free Energy Components
```
ΔG_total = ΔG_duplex + ΔG_seed + ΔG_AU_penalty + ΔG_position
```

**ΔG_duplex**: Sum of nearest-neighbor free energies
- Use Turner 2004 RNA parameters
- Example values (kcal/mol at 37°C):
  - AU/UA: -0.9
  - GC/CG: -2.1 to -2.4
  - GU/UG: -0.5 to -1.4
  - Terminal AU penalty: +0.45
  - Mismatch penalties vary by context

**ΔG_seed**: Enhanced weight for seed region
- Multiply seed region (2-8) contribution by 1.5x

**ΔG_AU_penalty**: 
- Add +0.45 kcal/mol per A or U at siRNA position 1 or 19

**ΔG_position**: Position-dependent weights
- Positions 2-8: weight = 1.5
- Positions 9-12: weight = 1.0
- Positions 13-19: weight = 0.8

#### Scoring Thresholds
- **High confidence off-target**: ΔG < -20 kcal/mol
- **Moderate risk**: -20 to -15 kcal/mol
- **Low risk**: -15 to -10 kcal/mol
- **Negligible**: > -10 kcal/mol

### 5. Context Features Analysis

#### Sequence Context Scoring
For each potential off-target, extract and score:

1. **Local AU content** (±30 nt window):
   - Higher AU content (>60%) increases accessibility
   - Score: +1 if >60%, 0 otherwise

2. **Secondary structure prediction**:
   - Use Vienna RNAfold or similar to predict mRNA structure
   - Calculate probability of target site being unpaired
   - Score: probability × 2 (0-2 range)

3. **Conservation score** (if available):
   - PhastCons or PhyloP scores across species
   - Conserved sites more likely to be functionally important
   - Score: normalized conservation (0-1)

### 6. Off-Target Prioritization

#### Combined Risk Score
```
Risk_score = (1 - ΔG_normalized) × 0.5 + 
             AU_content_score × 0.2 + 
             Structure_accessibility × 0.2 + 
             Conservation_score × 0.1
```

Where ΔG_normalized = (ΔG + 25) / 15, clamped to [0,1]

#### Output Ranking
Sort off-targets by:
1. Risk score (descending)
2. Number of seed matches
3. Gene expression level (if data available)

## Implementation Architecture

### Recommended Tech Stack
- **Language**: Python 3.8+
- **Core libraries**:
  - BioPython (sequence handling)
  - NumPy (calculations)
  - Pandas (data management)
  - ViennaRNA Python bindings (structure prediction)
- **Database**: SQLite for local transcript database

### Module Structure

```
siRNA_offtarget/
├── __init__.py
├── core/
│   ├── sequence.py          # Sequence validation and processing
│   ├── seed_search.py       # Seed region matching algorithms
│   ├── thermodynamics.py    # ΔG calculation engine
│   └── scoring.py           # Risk scoring functions
├── database/
│   ├── transcriptome.py     # Database interface
│   ├── build_db.py          # Database construction scripts
│   └── nearest_neighbor_params.json  # Turner parameters
├── analysis/
│   ├── structure.py         # RNA structure prediction wrapper
│   ├── context.py           # Sequence context analysis
│   └── prioritization.py    # Off-target ranking
├── utils/
│   ├── io.py                # Input/output handlers
│   └── visualization.py     # Results plotting
└── cli.py                   # Command-line interface
```

### Key Functions Pseudocode

#### Seed Search Function
```python
def find_seed_matches(sirna_guide, transcriptome_db, max_mismatches=1):
    """
    Find all seed region matches in transcriptome
    
    Args:
        sirna_guide: 21nt guide strand sequence (string)
        transcriptome_db: Database handle
        max_mismatches: Maximum mismatches allowed in seed
    
    Returns:
        List of (transcript_id, position, seed_sequence) tuples
    """
    seed = sirna_guide[1:8]  # Extract positions 2-8
    seed_rc = reverse_complement(seed)
    
    matches = []
    for transcript in transcriptome_db.get_3utr_sequences():
        # Use regex with mismatches or suffix array
        positions = find_fuzzy_matches(transcript.sequence, seed_rc, max_mismatches)
        for pos in positions:
            matches.append((transcript.id, pos, transcript.sequence[pos:pos+7]))
    
    return matches
```

#### Thermodynamic Scoring
```python
def calculate_binding_energy(sirna_seq, target_seq, nn_params):
    """
    Calculate predicted binding free energy
    
    Args:
        sirna_seq: siRNA guide strand
        target_seq: Target site (reverse complement for pairing)
        nn_params: Nearest neighbor parameters dictionary
    
    Returns:
        Free energy in kcal/mol
    """
    # Ensure sequences are aligned
    assert len(sirna_seq) == len(target_seq)
    
    delta_g = 0.0
    
    # Calculate nearest-neighbor contributions
    for i in range(len(sirna_seq) - 1):
        pair1 = get_base_pair(sirna_seq[i], target_seq[i])
        pair2 = get_base_pair(sirna_seq[i+1], target_seq[i+1])
        
        # Look up dinucleotide pair in parameters
        nn_key = f"{pair1}/{pair2}"
        delta_g += nn_params.get(nn_key, 0.0)
        
        # Apply position-dependent weights
        if 1 <= i <= 7:  # Seed region (0-indexed: 1-7 = positions 2-8)
            delta_g *= 1.5
    
    # Terminal penalties
    if sirna_seq[0] in ['A', 'U'] or sirna_seq[-1] in ['A', 'U']:
        delta_g += 0.45
    
    return delta_g
```

#### Risk Assessment
```python
def assess_offtarget_risk(sirna, offtarget_list, transcriptome_db):
    """
    Compute comprehensive risk scores for all off-targets
    
    Args:
        sirna: siRNA sequence object
        offtarget_list: List of potential off-targets from seed search
        transcriptome_db: Database handle
    
    Returns:
        Pandas DataFrame with scored and ranked off-targets
    """
    results = []
    
    for ot in offtarget_list:
        # Get target sequence context
        target_context = transcriptome_db.get_sequence_window(
            ot.transcript_id, ot.position, window=50
        )
        
        # Calculate thermodynamics
        delta_g = calculate_binding_energy(
            sirna.guide_strand,
            target_context[25:46]  # Center the target site
        )
        
        # Sequence context features
        au_content = calculate_au_content(target_context)
        structure_score = predict_accessibility(target_context, ot.position)
        
        # Combine into risk score
        risk = compute_risk_score(delta_g, au_content, structure_score)
        
        results.append({
            'transcript_id': ot.transcript_id,
            'gene_symbol': transcriptome_db.get_gene_symbol(ot.transcript_id),
            'position': ot.position,
            'delta_g': delta_g,
            'risk_score': risk,
            'seed_matches': count_seed_matches(sirna.seed, target_context[25:32])
        })
    
    df = pd.DataFrame(results)
    return df.sort_values('risk_score', ascending=False)
```

## Database Construction

### Transcriptome Database Schema
```sql
CREATE TABLE transcripts (
    transcript_id TEXT PRIMARY KEY,
    gene_symbol TEXT,
    gene_id TEXT,
    sequence TEXT,
    utr3_start INTEGER,
    utr3_end INTEGER,
    length INTEGER
);

CREATE INDEX idx_gene_symbol ON transcripts(gene_symbol);
CREATE INDEX idx_sequence ON transcripts(sequence);  -- For pattern matching

CREATE TABLE seed_index (
    seed_7mer TEXT,
    transcript_id TEXT,
    position INTEGER,
    FOREIGN KEY(transcript_id) REFERENCES transcripts(transcript_id)
);

CREATE INDEX idx_seed ON seed_index(seed_7mer);
```

### Building the Index
```python
def build_seed_index(transcriptome_fasta, output_db):
    """
    Pre-compute all 7-mer seeds in transcriptome for fast lookup
    """
    conn = sqlite3.connect(output_db)
    
    for record in SeqIO.parse(transcriptome_fasta, 'fasta'):
        transcript_id = record.id
        sequence = str(record.seq)
        
        # Store transcript
        conn.execute(
            "INSERT INTO transcripts VALUES (?, ?, ?)",
            (transcript_id, sequence, len(sequence))
        )
        
        # Index all 7-mers
        for i in range(len(sequence) - 6):
            seed = sequence[i:i+7]
            conn.execute(
                "INSERT INTO seed_index VALUES (?, ?, ?)",
                (seed, transcript_id, i)
            )
    
    conn.commit()
```

## Output Format

### Summary Report
```
siRNA Off-Target Analysis Report
================================
Query siRNA: 5'-GUGAUGUAGCCUAUGACACAA-3'
Seed region: UGAUGUA (positions 2-8)

High-Risk Off-Targets: 12
Moderate-Risk: 45
Low-Risk: 234

Top 10 Off-Targets:
Rank | Gene    | Transcript    | Position | ΔG (kcal/mol) | Risk Score | Seed Matches
-----|---------|---------------|----------|---------------|------------|-------------
1    | BCL2    | NM_000633.2   | 1245     | -22.3         | 0.87       | 7/7
2    | TP53    | NM_000546.5   | 892      | -21.1         | 0.82       | 7/7
3    | MYC     | NM_002467.5   | 2341     | -19.8         | 0.76       | 6/7 (1 G:U)
...
```

### Detailed CSV Output
Columns:
- gene_symbol
- transcript_id
- position
- alignment (visual representation)
- delta_g
- risk_score
- seed_matches
- mismatches
- wobbles
- au_content
- structure_accessibility
- conservation_score

## Validation and Testing

### Test Cases
1. **Perfect seed match**: Should identify known off-target from literature
2. **1-mismatch tolerance**: Should find off-targets with single seed mismatch
3. **Energy threshold**: Verify only ΔG < -10 kcal/mol reported
4. **Performance**: Process 20 siRNAs against human transcriptome in <5 minutes

### Benchmark Dataset
Use published siRNA datasets with validated off-targets:
- Jackson et al. (2006) Nature Biotechnology dataset
- Compare predictions with experimental microarray data

## Optimization Strategies

### Performance Enhancements
1. **Pre-indexed database**: Build comprehensive seed index offline
2. **Parallel processing**: Use multiprocessing for independent siRNA queries
3. **Caching**: Store computed ΔG values for recurring sequence pairs
4. **Filtering**: Early termination for seeds with >2 mismatches

### Memory Efficiency
- Stream large transcriptome files rather than loading entirely
- Use memory-mapped database access
- Batch processing for multiple siRNAs

## Additional Features (Optional Enhancements)

### 1. Position-Specific Scoring
Weight mismatches by position:
- Position 2-4: 2.0× penalty
- Position 5-8: 1.5× penalty
- Position 9-15: 1.0× penalty
- Position 16-21: 0.5× penalty

### 2. Machine Learning Integration
Train classifier on experimental off-target data:
- Features: ΔG, seed matches, position-specific mismatches, AU content, structure
- Model: Gradient boosting or random forest
- Output: Probability of functional off-target effect

### 3. Batch Analysis
Support multiple siRNA candidates:
- Compare off-target profiles
- Identify shared off-targets
- Rank siRNAs by specificity

### 4. Visualization
Generate plots:
- Off-target distribution histogram
- Risk score heatmap across transcriptome
- Position-specific binding energy profile

## References and Resources

### Key Papers
- Jackson et al. (2003) "Expression profiling reveals off-target gene regulation by RNAi"
- Birmingham et al. (2006) "3' UTR seed matches, but not overall identity, are associated with RNAi off-targets"
- Grimson et al. (2007) "MicroRNA targeting specificity in mammals: determinants beyond seed pairing"

### Databases
- **RefSeq**: https://www.ncbi.nlm.nih.gov/refseq/
- **Ensembl**: https://www.ensembl.org/
- **Turner nearest-neighbor parameters**: Available in ViennaRNA package

### Tools for Comparison
- BLAST for sequence similarity
- TargetScan algorithm (microRNA targeting, similar principles)
- ViennaRNA RNAfold for structure prediction

## Example Usage

```python
from sirna_offtarget import SiRNAAnalyzer

# Initialize analyzer with transcriptome database
analyzer = SiRNAAnalyzer('human_transcriptome.db')

# Define siRNA (guide strand)
sirna = "GUGAUGUAGCCUAUGACACAA"

# Run analysis
results = analyzer.analyze(
    sirna,
    max_seed_mismatches=1,
    energy_threshold=-10.0,
    include_structure=True
)

# Get summary
print(results.summary())

# Export detailed results
results.to_csv('offtarget_report.csv')

# Visualize top hits
results.plot_top_offtargets(n=20)
```

---

This specification provides the algorithmic foundation, implementation details, and context needed to build a functional siRNA off-target analysis tool. The key innovations are the seed-centric search strategy, thermodynamic scoring with position-specific weights, and integration of sequence context features for prioritization.
