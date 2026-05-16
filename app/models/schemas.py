from pydantic import BaseModel, Field
from typing import List, Literal, Optional

class Message(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]

class Recommendation(BaseModel):
    name: str = Field(..., description="Assessment Name")
    url: str = Field(..., description="Valid catalog URL for the assessment")
    test_type: str = Field(..., description="Type of the test, e.g., Knowledge, Personality, Coding, etc.")
    keys: Optional[str] = Field(None, description="Keys/Dimensions measured")
    languages: Optional[str] = Field(None, description="Supported languages")
    duration: Optional[str] = Field(None, description="Test duration")
    
class ChatResponse(BaseModel):
    reply: str = Field(..., description="Assistant response")
    recommendations: List[Recommendation] = Field(
        default_factory=list, 
        description="List of recommended assessments, max 10. Empty if clarifying/refusing."
    )
    end_of_conversation: bool = Field(
        ..., 
        description="Boolean indicating if the conversation has reached a natural conclusion or refusal"
    )
    estimated_tokens: Optional[int] = Field(None, description="Estimated total tokens used for this turn")
