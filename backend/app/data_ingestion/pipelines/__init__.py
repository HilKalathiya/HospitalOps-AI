"""
HospitalOps AI — Data Ingestion Pipelines.
"""

from app.data_ingestion.pipelines.base import BaseIngestionPipeline
from app.data_ingestion.pipelines.hero_dmc import HeroDMCIngestionPipeline
from app.data_ingestion.pipelines.mimic_iv import MIMICIVIngestionPipeline
from app.data_ingestion.pipelines.nhsn_hrd import NHSNHRDIngestionPipeline

__all__ = [
    "BaseIngestionPipeline",
    "HeroDMCIngestionPipeline",
    "MIMICIVIngestionPipeline",
    "NHSNHRDIngestionPipeline",
]
