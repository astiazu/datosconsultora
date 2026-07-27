from abc import ABC, abstractmethod

from app.mic.pipeline.context import PipelineContext


class PipelineStep(ABC):

    """
    Clase base para todos los pasos del pipeline.
    """

    name = "Unnamed Step"

    @abstractmethod
    def execute(self, context: PipelineContext):

        pass