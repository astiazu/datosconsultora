# app/mic/providers/registry.py
from __future__ import annotations

import logging
import os
from typing import Optional

from app.mic.providers.base import LLMProvider
from app.mic.providers.groq_provider import GroqProvider
from app.mic.providers.model_config import (
    AVAILABLE_MODELS,
    DEFAULT_MODEL,
    FALLBACK_CHAINS,
    ModelConfig,
    PLAN_MODEL_MAP,
    ProviderType,
)

logger = logging.getLogger(__name__)


class ProviderRegistry:
    """
    Registry que crea y gestiona proveedores LLM con fallback automático.
    """
    
    @classmethod
    def get_provider(
        cls,
        explicit_model: Optional[str] = None,
        user_plan: Optional[str] = None,
        used_models: Optional[list[str]] = None,
    ) -> LLMProvider:
        """
        Obtiene el proveedor, con fallback automático si el modelo falla.
        
        Args:
            explicit_model: Modelo explícito (si se pasa)
            user_plan: Plan del usuario
            used_models: Lista de modelos ya intentados (para evitar loops)
        """
        if used_models is None:
            used_models = []
        
        model_config = cls.select_model(
            explicit_model=explicit_model,
            user_plan=user_plan,
        )
        
        # Si este modelo ya fue intentado, buscar fallback
        if model_config.id in used_models:
            fallback_model = cls._get_next_fallback(model_config.id, used_models)
            if fallback_model:
                logger.warning(
                    f"Modelo {model_config.id} ya fue intentado. "
                    f"Usando fallback: {fallback_model.id}"
                )
                model_config = fallback_model
            else:
                raise ValueError(
                    f"No hay modelos alternativos disponibles. "
                    f"Intentados: {used_models}"
                )
        
        return cls._create_provider(model_config)
    
    @classmethod
    def _get_next_fallback(
        cls, 
        current_model: str, 
        used_models: list[str]
    ) -> Optional[ModelConfig]:
        """Obtiene el siguiente modelo de fallback que no haya sido usado."""
        fallbacks = FALLBACK_CHAINS.get(current_model, [])
        
        for fallback_id in fallbacks:
            if fallback_id not in used_models and fallback_id in AVAILABLE_MODELS:
                return AVAILABLE_MODELS[fallback_id]
        
        return None
    
    @classmethod
    def select_model(
        cls,
        explicit_model: Optional[str] = None,
        user_plan: Optional[str] = None,
    ) -> ModelConfig:
        """Selecciona el modelo según las reglas de prioridad."""
        
        # 1. Modelo explícito
        if explicit_model and explicit_model in AVAILABLE_MODELS:
            logger.info(f"Usando modelo explícito: {explicit_model}")
            return AVAILABLE_MODELS[explicit_model]
        
        # 2. Variable de entorno
        env_model = os.environ.get("GROQ_MODEL")
        if env_model and env_model in AVAILABLE_MODELS:
            logger.info(f"Usando modelo desde env: {env_model}")
            return AVAILABLE_MODELS[env_model]
        
        # 3. Según plan del usuario
        if user_plan:
            plan_lower = user_plan.lower()
            model_id = PLAN_MODEL_MAP.get(plan_lower)
            if model_id and model_id in AVAILABLE_MODELS:
                logger.info(
                    f"Usando modelo para plan '{plan_lower}': {model_id}"
                )
                return AVAILABLE_MODELS[model_id]
        
        # 4. Default
        logger.info(f"Usando modelo default: {DEFAULT_MODEL}")
        return AVAILABLE_MODELS[DEFAULT_MODEL]
    
    @classmethod
    def _create_provider(cls, model_config: ModelConfig) -> LLMProvider:
        """Crea el proveedor según el tipo."""
        
        if model_config.provider == ProviderType.GROQ:
            return GroqProvider(model=model_config.id)
        
        raise ValueError(
            f"Proveedor '{model_config.provider}' no soportado."
        )
    
    @classmethod
    def list_available_models(cls) -> list[ModelConfig]:
        """Lista todos los modelos disponibles."""
        return list(AVAILABLE_MODELS.values())
    
    @classmethod
    def get_model(cls, model_id: str) -> ModelConfig:
        """Obtiene la configuración de un modelo específico."""
        if model_id not in AVAILABLE_MODELS:
            raise ValueError(
                f"Modelo '{model_id}' no disponible. "
                f"Disponibles: {list(AVAILABLE_MODELS.keys())}"
            )
        return AVAILABLE_MODELS[model_id]