from backend.pipeline.doc_parser_steps.context import DocParserContext
from backend.pipeline.step import PipelineStep


class DocParserStep(PipelineStep[DocParserContext]):
    """Base class for all document parser pipeline steps"""
    pass
