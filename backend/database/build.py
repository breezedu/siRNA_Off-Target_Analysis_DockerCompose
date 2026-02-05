"""
Build transcriptome database from FASTA file
"""

from Bio import SeqIO
from database.db import get_db_session
from database.models import Transcript, SeedIndex
import sys

def build_transcriptome_database(fasta_file_path: str, organism: str = "human"):
    """
    Parse transcriptome FASTA and build seed index
    
    Args:
        fasta_file_path: Path to transcriptome FASTA file
        organism: Organism name for metadata
    """
    print(f"Building transcriptome database from {fasta_file_path}")
    
    transcript_count = 0
    seed_count = 0
    
    with get_db_session() as session:
        # Clear existing data
        print("Clearing existing data...")
        session.query(SeedIndex).delete()
        session.query(Transcript).delete()
        session.commit()
        
        print("Parsing FASTA file...")
        for record in SeqIO.parse(fasta_file_path, "fasta"):
            transcript_id = record.id
            sequence = str(record.seq).upper().replace('T', 'U')
            
            # Extract gene symbol from description if available
            # Format: >NM_001301717.2 Homo sapiens BRCA1 DNA repair...
            gene_symbol = "Unknown"
            if record.description:
                parts = record.description.split()
                if len(parts) >= 4:
                    gene_symbol = parts[3]
            
            # For simplicity, assume entire transcript is 3' UTR
            # In production, parse UTR coordinates from GTF/GFF
            utr3_start = 0
            utr3_end = len(sequence)
            
            # Create transcript record
            transcript = Transcript(
                transcript_id=transcript_id,
                gene_symbol=gene_symbol,
                sequence=sequence,
                utr3_start=utr3_start,
                utr3_end=utr3_end,
                length=len(sequence)
            )
            session.add(transcript)
            transcript_count += 1
            
            # Build seed index - extract all 7-mers
            for i in range(len(sequence) - 6):
                seed_7mer = sequence[i:i+7]
                
                # Only index valid seeds (no N's or ambiguous bases)
                if all(base in 'ACGU' for base in seed_7mer):
                    seed_index = SeedIndex(
                        seed_7mer=seed_7mer,
                        transcript_id=transcript_id,
                        position=i
                    )
                    session.add(seed_index)
                    seed_count += 1
            
            # Commit in batches for better performance
            if transcript_count % 100 == 0:
                session.commit()
                print(f"Processed {transcript_count} transcripts, {seed_count} seeds...")
        
        # Final commit
        session.commit()
    
    print(f"Database build complete!")
    print(f"Total transcripts: {transcript_count}")
    print(f"Total seed indices: {seed_count}")
    
    return transcript_count, seed_count

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python build.py <fasta_file_path>")
        sys.exit(1)
    
    fasta_file = sys.argv[1]
    build_transcriptome_database(fasta_file)
