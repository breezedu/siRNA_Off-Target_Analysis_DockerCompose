"""
Core siRNA Off-Target Analyzer - FIXED VERSION
Implements seed-based search and thermodynamic scoring with correct strand handling
"""

from typing import List, Dict, Tuple
import numpy as np
from Bio.Seq import Seq
from database.db import get_db_session
from database.models import Transcript, SeedIndex
import json

class SiRNAAnalyzer:
    def __init__(self):
        """Initialize the analyzer with nearest-neighbor parameters"""
        self.nn_params = self._load_nn_parameters()
        
    def _load_nn_parameters(self) -> Dict:
        """
        Load Turner nearest-neighbor thermodynamic parameters
        Values in kcal/mol at 37°C
        """
        return {
            # Watson-Crick pairs
            'AA/UU': -0.9, 'AU/UA': -1.1, 'UA/AU': -1.3, 'UU/AA': -0.9,
            'GA/UC': -2.1, 'GU/CA': -2.1, 'CG/GC': -2.4, 'GC/CG': -2.1,
            'CA/GU': -2.1, 'UC/GA': -2.1, 'CU/GA': -2.1, 'AG/CU': -2.1,
            'GG/CC': -3.3, 'CC/GG': -3.3,
            
            # G:U wobble pairs
            'GU/UG': -1.4, 'UG/GU': -1.4,
            'GU/AU': -1.3, 'UG/UA': -1.0,
            
            # Terminal penalties
            'terminal_AU': 0.45,
            'terminal_GC': 0.0,
            
            # Position weights
            'seed_weight': 1.5,      # Positions 2-8
            'central_weight': 1.0,   # Positions 9-12
            'supplementary_weight': 0.8  # Positions 13-19
        }
    
    def analyze(
        self,
        sirna_sequence: str,
        max_seed_mismatches: int = 1,
        energy_threshold: float = -10.0,
        include_structure: bool = True
    ) -> List[Dict]:
        """
        Main analysis pipeline
        
        Args:
            sirna_sequence: Guide strand sequence (19-23 nt)
            max_seed_mismatches: Maximum mismatches in seed region
            energy_threshold: Minimum binding energy to report (kcal/mol)
            include_structure: Calculate RNA structure accessibility
            
        Returns:
            List of off-target predictions with scores
        """
        # Validate and normalize sequence
        sirna_sequence = sirna_sequence.upper().replace('T', 'U')
        
        if not self._validate_sequence(sirna_sequence):
            raise ValueError("Invalid siRNA sequence")
        
        # Extract seed region (positions 2-8, 0-indexed: 1-7)
        seed = sirna_sequence[1:8]
        
        # Find seed matches in transcriptome
        seed_matches = self._find_seed_matches(seed, max_seed_mismatches)
        
        print(f"Found {len(seed_matches)} seed matches for seed: {seed}")
        
        # Score each potential off-target
        offtargets = []
        for match in seed_matches:
            try:
                score = self._score_offtarget(
                    sirna_sequence,
                    match,
                    max_seed_mismatches,
                    include_structure
                )
                
                # Filter by seed match quality BEFORE checking energy
                seed_match_parts = score['seed_matches'].split('/')
                seed_match_count = int(seed_match_parts[0])
                seed_length = int(seed_match_parts[1])
                
                # Only include if seed matches are within threshold
                if seed_match_count >= (seed_length - max_seed_mismatches):
                    if score['delta_g'] <= energy_threshold:
                        offtargets.append(score)
                else:
                    print(f"Filtered out match at {match['transcript_id']}:{match['position']} - seed matches {seed_match_count}/{seed_length} below threshold")
                    
            except Exception as e:
                # Skip matches that cause errors (e.g., sequence too short)
                print(f"Warning: Skipping match at {match['transcript_id']}:{match['position']} - {str(e)}")
                continue
        
        # Sort by risk score
        offtargets.sort(key=lambda x: x['risk_score'], reverse=True)
        
        return offtargets
    
    def _validate_sequence(self, sequence: str) -> bool:
        """Validate siRNA sequence format"""
        if len(sequence) < 19 or len(sequence) > 23:
            return False
        if not all(c in 'ACGU' for c in sequence):
            return False
        return True
    
    def _find_seed_matches(
        self,
        seed: str,
        max_mismatches: int
    ) -> List[Dict]:
        """
        Search transcriptome database for seed matches
        
        The seed index stores the FORWARD STRAND sequence.
        We need to search for the reverse complement of our siRNA seed.
        
        Returns list of matches with transcript info and position
        """
        # Get reverse complement for target search
        # siRNA binds antiparallel, so we search for RC in the transcriptome
        seed_rc = str(Seq(seed).reverse_complement())
        
        print(f"Searching for seed RC: {seed_rc}")
        
        matches = []
        
        with get_db_session() as session:
            # For now, only exact matches (fuzzy matching TODO)
            if max_mismatches == 0:
                # Exact match only
                results = session.query(SeedIndex).filter(
                    SeedIndex.seed_7mer == seed_rc
                ).all()
            else:
                # For max_mismatches > 0, we need to implement fuzzy matching
                # For now, still using exact match but will filter later by alignment
                results = session.query(SeedIndex).filter(
                    SeedIndex.seed_7mer == seed_rc
                ).all()
                
                # TODO: Implement proper fuzzy seed matching with:
                # - Hamming distance calculation
                # - Position-weighted mismatches (5' end more important)
            
            print(f"Found {len(results)} seed index matches")
            
            for result in results:
                # Get full transcript
                transcript = session.query(Transcript).filter(
                    Transcript.transcript_id == result.transcript_id
                ).first()
                
                if transcript:
                    matches.append({
                        'transcript_id': transcript.transcript_id,
                        'gene_symbol': transcript.gene_symbol,
                        'position': result.position,
                        'sequence': transcript.sequence,
                        'utr3_start': transcript.utr3_start,
                        'utr3_end': transcript.utr3_end
                    })
        
        return matches
    
    def _score_offtarget(
        self,
        sirna_sequence: str,
        match: Dict,
        max_seed_mismatches: int,
        include_structure: bool
    ) -> Dict:
        """
        Calculate comprehensive off-target score with CORRECT STRAND HANDLING
        
        KEY CONCEPT:
        - siRNA (5' to 3'): GCCACUGCGCCCGGCCCCC
        - Target in transcript (5' to 3'): GCAGUGGCUUGGCGCAGGUUA
        - For antiparallel binding, we align siRNA 5'->3' with target 3'->5'
        - So we need the REVERSE (not RC) of the target for proper alignment
        
        Combines:
        - Thermodynamic binding energy
        - Position-specific weights
        - Sequence context
        - Structure accessibility (optional)
        """
        position = match['position']
        full_sequence = match['sequence']
        sirna_len = len(sirna_sequence)
        
        # Extract target site - get enough sequence for the full siRNA length
        target_start = position
        target_end = min(position + sirna_len, len(full_sequence))
        
        available_length = target_end - target_start
        
        # Require at least 80% of siRNA length to be alignable
        min_required_length = int(sirna_len * 0.8)
        
        if available_length < min_required_length:
            raise ValueError(
                f"Target sequence too short for meaningful alignment: "
                f"only {available_length}/{sirna_len} nt available "
                f"(need at least {min_required_length})"
            )
        
        if available_length < 7:  # Absolute minimum: need at least seed region
            raise ValueError(f"Target sequence too short: {available_length} nt")
        
        # Extract the target sequence from the transcript (5' to 3')
        target_forward = full_sequence[target_start:target_end]
        
        print(f"\nAnalyzing match at {match['transcript_id']}:{position}")
        print(f"siRNA (5'->3'):      {sirna_sequence}")
        print(f"Target fwd (5'->3'): {target_forward}")
        
        # For antiparallel binding:
        # siRNA 5'->3' pairs with target 3'->5'
        # So we reverse (not reverse complement) the target
        target_reversed = target_forward[::-1]
        
        print(f"Target rev (3'->5'): {target_reversed}")
        
        # Now align them for complementarity checking
        # We need to compare if they are complementary (Watson-Crick pairing)
        min_len = min(len(sirna_sequence), len(target_reversed))
        sirna_trimmed = sirna_sequence[:min_len]
        target_trimmed = target_reversed[:min_len]
        
        # Track alignment coverage
        alignment_coverage = min_len / len(sirna_sequence)
        
        print(f"Alignment coverage: {min_len}/{len(sirna_sequence)} nt ({alignment_coverage*100:.1f}%)")
        
        # Calculate binding energy with proper pairing
        delta_g = self._calculate_binding_energy(sirna_trimmed, target_trimmed)
        
        # Count mismatches (non-complementary positions)
        mismatches = sum(
            1 for i in range(min_len)
            if not self._is_complementary(sirna_trimmed[i], target_trimmed[i])
        )
        
        print(f"Mismatches: {mismatches}/{min_len}")
        
        # Seed match quality (positions 2-8 in siRNA, indices 1-7)
        seed_start = 1
        seed_end = min(8, min_len)
        seed_sirna = sirna_trimmed[seed_start:seed_end]
        seed_target = target_trimmed[seed_start:seed_end]
        
        seed_matches = sum(
            1 for i in range(len(seed_sirna))
            if self._is_complementary(seed_sirna[i], seed_target[i])
        )
        seed_matches_str = f"{seed_matches}/{len(seed_sirna)}"
        
        print(f"Seed matches: {seed_matches_str}")
        
        # Context features
        context_start = max(0, position - 30)
        context_end = min(len(full_sequence), position + 51)
        context_seq = full_sequence[context_start:context_end]
        au_content = self._calculate_au_content(context_seq)
        
        # Structure accessibility (simplified)
        structure_score = 0.5  # Default neutral
        if include_structure:
            structure_score = self._predict_accessibility(context_seq, 30)
        
        # Combined risk score
        risk_score = self._calculate_risk_score(
            delta_g, au_content, structure_score, seed_matches, len(seed_sirna)
        )
        
        # Create alignment string
        alignment = self._format_alignment(sirna_trimmed, target_trimmed)
        
        return {
            'gene_symbol': match['gene_symbol'],
            'transcript_id': match['transcript_id'],
            'position': position,
            'delta_g': round(delta_g, 2),
            'risk_score': round(risk_score, 3),
            'seed_matches': seed_matches_str,
            'mismatches': mismatches,
            'alignment_coverage': f"{min_len}/{len(sirna_sequence)}",
            'alignment': alignment,
            'au_content': round(au_content, 2),
            'structure_accessibility': round(structure_score, 2)
        }
    
    def _is_complementary(self, base1: str, base2: str) -> bool:
        """
        Check if two bases are complementary in RNA
        base1 from siRNA (5'->3'), base2 from target (3'->5')
        
        Watson-Crick pairs: A-U, U-A, G-C, C-G
        Wobble pairs: G-U, U-G
        """
        complement_pairs = {
            ('A', 'U'), ('U', 'A'),
            ('G', 'C'), ('C', 'G'),
            ('G', 'U'), ('U', 'G')
        }
        return (base1, base2) in complement_pairs
    
    def _calculate_binding_energy(self, sirna: str, target: str) -> float:
        """
        Calculate nearest-neighbor binding free energy
        
        Args:
            sirna: siRNA sequence 5'->3'
            target: target sequence 3'->5' (reversed from transcript)
        """
        if len(sirna) != len(target):
            raise ValueError(f"Sequences must be same length: {len(sirna)} vs {len(target)}")
        
        delta_g = 0.0
        
        # Nearest-neighbor contributions
        for i in range(len(sirna) - 1):
            # Get the base pairs
            sirna_pair = sirna[i:i+2]
            target_pair = target[i:i+2]
            
            # Check if bases are complementary
            if not (self._is_complementary(sirna[i], target[i]) and 
                    self._is_complementary(sirna[i+1], target[i+1])):
                # Non-Watson-Crick pairing - skip or penalize
                continue
            
            # Build nearest-neighbor key
            # Format: "AB/CD" where A-C and B-D are pairs
            nn_key = f"{sirna_pair}/{target_pair}"
            
            # Look up in parameters
            nn_energy = self.nn_params.get(nn_key, 0.0)
            
            # Apply position-specific weights
            if 1 <= i <= 7:  # Seed region (positions 2-8)
                nn_energy *= self.nn_params['seed_weight']
            elif 8 <= i <= 12:  # Central
                nn_energy *= self.nn_params['central_weight']
            else:  # Supplementary
                nn_energy *= self.nn_params['supplementary_weight']
            
            delta_g += nn_energy
        
        # Terminal AU penalty
        if len(sirna) > 0 and len(target) > 0:
            if sirna[0] in ['A', 'U'] or sirna[-1] in ['A', 'U']:
                delta_g += self.nn_params['terminal_AU']
        
        return delta_g
    
    def _is_watson_crick(self, base1: str, base2: str) -> bool:
        """Legacy method - redirects to _is_complementary"""
        return self._is_complementary(base1, base2)
    
    def _count_seed_matches(self, seed_sirna: str, seed_target: str) -> str:
        """Count matching positions in seed region"""
        min_len = min(len(seed_sirna), len(seed_target))
        
        matches = sum(
            1 for i in range(min_len)
            if self._is_complementary(seed_sirna[i], seed_target[i])
        )
        return f"{matches}/{min_len}"
    
    def _calculate_au_content(self, sequence: str) -> float:
        """Calculate A+U content percentage"""
        if not sequence:
            return 0.0
        au_count = sum(1 for base in sequence.upper() if base in ['A', 'U', 'T'])
        return (au_count / len(sequence)) * 100
    
    def _predict_accessibility(self, sequence: str, target_pos: int) -> float:
        """
        Predict target site accessibility
        Simplified version - returns normalized score
        """
        # In full implementation, would use ViennaRNA
        # For now, use AU content as proxy
        au_content = self._calculate_au_content(sequence)
        return min(au_content / 100, 1.0)
    
    def _calculate_risk_score(
        self,
        delta_g: float,
        au_content: float,
        structure_score: float,
        seed_matches: int,
        seed_length: int
    ) -> float:
        """
        Combined risk score (0-1 scale)
        Higher score = higher off-target risk
        
        Enhanced with seed match quality
        """
        # Normalize delta_g (-25 to 0 range)
        dg_normalized = max(0, min(1, (delta_g + 25) / 25))
        
        # AU content contribution (normalized)
        au_score = au_content / 100
        
        # Seed match quality (perfect seed = higher risk)
        seed_quality = seed_matches / seed_length if seed_length > 0 else 0
        
        # Weighted combination - seed quality is most important
        risk = (
            (1 - dg_normalized) * 0.3 +  # Lower (more negative) ΔG = higher risk
            au_score * 0.1 +
            structure_score * 0.2 +
            seed_quality * 0.4  # Seed match quality is key predictor
        )
        
        return min(1.0, risk)
    
    def _format_alignment(self, sirna: str, target: str) -> str:
        """
        Create visual alignment string showing complementarity
        
        Args:
            sirna: siRNA sequence 5'->3'
            target: target sequence 3'->5' (already reversed)
        """
        min_len = min(len(sirna), len(target))
        match_line = ""
        
        for i in range(min_len):
            if self._is_complementary(sirna[i], target[i]):
                match_line += ":"  # Use : for Watson-Crick pairs
            else:
                match_line += " "  # Space for mismatch
        
        # Format with proper directionality
        alignment = f"siRNA:  5'-{sirna}-3'\n"
        alignment += f"           {match_line}\n"
        alignment += f"Target: 3'-{target}-5'"
        
        return alignment
