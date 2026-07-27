# app/mic/adapters/base_adapter.py
from abc import ABC
from abc import abstractmethod

from app.mic.domain.entities.conversation import Conversation


class BaseAdapter(ABC):

    """
    Contrato para todos los adaptadores.
    """

    @abstractmethod
    def convert(self, data) -> Conversation:
        pass