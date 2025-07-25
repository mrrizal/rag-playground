from abc import ABC, abstractmethod
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any
import hashlib

class EmbeddingService(ABC):
    @abstractmethod
    def index_chunks(self, chunks: List[Dict[str, Any]], batch_size: int = 100) -> None:
        """
        Index code chunks into the embedding service.

        Args:
            chunks: List of parsed code chunks
            batch_size: Number of chunks to process at once
        """
        pass

    def query_code(self, query: str, n_results: int = 5, where: Dict = None) -> Dict:
        """
        Query the code collection.

        Args:
            query: Natural language query or code snippet
            n_results: Number of results to return
            where: Metadata filters

        Returns:
            Query results with documents, metadata, and distances
        """
        raise NotImplementedError("This method should be implemented by subclasses.")


class ChromaDBEmbeddingService(EmbeddingService):
    def __init__(self, collection_name: str = "code_repository", persist_directory: str = "./chroma_db"):
        """
        Initialize ChromaDB client and collection for code indexing.

        Args:
            collection_name: Name of the ChromaDB collection
            persist_directory: Directory to persist the database
        """
        # Initialize ChromaDB client with persistence
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        self.collection = self.client.get_or_create_collection(collection_name)

    def prepare_documents_for_indexing(self, chunks: List[Dict[str, Any]]) -> tuple:
        """
        Prepare code chunks for ChromaDB indexing.

        Args:
            chunks: List of parsed code chunks from your parser

        Returns:
            tuple: (documents, metadatas, ids)
        """
        documents = []
        metadatas = []
        ids = []

        for chunk in chunks:
            # Skip empty chunks
            if not chunk.get('code') or not chunk['code'].strip():
                continue

            # Document content - what gets vectorized
            # Option 1: Just the code
            document_content = chunk['code']

            # Option 2: Code + docstring (often better for semantic search)
            if chunk.get('docstring'):
                document_content = f"{chunk['docstring']}\n\n{chunk['code']}"

            # Option 3: Add more context for better retrieval
            context_parts = [chunk['code']]
            if chunk.get('docstring'):
                context_parts.insert(0, f"'''{chunk['docstring']}'''")
            if chunk.get('class_name'):
                context_parts.insert(0, f"# Class: {chunk['class_name']}")
            if chunk.get('class_docstring'):
                context_parts.insert(0, f"# Class docstring: {chunk['class_docstring']}")

            document_content = '\n'.join(context_parts)

            documents.append(document_content)

            # Metadata - used for filtering, not vectorized
            metadata = self._prepare_metadata(chunk)
            metadatas.append(metadata)

            # Unique ID for each chunk
            chunk_id = self._generate_chunk_id(chunk)
            ids.append(chunk_id)

        return documents, metadatas, ids

    def _prepare_metadata(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare metadata for ChromaDB.
        Note: ChromaDB metadata values must be strings, ints, floats, or bools.
        """
        # Copy the chunk dict to avoid modifying the original
        metadata = chunk.copy()

        # Remove fields that shouldn't be in metadata (too large or not useful for filtering)
        fields_to_remove = [
            'code',           # Too large, goes in document content
            'docstring',      # Can be large, include in document if needed
            'class_docstring' # Can be large, include in document if needed
        ]

        for field in fields_to_remove:
            metadata.pop(field, None)

        # Convert lists to comma-separated strings (ChromaDB requirement)
        list_fields = [
            'decorators', 'calls_functions', 'accesses_attributes',
            'imports_used', 'raises_exceptions', 'base_classes', 'methods',
            'parameters'  # This is a list of dicts, might want to handle specially
        ]

        for field in list_fields:
            if field in metadata and isinstance(metadata[field], list):
                if field == 'parameters':
                    # Special handling for parameters (list of dicts)
                    param_strings = []
                    for param in metadata[field]:
                        if isinstance(param, dict):
                            param_str = f"{param.get('name', '')}:{param.get('type', '')}"
                            param_strings.append(param_str)
                    metadata[field] = ','.join(param_strings)
                else:
                    # Regular list to comma-separated string
                    metadata[field] = ','.join(str(item) for item in metadata[field])

        # Ensure all values are ChromaDB-compatible types
        compatible_metadata = {}
        for key, value in metadata.items():
            if isinstance(value, (str, int, float, bool)):
                compatible_metadata[key] = value
            elif value is None:
                # Skip None values
                continue
            else:
                # Convert other types to string
                compatible_metadata[key] = str(value)

        # Remove empty strings if desired
        compatible_metadata = {k: v for k, v in compatible_metadata.items()
                             if v != '' and v is not None}

        return compatible_metadata

    def _generate_chunk_id(self, chunk: Dict[str, Any]) -> str:
        """Generate unique ID for each chunk"""
        filepath = chunk.get('filepath', 'unknown')
        start_line = chunk.get('start_line', 0)
        name = chunk.get('name', 'unnamed')

        # Create a unique but readable ID
        base_id = f"{filepath}:{start_line}:{name}"

        # If ID is too long, use hash
        if len(base_id) > 100:
            hash_suffix = hashlib.md5(base_id.encode()).hexdigest()[:8]
            return f"{name}:{hash_suffix}"

        return base_id

    def index_chunks(self, chunks: List[Dict[str, Any]], batch_size: int = 100) -> None:
        """
        Index code chunks into ChromaDB.

        Args:
            chunks: List of parsed code chunks
            batch_size: Number of chunks to process at once
        """
        print(f"Preparing to index {len(chunks)} chunks...")

        documents, metadatas, ids = self.prepare_documents_for_indexing(chunks)

        print(f"Indexing {len(documents)} valid chunks...")

        # Index in batches to avoid memory issues
        for i in range(0, len(documents), batch_size):
            batch_end = min(i + batch_size, len(documents))

            batch_documents = documents[i:batch_end]
            batch_metadatas = metadatas[i:batch_end]
            batch_ids = ids[i:batch_end]

            print(f"Indexing batch {i//batch_size + 1}/{(len(documents) + batch_size - 1)//batch_size}")

            try:
                self.collection.add(
                    documents=batch_documents,
                    metadatas=batch_metadatas,
                    ids=batch_ids
                )
            except Exception as e:
                print(f"Error indexing batch: {e}")
                # Handle duplicate IDs or other errors
                for j, doc_id in enumerate(batch_ids):
                    try:
                        self.collection.add(
                            documents=[batch_documents[j]],
                            metadatas=[batch_metadatas[j]],
                            ids=[doc_id]
                        )
                    except Exception as inner_e:
                        print(f"Skipping document {doc_id}: {inner_e}")

        print(f"Successfully indexed chunks!")
        print(f"Collection now contains {self.collection.count()} documents")

    def update_chunk(self, chunk: Dict[str, Any]) -> None:
        """Update a single chunk in the collection"""
        documents, metadatas, ids = self.prepare_documents_for_indexing([chunk])

        if documents:
            try:
                self.collection.upsert(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
                print(f"Updated chunk: {ids[0]}")
            except Exception as e:
                print(f"Error updating chunk: {e}")

    def query_code(self, query: str, n_results: int = 5, where: Dict = None) -> Dict:
        """
        Query the code collection.

        Args:
            query: Natural language query or code snippet
            n_results: Number of results to return
            where: Metadata filters

        Returns:
            Query results with documents, metadata, and distances
        """
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where
            )
            return results
        except Exception as e:
            print(f"Query error: {e}")
            return {"documents": [], "metadatas": [], "distances": []}

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the indexed collection"""
        count = self.collection.count()

        # Get sample of metadata to show what's available
        sample = self.collection.peek(limit=5)

        return {
            "total_documents": count,
            "sample_metadata_keys": list(sample["metadatas"][0].keys()) if sample["metadatas"] else [],
            "collection_name": self.collection.name
        }
