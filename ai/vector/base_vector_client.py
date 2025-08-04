from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any


class BaseVectorClient:
    
    @abstractmethod
    def add_document(self, document_id: str, text: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Add a document to the vector store.
        
        :param document_id: Unique identifier for the document.
        :param text: The text content of the document.
        :param metadata: Optional metadata associated with the document.
        """
        pass
    @abstractmethod
    def update_document(self, document_id: str, text: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Update an existing document in the vector store.
        
        :param document_id: Unique identifier for the document.
        :param text: The updated text content of the document.
        :param metadata: Optional updated metadata associated with the document.
        """
        pass
    @abstractmethod
    def query_similar_documents(self, query: str, top_k: int = 5, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Query the vector store for similar documents based on a text query.
        
        :param query: The text query to search for similar documents.
        :param top_k: The number of top similar documents to return.
        :return: A list of dictionaries containing document IDs and their similarity scores.
        """
        pass
    @abstractmethod
    def get_document_embedding(self, document_id: str) -> Optional[List[float]]:
        """
        Get the vector embedding for a given document.

        :param document_id: The ID of the document to retrieve the embedding for.
        :return: A list of floats representing the vector embedding, or None if not found.
        """
        pass
    @abstractmethod
    def delete_document(self, document_id: str) -> bool:
        """
        Delete a document from the vector store.
        
        :param document_id: Unique identifier for the document to be deleted.
        :return: True if the document was successfully deleted, False otherwise.
        """
        pass
    