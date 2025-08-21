# app/llm/base.py
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, Any, Iterable


class BaseLLM(ABC):
    """
    A minimal contract every provider must satisfy.
    """

    @abstractmethod
    async def chat(
        self, messages: Iterable[Dict[str, str]], **kwargs: Any
    ) -> str:
        ...

    @abstractmethod
    async def stream(
        self, messages: Iterable[Dict[str, str]], **kwargs: Any
    ) -> AsyncGenerator[str, None]:
        ...
