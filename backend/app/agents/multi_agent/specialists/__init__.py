"""
HospitalOps AI — Domain Specialist Agents Package (Milestone 5, Chunk 5.6.2).

Exports:
- BaseSpecialist: Abstract base contract for all domain specialists.
- ForecastingSpecialist: Admissions and ICU capacity projections.
- SimulationSpecialist: What-if surge scenarios and bottleneck evaluations.
- OptimizationSpecialist: MILP resource allocation and constraint trade-offs.
- KnowledgeSpecialist: Hospital operational policy and SOP retrieval.
"""

from app.agents.multi_agent.specialists.base import BaseSpecialist
from app.agents.multi_agent.specialists.forecasting import ForecastingSpecialist
from app.agents.multi_agent.specialists.knowledge import KnowledgeSpecialist
from app.agents.multi_agent.specialists.optimization import OptimizationSpecialist
from app.agents.multi_agent.specialists.simulation import SimulationSpecialist

__all__ = [
    "BaseSpecialist",
    "ForecastingSpecialist",
    "SimulationSpecialist",
    "OptimizationSpecialist",
    "KnowledgeSpecialist",
]
