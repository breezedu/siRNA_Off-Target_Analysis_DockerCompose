"""
Database models for transcriptome and seed index
"""

from sqlalchemy import Column, Integer, String, Text, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class Transcript(Base):
    """Transcriptome sequences"""
    __tablename__ = 'transcripts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    transcript_id = Column(String(50), unique=True, nullable=False, index=True)
    gene_symbol = Column(String(50), index=True)
    gene_id = Column(String(50))
    sequence = Column(Text, nullable=False)
    utr3_start = Column(Integer)
    utr3_end = Column(Integer)
    length = Column(Integer)
    
    # Relationship
    seed_indices = relationship("SeedIndex", back_populates="transcript")
    
    def __repr__(self):
        return f"<Transcript {self.transcript_id} ({self.gene_symbol})>"


class SeedIndex(Base):
    """Pre-computed seed region index for fast lookup"""
    __tablename__ = 'seed_index'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    seed_7mer = Column(String(7), nullable=False, index=True)
    transcript_id = Column(String(50), ForeignKey('transcripts.transcript_id'), nullable=False)
    position = Column(Integer, nullable=False)
    
    # Relationship
    transcript = relationship("Transcript", back_populates="seed_indices")
    
    # Composite index for faster queries
    __table_args__ = (
        Index('idx_seed_transcript', 'seed_7mer', 'transcript_id'),
    )
    
    def __repr__(self):
        return f"<SeedIndex {self.seed_7mer} @ {self.transcript_id}:{self.position}>"


class AnalysisJob(Base):
    """Track analysis jobs"""
    __tablename__ = 'analysis_jobs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(36), unique=True, nullable=False, index=True)
    sirna_name = Column(String(100))
    sirna_sequence = Column(String(25))
    status = Column(String(20))  # pending, processing, completed, failed
    created_at = Column(String(50))
    completed_at = Column(String(50))
    result_summary = Column(Text)  # JSON summary
    
    def __repr__(self):
        return f"<AnalysisJob {self.job_id} - {self.status}>"
