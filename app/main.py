import logging
import traceback

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    __import__('pysqlite3')
    import sys
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
    logger.info("Successfully injected pysqlite3")
except ImportError:
    logger.info("pysqlite3 not found, using system sqlite3")
except Exception as e:
    logger.error(f"Error injecting pysqlite3: {e}")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging
from contextlib import asynccontextmanager
from app.models.schemas import ChatRequest, ChatResponse
from app.retrieval.engine import RetrievalEngine
from app.services.chat_agent import ChatAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global instances
retrieval_engine = None
chat_agent = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global retrieval_engine, chat_agent
    logger.info("Initializing Retrieval Engine...")
    retrieval_engine = RetrievalEngine()
    logger.info("Initializing Chat Agent...")
    chat_agent = ChatAgent(retrieval_engine)
    yield
    # Cleanup if needed

app = FastAPI(
    title="Conversational SHL Assessment Recommender",
    description="Stateless conversational AI system that helps recruiters discover relevant SHL assessments.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, replace with specific domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not chat_agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        response = await chat_agent.process_chat(request.messages)
        return response
    except Exception as e:
        logger.error(f"Error processing chat: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
