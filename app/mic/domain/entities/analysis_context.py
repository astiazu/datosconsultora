from dataclasses import dataclass


@dataclass(slots=True)
class AnalysisContext:

    language: str = "es"

    country: str = "AR"

    domain: str = "general"

    client: str = ""

    campaign: str = ""

    model: str = ""

    model_version: str = ""