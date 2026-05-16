import json
import logging
from pathlib import Path
from typing import List, Dict, Any
import chromadb
import os
from chromadb.utils import embedding_functions
from app.models.catalog import Assessment

logger = logging.getLogger(__name__)

class RetrievalEngine:
    def __init__(self, data_path: str = "data/catalog.json", db_path: str = "data/chroma_db"):
        self.data_path = Path(data_path)
        self.db_path = Path(db_path)
        self.client = chromadb.PersistentClient(path=str(self.db_path))
        
        # Use Google Gemini Embeddings to save memory on Render
        api_key = os.getenv("GEMINI_API_KEY")
        self.embedding_function = embedding_functions.GoogleGenerativeAiEmbeddingFunction(
            api_key=api_key,
            model_name="models/text-embedding-004"
        )
        
        self.collection_name = "shl_assessments_gemini" # New collection for different embedding space
        
        # Try to get the collection, if it doesn't exist, create and populate it
        try:
            self.collection = self.client.get_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function
            )
            logger.info(f"Loaded existing collection: {self.collection_name}")
        except Exception:
            logger.info(f"Collection {self.collection_name} not found. Creating and populating...")
            self.collection = self.client.create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function,
                metadata={"hnsw:space": "cosine"}
            )
            self._populate_collection()

    def _populate_collection(self):
        if not self.data_path.exists():
            logger.error(f"Catalog data file not found at {self.data_path}")
            return

        with open(self.data_path, "r") as f:
            assessments_data = json.load(f)

        documents = []
        metadatas = []
        ids = []

        for i, item in enumerate(assessments_data):
            # Map official schema to our internal document and metadata
            name = item.get("name", "")
            description = item.get("description", "")
            key_list = item.get("keys", [])
            keys = ", ".join(key_list)
            languages = ", ".join(item.get("languages", []))
            duration = item.get("duration", "")
            job_levels = ", ".join(item.get("job_levels", []))
            link = item.get("link", "")
            remote = item.get("remote", "no")

            # Shorthand mapping for test types
            type_mapping = {
                "Ability & Aptitude": "A",
                "Knowledge & Skills": "K",
                "Personality & Behavior": "P",
                "Biodata & Situational Judgment": "B",
                "Simulations": "S",
                "Competencies": "C",
                "Development & 360": "D"
            }
            shorthand_types = [type_mapping.get(k, k[0] if k else "?") for k in key_list]
            assessment_type = ",".join(shorthand_types)

            # Create a rich text document for embedding
            doc_text = f"Assessment Name: {name}\nDescription: {description}\nKeys/Types: {keys}\nJob Levels: {job_levels}"
            
            documents.append(doc_text)
            
            # Metadata for filtering and response generation
            metadata = {
                "name": name,
                "url": link,
                "assessment_type": assessment_type, 
                "keys": keys,
                "languages": languages,
                "duration": duration,
                "remote_testing_support": True if remote.lower() == "yes" else False
            }
            metadatas.append(metadata)
            ids.append(f"assessment_{i}")

        if documents:
            # Batch process to avoid large payload errors if necessary, but 377 should be fine
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"Successfully populated collection with {len(documents)} assessments.")

    def search(self, query: str, top_k: int = 5, filter_dict: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Search for relevant assessments based on semantic query and optional metadata filters.
        """
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k,
            where=filter_dict
        )

        formatted_results = []
        if results['ids'] and len(results['ids']) > 0:
            for i in range(len(results['ids'][0])):
                formatted_results.append({
                    "id": results['ids'][0][i],
                    "score": results['distances'][0][i] if 'distances' in results and results['distances'] else None,
                    "metadata": results['metadatas'][0][i],
                    "document": results['documents'][0][i]
                })

        return formatted_results

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    engine = RetrievalEngine()
    print("Search test: 'Looking for a coding test for software engineer'")
    res = engine.search("Looking for a coding test for software engineer", top_k=2)
    for r in res:
        print(f"- {r['metadata']['name']}")
