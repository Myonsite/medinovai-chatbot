"""
Vector Store - RAG Integration for MedinovAI
Provides context-aware healthcare knowledge retrieval for AI responses
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import json

import structlog
import numpy as np
from sentence_transformers import SentenceTransformer

from utils.config import Settings
from utils.phi_protection import PHIProtector

logger = structlog.get_logger(__name__)


class Document:
    """Document model for vector storage."""
    
    def __init__(
        self,
        id: str,
        content: str,
        metadata: Dict[str, Any],
        embedding: Optional[List[float]] = None
    ):
        self.id = id
        self.content = content
        self.metadata = metadata
        self.embedding = embedding
        self.created_at = datetime.utcnow()


class VectorStore:
    """
    In-memory vector store for healthcare knowledge retrieval.
    In production, this would use Pinecone, Weaviate, or Chroma.
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.phi_protector: Optional[PHIProtector] = None
        
        # Embedding model
        self.embedding_model: Optional[SentenceTransformer] = None
        self.embedding_dimension = 384  # all-MiniLM-L6-v2 dimension
        
        # Document storage
        self.documents: Dict[str, Document] = {}
        self.embeddings: Dict[str, np.ndarray] = {}
        
        # Healthcare knowledge categories
        self.categories = {
            "general_health": "General health information and wellness",
            "symptoms": "Symptom descriptions and possible conditions", 
            "medications": "Medication information and interactions",
            "procedures": "Medical procedures and treatments",
            "billing": "Insurance and billing information",
            "appointments": "Scheduling and appointment management",
            "emergency": "Emergency care and when to seek help",
            "prevention": "Preventive care and health maintenance"
        }
        
        logger.info("Vector store initialized")
    
    async def initialize(self) -> None:
        """Initialize vector store and load healthcare knowledge."""
        try:
            # Load embedding model
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Embedding model loaded")
            
            # Get PHI protector
            from main import phi_protector
            self.phi_protector = phi_protector
            
            # Load healthcare knowledge base
            await self._load_healthcare_knowledge()
            
            logger.info(
                "Vector store initialized successfully",
                document_count=len(self.documents),
                categories=len(self.categories)
            )
            
        except Exception as e:
            logger.error("Failed to initialize vector store", error=str(e))
            raise
    
    async def add_document(
        self,
        content: str,
        metadata: Dict[str, Any],
        document_id: Optional[str] = None
    ) -> str:
        """Add document to vector store."""
        try:
            # Generate document ID if not provided
            if not document_id:
                document_id = f"doc_{len(self.documents)}_{int(datetime.utcnow().timestamp())}"
            
            # Check for PHI in content
            clean_content = content
            if self.phi_protector:
                phi_detected, clean_content = await self.phi_protector.detect_and_redact(
                    content,
                    context={"source": "knowledge_base"}
                )
                
                if phi_detected:
                    logger.warning("PHI detected in document, redacted", doc_id=document_id)
            
            # Generate embedding
            embedding = self.embedding_model.encode(clean_content).tolist()
            
            # Create document
            document = Document(
                id=document_id,
                content=clean_content,
                metadata=metadata,
                embedding=embedding
            )
            
            # Store document and embedding
            self.documents[document_id] = document
            self.embeddings[document_id] = np.array(embedding)
            
            logger.debug("Document added to vector store", doc_id=document_id)
            return document_id
            
        except Exception as e:
            logger.error("Failed to add document", error=str(e))
            raise
    
    async def search(
        self,
        query: str,
        k: int = 5,
        category_filter: Optional[str] = None,
        min_similarity: float = 0.3
    ) -> List[Tuple[Document, float]]:
        """Search for similar documents."""
        try:
            if not self.embedding_model or not self.embeddings:
                return []
            
            # Generate query embedding
            query_embedding = self.embedding_model.encode(query)
            query_norm = np.linalg.norm(query_embedding)
            
            # Calculate similarities
            similarities = []
            for doc_id, doc_embedding in self.embeddings.items():
                document = self.documents[doc_id]
                
                # Apply category filter if specified
                if category_filter and document.metadata.get("category") != category_filter:
                    continue
                
                # Calculate cosine similarity
                doc_norm = np.linalg.norm(doc_embedding)
                if doc_norm == 0 or query_norm == 0:
                    similarity = 0.0
                else:
                    similarity = np.dot(query_embedding, doc_embedding) / (query_norm * doc_norm)
                
                # Filter by minimum similarity
                if similarity >= min_similarity:
                    similarities.append((document, float(similarity)))
            
            # Sort by similarity and return top k
            similarities.sort(key=lambda x: x[1], reverse=True)
            results = similarities[:k]
            
            logger.debug(
                "Vector search completed",
                query_length=len(query),
                results_count=len(results),
                category_filter=category_filter
            )
            
            return results
            
        except Exception as e:
            logger.error("Vector search failed", error=str(e))
            return []
    
    async def get_context_for_query(
        self,
        query: str,
        conversation_context: Optional[Dict[str, Any]] = None,
        max_context_length: int = 2000
    ) -> str:
        """Get relevant context for a query to enhance AI responses."""
        try:
            # Determine category based on query
            category = await self._classify_query(query)
            
            # Search for relevant documents
            results = await self.search(
                query=query,
                k=3,
                category_filter=category,
                min_similarity=0.4
            )
            
            if not results:
                # Fallback to general search without category filter
                results = await self.search(query=query, k=2, min_similarity=0.3)
            
            # Build context string
            context_parts = []
            current_length = 0
            
            for document, similarity in results:
                content = document.content
                metadata = document.metadata
                
                # Add source information
                source_info = f"[Source: {metadata.get('title', 'Healthcare Knowledge')}]"
                full_content = f"{source_info}\n{content}\n"
                
                # Check if adding this would exceed max length
                if current_length + len(full_content) > max_context_length:
                    # Truncate if needed
                    remaining_length = max_context_length - current_length
                    if remaining_length > 100:  # Only add if meaningful length remains
                        truncated_content = content[:remaining_length-len(source_info)-10] + "..."
                        context_parts.append(f"{source_info}\n{truncated_content}")
                    break
                
                context_parts.append(full_content)
                current_length += len(full_content)
            
            context = "\n".join(context_parts)
            
            logger.debug(
                "Context generated for query",
                query_length=len(query),
                context_length=len(context),
                sources_used=len(context_parts),
                category=category
            )
            
            return context
            
        except Exception as e:
            logger.error("Failed to get context for query", error=str(e))
            return ""
    
    async def get_document_count(self) -> int:
        """Get total number of documents in store."""
        return len(self.documents)
    
    async def health_check(self) -> Dict[str, Any]:
        """Check vector store health."""
        try:
            return {
                "status": "healthy",
                "document_count": len(self.documents),
                "embedding_dimension": self.embedding_dimension,
                "model_loaded": self.embedding_model is not None,
                "categories": list(self.categories.keys())
            }
        except Exception as e:
            logger.error("Vector store health check failed", error=str(e))
            return {"status": "unhealthy", "error": str(e)}
    
    async def cleanup(self) -> None:
        """Cleanup vector store resources."""
        logger.info("Cleaning up vector store...")
        
        # Clear storage
        self.documents.clear()
        self.embeddings.clear()
        
        # Note: In production, you might want to save state to disk
        logger.info("Vector store cleanup complete")
    
    # Private methods
    
    async def _load_healthcare_knowledge(self) -> None:
        """Load healthcare knowledge base."""
        try:
            # Sample healthcare knowledge - in production, load from files/database
            knowledge_base = [
                {
                    "title": "General Health Information",
                    "content": "Regular checkups are important for maintaining good health. Adults should have annual physical exams to monitor vital signs, blood pressure, cholesterol levels, and discuss any health concerns with their healthcare provider.",
                    "category": "general_health",
                    "tags": ["checkup", "physical", "preventive", "annual"]
                },
                {
                    "title": "Fever and When to Seek Care",
                    "content": "A fever is typically defined as a body temperature above 100.4°F (38°C). For adults, seek medical attention if fever exceeds 103°F (39.4°C), persists for more than 3 days, or is accompanied by severe symptoms like difficulty breathing, chest pain, or severe headache.",
                    "category": "symptoms",
                    "tags": ["fever", "temperature", "emergency", "symptoms"]
                },
                {
                    "title": "Medication Safety and Interactions",
                    "content": "Always inform your healthcare provider about all medications, supplements, and over-the-counter drugs you're taking. Some medications can interact with each other or with certain foods. Never stop taking prescribed medications without consulting your doctor first.",
                    "category": "medications",
                    "tags": ["medication", "safety", "interactions", "prescription"]
                },
                {
                    "title": "Insurance and Billing Questions",
                    "content": "For insurance coverage questions, contact your insurance provider directly or speak with our billing department. Keep copies of all medical bills and insurance communications. If you receive a bill you don't understand, contact our billing office for clarification.",
                    "category": "billing",
                    "tags": ["insurance", "billing", "coverage", "payment"]
                },
                {
                    "title": "Scheduling Appointments",
                    "content": "To schedule an appointment, you can call our office during business hours, use our online patient portal, or request an appointment through our mobile app. For urgent concerns, same-day appointments may be available.",
                    "category": "appointments",
                    "tags": ["scheduling", "appointment", "booking", "urgent"]
                },
                {
                    "title": "Emergency Care Guidelines",
                    "content": "Call 911 immediately for life-threatening emergencies such as chest pain, difficulty breathing, severe bleeding, loss of consciousness, or signs of stroke. For non-emergency urgent care needs, visit our urgent care center or call our nurse hotline.",
                    "category": "emergency",
                    "tags": ["emergency", "911", "urgent", "stroke", "chest pain"]
                },
                {
                    "title": "Preventive Care and Vaccines",
                    "content": "Stay up to date with recommended vaccinations including annual flu shots, COVID-19 boosters, and age-appropriate vaccines. Discuss cancer screenings with your doctor based on your age, family history, and risk factors.",
                    "category": "prevention",
                    "tags": ["prevention", "vaccines", "screening", "flu shot"]
                },
                {
                    "title": "Common Cold vs Flu Symptoms",
                    "content": "Cold symptoms typically include runny nose, mild cough, and low-grade fever. Flu symptoms are more severe with high fever, body aches, fatigue, and can develop suddenly. Both are viral infections that usually resolve with rest and fluids.",
                    "category": "symptoms",
                    "tags": ["cold", "flu", "symptoms", "viral", "fever"]
                },
                {
                    "title": "Blood Pressure Management",
                    "content": "Normal blood pressure is typically below 120/80 mmHg. High blood pressure (hypertension) often has no symptoms but increases risk of heart disease and stroke. Regular monitoring, healthy diet, exercise, and medication when prescribed can help manage blood pressure.",
                    "category": "general_health",
                    "tags": ["blood pressure", "hypertension", "heart", "monitoring"]
                },
                {
                    "title": "Diabetes Management and Monitoring",
                    "content": "For diabetes management, monitor blood sugar levels as directed by your healthcare provider. Maintain a healthy diet, exercise regularly, take medications as prescribed, and attend regular checkups to prevent complications.",
                    "category": "general_health",
                    "tags": ["diabetes", "blood sugar", "monitoring", "management"]
                }
            ]
            
            # Add documents to vector store
            for item in knowledge_base:
                await self.add_document(
                    content=item["content"],
                    metadata={
                        "title": item["title"],
                        "category": item["category"],
                        "tags": item["tags"],
                        "source": "healthcare_knowledge_base"
                    }
                )
            
            logger.info(f"Loaded {len(knowledge_base)} healthcare knowledge documents")
            
        except Exception as e:
            logger.error("Failed to load healthcare knowledge", error=str(e))
    
    async def _classify_query(self, query: str) -> Optional[str]:
        """Classify query to determine relevant category."""
        query_lower = query.lower()
        
        # Simple keyword-based classification
        # In production, use a trained classifier
        category_keywords = {
            "symptoms": ["symptom", "pain", "fever", "headache", "cough", "cold", "flu", "sick", "hurt"],
            "medications": ["medication", "medicine", "drug", "prescription", "pill", "dosage", "side effect"],
            "billing": ["bill", "insurance", "cost", "payment", "coverage", "copay", "deductible"],
            "appointments": ["appointment", "schedule", "booking", "visit", "see doctor", "when can"],
            "emergency": ["emergency", "urgent", "911", "chest pain", "breathing", "unconscious"],
            "prevention": ["vaccine", "shot", "screening", "checkup", "prevention", "immunization"],
            "general_health": ["health", "wellness", "exercise", "diet", "blood pressure", "diabetes"]
        }
        
        for category, keywords in category_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                return category
        
        return None  # No specific category detected


