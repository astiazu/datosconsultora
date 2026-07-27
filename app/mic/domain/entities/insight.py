from dataclasses import dataclass

from app.mic.domain.enums import InsightType


@dataclass(slots=True)
class Insight:

    insight_type: InsightType

    title: str

    description: str

    confidence: float