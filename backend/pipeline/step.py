# backend/pipeline/step.py
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Optional

# Define a type variable for the context
TContext = TypeVar('TContext')


class PipelineStep(ABC, Generic[TContext]):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def run(self, ctx: TContext, job_id: Optional[str] = None) -> TContext:
        pass

    def get_pipeline_name(self) -> str:
        return self.name
