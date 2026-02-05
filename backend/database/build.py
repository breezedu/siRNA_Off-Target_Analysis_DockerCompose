"""
Build transcriptome database from FASTA file
Improved version with progress tracking and better error handling
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
    print(f"Organism: {organism}")
    print("")
    
    transcript_count = 0
    seed_count = 0
    skipped_count = 0
    duplicate_count = 0
    
    seen_ids = set()
    
    with get_db_session() as session:
        # Clear existing data
        print("Clearing existing data...")
        session.query(SeedIndex).delete()
        session.query(Transcript).delete()
        session.commit()
        print("✓ Existing data cleared")
        print("")
        
        print("Parsing FASTA file...")
        print("This may take 15-30 minutes for large transcriptomes")
        print("")
        
        try:
            for record_num, record in enumerate(SeqIO.parse(fasta_file_path, "fasta"), 1):
                try:
                    transcript_id = record.id
                    
                    # Check for duplicates
                    if transcript_id in seen_ids:
                        duplicate_count += 1
                        print(f"Warning: Duplicate ID {transcript_id} - skipping")
                        continue
                    
                    seen_ids.add(transcript_id)
                    
                    sequence = str(record.seq).upper().replace('T', 'U')
                    
                    # Skip if sequence is too short
                    if len(sequence) < 50:
                        skipped_count += 1
                        continue
                    
                    # Extract gene symbol from description if available
                    gene_symbol = "Unknown"
                    if record.description:
                        parts = record.description.split()
                        # Try to extract gene symbol from various formats
                        for i, part in enumerate(parts):
                            if part.startswith('gene:') or part.startswith('gene_symbol:'):
                                gene_symbol = part.split(':')[1]
                                break
                            elif i > 0 and i < len(parts) - 1:
                                # Often the gene symbol is after the transcript ID
                                if not part.startswith('chromosome:') and not part.startswith('gene_biotype:'):
                                    if len(part) < 20 and not part.startswith('ENS'):
                                        gene_symbol = part
                                        break
                    
                    # For simplicity, treat entire transcript as potential target
                    # In production, would parse UTR coordinates from GTF/GFF
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
                        print(f"Progress: {transcript_count:,} transcripts, {seed_count:,} seeds indexed...")
                    
                    # More frequent updates for large files
                    if transcript_count % 1000 == 0:
                        session.commit()
                        print(f"✓ Checkpoint: {transcript_count:,} transcripts processed")
                        
                except Exception as e:
                    print(f"Error processing record {record_num} ({transcript_id}): {str(e)}")
                    skipped_count += 1
                    continue
            
            # Final commit
            session.commit()
            
        except Exception as e:
            print(f"Critical error parsing FASTA file: {str(e)}")
            raise
    
    print("")
    print("=" * 60)
    print("Database build complete!")
    print("=" * 60)
    print(f"✓ Transcripts processed: {transcript_count:,}")
    print(f"✓ Seed indices created:  {seed_count:,}")
    if duplicate_count > 0:
        print(f"⚠ Duplicates skipped:    {duplicate_count:,}")
    if skipped_count > 0:
        print(f"⚠ Records skipped:       {skipped_count:,}")
    print("=" * 60)
    
    # Verify database contents
    print("")
    print("Verifying database...")
    with get_db_session() as session:
        db_transcript_count = session.query(Transcript).count()
        db_seed_count = session.query(SeedIndex).count()
        
        print(f"Database contains:")
        print(f"  Transcripts: {db_transcript_count:,}")
        print(f"  Seed indices: {db_seed_count:,}")
        
        if db_transcript_count != transcript_count:
            print(f"⚠️ WARNING: Mismatch in transcript count!")
            print(f"   Expected: {transcript_count}, Got: {db_transcript_count}")
        else:
            print("✓ Verification passed")
    
    return transcript_count, seed_count

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python build.py <fasta_file_path>")
        sys.exit(1)
    
    fasta_file = sys.argv[1]
    build_transcriptome_database(fasta_file)
