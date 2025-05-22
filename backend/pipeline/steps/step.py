from backend.pipeline.context import PDFContext
from abc import ABC, abstractmethod


class PipelineStep(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def run(self, ctx: PDFContext) -> PDFContext:
        pass

    def get_pipeline_name(self):
        return self.name
