import asyncio
import logging
from app.models.schemas import Message
from app.retrieval.engine import RetrievalEngine
from app.services.chat_agent import ChatAgent

logging.basicConfig(level=logging.INFO)

async def run_evals():
    engine = RetrievalEngine()
    agent = ChatAgent(engine)
    
    print("\n--- TEST 1: Vague Query (Clarification) ---")
    msgs = [Message(role="user", content="I need a test for a developer.")]
    res = await agent.process_chat(msgs)
    print(f"Reply: {res.reply}")
    print(f"Recommendations: {len(res.recommendations)}")
    print(f"Tokens Used: {res.estimated_tokens}")
    
    await asyncio.sleep(2)
    
    print("\n--- TEST 2: Specific Query (Recommendation) ---")
    msgs.append(Message(role="assistant", content=res.reply))
    msgs.append(Message(role="user", content="They are a senior Java developer. I want to test their coding skills specifically."))
    res = await agent.process_chat(msgs)
    print(f"Reply: {res.reply}")
    print(f"Recommendations: {[r.name for r in res.recommendations]}")
    print(f"Tokens Used: {res.estimated_tokens}")
    
    await asyncio.sleep(2)
    
    print("\n--- TEST 3: Refinement ---")
    msgs.append(Message(role="assistant", content=res.reply))
    msgs.append(Message(role="user", content="Actually, add a personality test to see if they fit our leadership culture."))
    res = await agent.process_chat(msgs)
    print(f"Reply: {res.reply}")
    print(f"Recommendations: {[r.name for r in res.recommendations]}")
    print(f"Tokens Used: {res.estimated_tokens}")
    
    await asyncio.sleep(2)
    
    print("\n--- TEST 4: Refusal Guardrail ---")
    msgs_refusal = [Message(role="user", content="Can you write a legal contract for my new hire?")]
    res = await agent.process_chat(msgs_refusal)
    print(f"Reply: {res.reply}")
    print(f"Recommendations: {len(res.recommendations)}")
    print(f"End of convo: {res.end_of_conversation}")
    print(f"Tokens Used: {res.estimated_tokens}")

if __name__ == "__main__":
    asyncio.run(run_evals())
