import json
import logging
from typing import List, Dict, Any, Tuple
import litellm
from app.models.schemas import Message, ChatResponse, Recommendation
from app.prompts.templates import SYSTEM_PROMPT, ANALYSIS_PROMPT, STATE_EXTRACTION_PROMPT, INTENT_CLASSIFICATION_PROMPT, GROUNDED_RESPONSE_PROMPT, RECOMMENDATION_PROMPT, COMPARISON_PROMPT
from app.retrieval.engine import RetrievalEngine

import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Using 2.5-flash because the current API key is restricted to this specific model name.
# Note: This model has a very low 20 RPD limit on this key.
MODEL_NAME = os.getenv("MODEL_NAME", "gemini/gemini-2.5-flash")

class ChatAgent:
    def __init__(self, retrieval_engine: RetrievalEngine):
        self.retrieval_engine = retrieval_engine

    async def _extract_intent_and_state(self, messages: List[Message]) -> Tuple[Dict[str, Any], int]:
        """
        Uses LLM to analyze the conversation, extract state, and then classify intent in a single call.
        """
        history = "\n".join([f"{m.role}: {m.content}" for m in messages])
        
        analysis_prompt = ANALYSIS_PROMPT.format(history=history)
        
        tokens_used = 0
        try:
            response = await litellm.acompletion(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": "You are a structured hiring context analyzer. Output valid JSON only."},
                    {"role": "user", "content": analysis_prompt}
                ],
                response_format={ "type": "json_object" },
                temperature=0.0
            )
            data = json.loads(response.choices[0].message.content)
            
            # Track tokens
            usage = getattr(response, 'usage', None)
            if usage:
                tokens_used = usage.total_tokens

            # Flatten for compatibility
            state = data.get("state", {})
            state["intent"] = data.get("intent", "CLARIFY")
            if "reply" in data:
                state["reply"] = data["reply"]
            return state, tokens_used
        except Exception as e:
            logger.error(f"Error in combined analysis: {e}")
            error_str = str(e).lower()
            if "rate_limit" in error_str or "429" in error_str or "quota" in error_str:
                return {"intent": "RATE_LIMITED", "error": "rate_limit"}, 0
            return {"intent": "CLARIFY", "search_query": messages[-1].content if messages else ""}, 0

    async def _generate_response(self, messages: List[Message], intent_data: Dict[str, Any], retrieved_docs: List[Dict[str, Any]]) -> Tuple[str, List[Recommendation], int]:
        """
        Generates the grounded response and formats recommendations.
        """
        intent = intent_data.get("intent", "CLARIFY")
        
        # Handle early exit for rate limits
        if intent == "RATE_LIMITED":
            last_msg = messages[-1].content.lower()
            # Heuristic to check if the user is actually asking for something
            is_job_query = any(k in last_msg for k in ["dev", "engineer", "lead", "manager", "test", "hiring", "role", "junior", "senior", "coding", "assessment"])
            
            if is_job_query and retrieved_docs:
                recs = []
                for doc in retrieved_docs[:3]:
                    meta = doc['metadata']
                    recs.append(Recommendation(
                        name=meta['name'],
                        url=meta['url'],
                        test_type=meta['assessment_type'],
                        keys=meta.get('keys', ''),
                        languages=meta.get('languages', ''),
                        duration=meta.get('duration', '')
                    ))
                
                fallback_reply = "I'm currently experiencing high traffic (API quota reached), but based on your request, I found these assessments that might help:\n\n"
                for i, r in enumerate(recs):
                    fallback_reply += f"{i+1}. **{r.name}** - {r.test_type}\n   [View Assessment]({r.url})\n\n"
                fallback_reply += "Please try again in a while when my quota resets for a more intelligent conversation!"
                return fallback_reply, recs, 0
            
            return "I've reached my daily AI message limit (20 requests/day). I can still help you find assessments if you specify a role, but for a full conversation, please try again tomorrow or use a different API key.", [], 0

        # If analysis already provided a reply for CLARIFY/REFUSE, use it
        if "reply" in intent_data and intent in ["CLARIFY", "REFUSE"] and not retrieved_docs:
            return intent_data["reply"], [], 0

        # Format retrieved data
        retrieved_text = ""
        recs = []
        retrieved_objects = []
        if retrieved_docs:
            for i, doc in enumerate(retrieved_docs):
                meta = doc['metadata']
                retrieved_text += f"\n--- Assessment {i+1} ---\n{doc['document']}\nURL: {meta['url']}\n"
                recs.append(Recommendation(
                    name=meta['name'],
                    url=meta['url'],
                    test_type=meta['assessment_type'],
                    keys=meta.get('keys', ''),
                    languages=meta.get('languages', ''),
                    duration=meta.get('duration', '')
                ))
                retrieved_objects.append(meta)
        else:
            retrieved_text = "No assessments retrieved."

        # Prepare messages for generation
        if intent in ["RECOMMEND", "REFINE"]:
            history = "\n".join([f"{m.role}: {m.content}" for m in messages])
            prompt = RECOMMENDATION_PROMPT.format(
                extracted_state_json=json.dumps(intent_data, indent=2),
                retrieved_assessment_objects_json=json.dumps(retrieved_objects, indent=2),
                full_messages_array=history
            )
            gen_messages = [{"role": "user", "content": prompt}]
        elif intent == "COMPARE":
            prompt = COMPARISON_PROMPT.format(
                retrieved_comparison_targets_json=json.dumps(retrieved_objects, indent=2),
                extracted_state_json=json.dumps(intent_data, indent=2)
            )
            gen_messages = [{"role": "user", "content": prompt}]
        else:
            gen_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            for m in messages[:-1]: # Add history except last
                gen_messages.append({"role": m.role, "content": m.content})
                
            # Add last user message with context
            last_user_msg = messages[-1].content
            enriched_user_msg = GROUNDED_RESPONSE_PROMPT.format(retrieved_data=retrieved_text) + f"\n\nUser Message:\n{last_user_msg}"
            gen_messages.append({"role": "user", "content": enriched_user_msg})

        tokens_used = 0
        try:
            response = await litellm.acompletion(
                model=MODEL_NAME,
                messages=gen_messages,
                temperature=0.3
            )
            reply = response.choices[0].message.content
            usage = getattr(response, 'usage', None)
            if usage:
                tokens_used = usage.total_tokens
            return reply, recs, tokens_used
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            if "RateLimitError" in str(e) or "429" in str(e):
                if recs:
                    fallback_reply = "I'm currently experiencing high traffic and reached my message limit, but I've found some assessments that might match your needs:\n\n"
                    for i, r in enumerate(recs[:3]):
                        fallback_reply += f"{i+1}. **{r.name}** - {r.test_type}\n   [View Assessment]({r.url})\n\n"
                    fallback_reply += "Please try again in a few minutes for a more detailed recommendation."
                    return fallback_reply, recs, 0
                return "I'm currently receiving too many requests (quota exceeded). Please try again in a few moments.", [], 0
            return "I apologize, but I encountered an error processing your request.", [], 0


    async def process_chat(self, messages: List[Message]) -> ChatResponse:
        """
        Main pipeline for processing a chat request.
        """
        if not messages:
            return ChatResponse(
                reply="Hello! I'm your SHL Assessment Advisor.\n\nI help recruiters and hiring managers find the right SHL assessments for any role — through a quick conversation rather than manual catalog searching.\n\nTo get started, tell me about the role you're hiring for:\n\n- **What's the job title or function?**\n- **What level of experience are you targeting?** (e.g., junior, mid-level, senior, leadership)\n- **Any specific skills or behavioral traits you want to assess?**\n\nYou don't need all the answers right now — just share what you know and I'll guide you from there.",
                recommendations=[],
                end_of_conversation=False,
                estimated_tokens=0
            )

        if len(messages) > 16: # 8 turns (user + assistant)
             return ChatResponse(
                reply="We have reached the maximum conversation length. Please start a new session.",
                recommendations=[],
                end_of_conversation=True,
                estimated_tokens=0
             )

        # 1. Intent Detection & State Extraction
        intent_data, intent_tokens = await self._extract_intent_and_state(messages)
        intent = intent_data.get("intent", "CLARIFY")
        logger.info(f"Detected Intent: {intent}")

        # 2. Retrieval
        retrieved_docs = []
        if intent in ["RECOMMEND", "REFINE", "COMPARE", "CLARIFY", "RATE_LIMITED"]:
            if intent == "COMPARE" and intent_data.get("comparison_targets"):
                # Retrieve each target specifically
                for target in intent_data["comparison_targets"]:
                    docs = self.retrieval_engine.search(target, top_k=1)
                    if docs:
                        retrieved_docs.extend(docs)
                
                # Deduplicate by ID
                seen_ids = set()
                deduped = []
                for d in retrieved_docs:
                    if d['id'] not in seen_ids:
                        deduped.append(d)
                        seen_ids.add(d['id'])
                retrieved_docs = deduped
            else:
                query = intent_data.get("search_query")
                if not query or query == "":
                     query = messages[-1].content
                
                logger.info(f"Retrieving for query: {query}")
                # Dynamic Top K based on intent
                top_k = 2 if intent == "COMPARE" else 5
                retrieved_docs = self.retrieval_engine.search(query, top_k=top_k)

        # 3. Generate Response
        reply, recommendations, gen_tokens = await self._generate_response(messages, intent_data, retrieved_docs)

        # 4. Determine if conversation ended
        end_of_convo = False
        if intent in ["RECOMMEND", "REFINE", "COMPARE", "CLARIFY"]:
             # Simple heuristic: if user says "perfect", "thanks", "that works", etc.
             last_msg = messages[-1].content.lower()
             if any(word in last_msg for word in ["perfect", "thanks", "thank you", "that works", "locking it in", "confirmed", "final list"]):
                 end_of_convo = True

        # 5. Schema constraints
        if intent in ["CLARIFY", "REFUSE", "RATE_LIMITED"]:
            if intent != "RATE_LIMITED" or not recommendations:
                recommendations = []

        return ChatResponse(
            reply=reply,
            recommendations=recommendations[:10], # Max 10
            end_of_conversation=end_of_convo,
            estimated_tokens=intent_tokens + gen_tokens
        )
