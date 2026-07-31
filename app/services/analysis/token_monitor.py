# app/services/analysis/token_monitor.py
"""
Monitor de consumo de tokens de la API de Groq.

Lee los headers de rate-limit de cada respuesta y:
- Loguea el consumo
- Emite alertas cuando queda poco saldo
- Permite consultar el estado actual
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any


logger = logging.getLogger(__name__)


@dataclass
class TokenStatus:
    """Estado actual del consumo de tokens."""
    limit_tokens: int = 0
    remaining_tokens: int = 0
    used_tokens: int = 0
    usage_percent: float = 0.0
    reset_seconds: int = 0
    last_request_tokens: int = 0
    
    @property
    def is_critical(self) -> bool:
        """Menos del 5% disponible."""
        return self.remaining_tokens > 0 and self.usage_percent >= 95
    
    @property
    def is_warning(self) -> bool:
        """Menos del 20% disponible."""
        return self.usage_percent >= 80
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "limit_tokens": self.limit_tokens,
            "remaining_tokens": self.remaining_tokens,
            "used_tokens": self.used_tokens,
            "usage_percent": round(self.usage_percent, 2),
            "reset_seconds": self.reset_seconds,
            "last_request_tokens": self.last_request_tokens,
            "status": (
                "critical" if self.is_critical 
                else "warning" if self.is_warning 
                else "ok"
            ),
        }


class TokenMonitor:
    """
    Monitor singleton que trackea el consumo de tokens.
    """
    
    _instance: TokenMonitor | None = None
    
    WARNING_THRESHOLD = 80
    CRITICAL_THRESHOLD = 95
    
    def __init__(self):
        self._status = TokenStatus()
        self._total_requests = 0
        self._total_tokens_consumed = 0
    
    @classmethod
    def get_instance(cls) -> TokenMonitor:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def reset(cls) -> None:
        """Reset para tests."""
        cls._instance = None
    
    def update_from_response(self, response: Any) -> TokenStatus:
        """
        Extrae los headers de rate-limit de la respuesta HTTP de Groq.
        """
        try:
            headers = self._extract_headers(response)
            
            if not headers:
                return self._status
            
            limit = int(headers.get("x-ratelimit-limit-tokens", 0))
            remaining = int(headers.get("x-ratelimit-remaining-tokens", 0))
            reset = int(headers.get("x-ratelimit-reset-tokens", 0))
            
            if limit > 0:
                used = limit - remaining
                usage_percent = (used / limit) * 100
            else:
                used = 0
                usage_percent = 0
            
            last_request = self._estimate_last_request(response)
            
            self._status = TokenStatus(
                limit_tokens=limit,
                remaining_tokens=remaining,
                used_tokens=used,
                usage_percent=usage_percent,
                reset_seconds=reset,
                last_request_tokens=last_request,
            )
            
            self._total_requests += 1
            self._total_tokens_consumed += last_request
            
            self._emit_alerts()
            
            return self._status
            
        except (ValueError, TypeError, AttributeError) as exc:
            logger.debug(f"No se pudieron leer headers de tokens: {exc}")
            return self._status
    
    def get_status(self) -> TokenStatus:
        return self._status
    
    def get_summary(self) -> dict[str, Any]:
        return {
            "current": self._status.to_dict(),
            "session": {
                "total_requests": self._total_requests,
                "total_tokens_consumed": self._total_tokens_consumed,
            },
        }
    
    def _extract_headers(self, response: Any) -> dict:
        """Extrae headers de la respuesta de Groq."""
        if hasattr(response, "headers") and response.headers:
            return response.headers
        if hasattr(response, "http_response") and response.http_response:
            return response.http_response.headers
        return {}
    
    def _estimate_last_request(self, response: Any) -> int:
        """Estima tokens consumidos en la última request."""
        try:
            if hasattr(response, "usage") and response.usage:
                return (
                    getattr(response.usage, "total_tokens", 0) or
                    getattr(response.usage, "prompt_tokens", 0) +
                    getattr(response.usage, "completion_tokens", 0)
                )
        except Exception:
            pass
        return 0
    
    def _emit_alerts(self) -> None:
        """Emite alertas según los umbrales."""
        if self._status.is_critical:
            logger.critical(
                f"🚨 CRÍTICO: Tokens al {self._status.usage_percent:.1f}%. "
                f"Disponibles: {self._status.remaining_tokens}. "
                f"Reset en {self._status.reset_seconds}s."
            )
        elif self._status.is_warning:
            logger.warning(
                f"⚠️  ALERTA: Tokens al {self._status.usage_percent:.1f}%. "
                f"Disponibles: {self._status.remaining_tokens}."
            )
        else:
            logger.info(
                f"✓ Tokens: {self._status.usage_percent:.1f}% usado. "
                f"Disponibles: {self._status.remaining_tokens}."
            )