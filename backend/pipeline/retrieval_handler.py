
import logging
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from vidavox.core import RAG_Engine
import asyncio
import uuid
from vidavox.document import ProcessingConfig
from utils.formatter import CustomResultFormatter
from vidavox.core import BaseResultFormatter
from settings import RAG_STATE

from dataclasses import dataclass, asdict
from starlette.concurrency import run_in_threadpool


@dataclass
class DocItem:
    path: str          # full file system path
    db_id: str | None  # UUID we got back from upload_files


logger = logging.getLogger(__name__)


class RetrievalHandler:
    def __init__(self, embedding_model: str = "Snowflake/snowflake-arctic-embed-l-v2.0",
                 use_async: bool = False,
                 state_path: Path = RAG_STATE):
        self.embedding_model = embedding_model
        self.use_async = use_async
        self.state_path: Path = state_path          # stem only

        self._snapshot_path: Path = (
            state_path.parent / f"{state_path.name}_state.pkl"
        )
        self.rag_engine: RAG_Engine | None = None
        self._lock = asyncio.Lock()

    async def initialize(self) -> RAG_Engine:
        """Create engine once, then either load an existing snapshot or start empty."""
        if self.rag_engine:                # already initialised in this process
            return self.rag_engine

        logger.info("Booting RAG engine (embedder=%s)…", self.embedding_model)
        self.rag_engine = RAG_Engine(
            embedding_model=self.embedding_model,
            use_async=False
        )

        snap = self.state_path.parent / f"{self.state_path.name}_state.pkl"
        if snap.exists():
            try:
                ok = await run_in_threadpool(lambda: self.rag_engine.load_state(str(self.state_path)))
                logger.info("Loaded snapshot %s (success=%s)", snap.name, ok)
            except Exception:
                logger.error("Failed to load snapshot…")

        # if snap.exists():
        #     ok = await run_in_threadpool(self._init_sync, self.state_path)
        #     # ok = self.rag_engine.load_state(str(self.state_path))
        #     logger.info("Loaded snapshot %s (ok=%s)", snap.name, ok)
        else:
            logger.warning("No previous snapshot found, starting fresh")
        return self.rag_engine

    def _init_sync(self, path):
        return self.rag_engine.load_state(str(path))

        # ――――― public helper ―――――――――――――――――――――――――――――――――――――――――

    @property
    def current_state_path(self) -> Path:
        """
        Absolute path of the *latest* <stem>_state.pkl on disk.
        Always updated after every save in `_save_state()`.
        """
        return self._snapshot_path

    async def shutdown(self):
        """Persist in-memory state before the process exits."""
        await self._save_state()

    async def add_documents_from_paths(self, docs: list[DocItem], chunk_size: int = 5000, chunk_overlap: int = 100, user_id: str = "User A") -> None:
        """
        Add documents to the RAG engine from file paths.

        Args:
            file_paths: List of file paths to add
            chunk_size: Size of document chunks
            chunk_overlap: Overlap between chunks
        """

        async with self._lock:

            logger.info("Ingesting %d docs for %s", len(docs), user_id)
            await run_in_threadpool(self._ingest_sync, docs, user_id)
            # self.rag_engine.from_paths(
            #     sources=docs,
            #     config=ProcessingConfig(
            #         chunk_size=chunk_size, chunk_overlap=chunk_overlap),
            #     user_id=user_id
            # )
            await self._save_state()

    def _ingest_sync(self, docs, user_id):
        self.rag_engine.from_paths(
            sources=docs,
            config=ProcessingConfig(chunk_size=5000, chunk_overlap=100),
            user_id=user_id
        )

    async def add_documents_from_directory(self, directory_path: str, chunk_size: int = 5000, chunk_overlap: int = 100, user_id: str = "User A") -> None:
        """
        Add documents to the RAG engine from a directory.

        Args:
            directory_path: Path to directory containing documents
            chunk_size: Size of document chunks
            chunk_overlap: Overlap between chunks
        """
        async with self._lock:
            logger.info("Ingesting docs from %s", directory_path)
            self.rag_engine.from_directory(
                directory_path,
                show_progress=True,
                config=ProcessingConfig(
                    chunk_size=chunk_size, chunk_overlap=chunk_overlap),
                user_id=user_id
            )
            await self._save_state()

    async def delete_document(self, doc_id: str, user_id: str):
        async with self._lock:
            deleted = self.rag_engine.delete_document(doc_id, user_id=user_id)
            logger.info(f"doc_id: {doc_id} and  user_id: {user_id}")
            if deleted:
                logger.info("Deleted %s for %s", doc_id, user_id)
                await self._save_state()
            return deleted

    def get_document_content(self, user_id: str = "User A") -> Dict[str, str]:
        """Get content dictionary of all documents."""
        return self.rag_engine.doc_manager.get_all_just_added_documents(user_id=user_id)

    def retrieve_relevant_documents(self, query: str, threshold: float = 0.2, prefixes: str = None, include_doc_ids: List[str] = None, exclude_doc_ids: List[str] = None, user_id: str = "User A") -> List[Dict[str, Any]]:
        """
        Retrieve relevant document chunks for a query.

        Args:
            query: Search query
            threshold: Similarity threshold

        Returns:
            List of document chunks with metadata
        """

        return self.rag_engine.retrieve_best_chunk_per_document(
            query,
            threshold=threshold,
            result_formatter=CustomResultFormatter(),
            prefixes=prefixes,
            include_doc_ids=include_doc_ids,
            exclude_doc_ids=exclude_doc_ids,
            user_id=user_id
        )

    async def retrieve_from_documents(self, query: str, keywords: List[str] | None = None, threshold: float = 0.5, top_k: int = 5, result_formatter: Optional[BaseResultFormatter] = None, prefixes: str = None, include_doc_ids: List[str] = None, exclude_doc_ids: List[str] = None, user_id: str = "User A") -> List[Dict[str, Any]]:
        """
        Retrieve relevant document chunks for a query.

        Args:
            query: Search query
            threshold: Similarity threshold

        Returns:
            List of document chunks with metadata
        """
        return self.rag_engine.retrieve(
            query,
            threshold=threshold,
            keywords=keywords,
            top_k=top_k,
            result_formatter=result_formatter,
            prefixes=prefixes,
            include_doc_ids=include_doc_ids,
            exclude_doc_ids=exclude_doc_ids,
            user_id=user_id
        )

    # ---------- private helpers --------------------------------------------

    async def _save_state(self):
        tmp_stem = self.state_path.parent / f".tmp-{uuid.uuid4().hex}"
        await asyncio.to_thread(self.rag_engine.save_state, str(tmp_stem))

        for f in tmp_stem.parent.glob(f"{tmp_stem.name}*"):
            target = self.state_path.parent / f.name.replace(
                tmp_stem.name, self.state_path.name
            )
            f.replace(target)

        # ❶ ← refresh the pointer so everybody sees the new snapshot
        self._snapshot_path = (
            self.state_path.parent / f"{self.state_path.name}_state.pkl"
        )

        logger.info("Snapshot saved to %s", self._snapshot_path)