class DocumentProcessor:
    """Process and prepare documents for vector storage."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.phi_protector: Optional[PHIProtector] = None
    
    async def initialize(self) -> None:
        """Initialize document processor."""
        from main import phi_protector
        self.phi_protector = phi_protector
    
    async def process_text_document(
        self,
        text: str,
        metadata: Dict[str, Any],
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ) -> List[Dict[str, Any]]:
        """Process text document into chunks for vector storage."""
        try:
            # Clean and protect text
            clean_text = text
            if self.phi_protector:
                phi_detected, clean_text = await self.phi_protector.detect_and_redact(
                    text,
                    context={"source": "document_processing"}
                )
                
                if phi_detected:
                    logger.warning("PHI detected in document processing")
            
            # Split into chunks
            chunks = self._split_text_into_chunks(clean_text, chunk_size, chunk_overlap)
            
            # Prepare documents
            documents = []
            for i, chunk in enumerate(chunks):
                chunk_metadata = metadata.copy()
                chunk_metadata.update({
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "chunk_size": len(chunk)
                })
                
                documents.append({
                    "content": chunk,
                    "metadata": chunk_metadata
                })
            
            return documents
            
        except Exception as e:
            logger.error("Failed to process document", error=str(e))
            return []
    
    def _split_text_into_chunks(
        self,
        text: str,
        chunk_size: int,
        chunk_overlap: int
    ) -> List[str]:
        """Split text into overlapping chunks."""
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # If this is not the last chunk and we're in the middle of a word,
            # try to end at a sentence or word boundary
            if end < len(text):
                # Look for sentence boundaries (. ! ?)
                sentence_end = text.rfind('.', start, end)
                if sentence_end == -1:
                    sentence_end = text.rfind('!', start, end)
                if sentence_end == -1:
                    sentence_end = text.rfind('?', start, end)
                
                if sentence_end != -1 and sentence_end > start + chunk_size // 2:
                    end = sentence_end + 1
                else:
                    # Look for word boundaries
                    space_pos = text.rfind(' ', start, end)
                    if space_pos != -1 and space_pos > start + chunk_size // 2:
                        end = space_pos
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move start position with overlap
            start = end - chunk_overlap
            if start <= 0:
                start = end
        
        return chunks 