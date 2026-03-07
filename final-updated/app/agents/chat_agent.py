import time
from datetime import datetime, timezone
from uuid import uuid4

from botocore.exceptions import ClientError

from app.agents.base_agent import BaseAgent, MAX_RETRIES, RETRY_BACKOFF_BASE
from app.config import settings
from app.models.chat import ChatMessage, ChatResponse
from app.utils.errors import AWSServiceError
from app.utils.logging import get_logger

logger = get_logger(__name__)

CONFIRMATION_PHRASES = [
    "looks good, generate",
    "looks good generate",
    "generate it",
    "generate the render",
    "generate the final",
    "go ahead and generate",
    "ready to generate",
    "let's generate",
    "create the render",
    "make the render",
    "render it",
]


class ChatAgent(BaseAgent):
    """Agent for multi-turn design refinement conversations using the Bedrock Converse API."""

    def converse_bedrock(
        self,
        model_id: str,
        messages: list[dict],
        system: list[dict],
        inference_config: dict,
    ) -> dict:
        """Invoke Bedrock Converse API with retry logic.

        Returns the full response dict directly (no JSON parsing needed).

        Raises:
            AWSServiceError: If all retries are exhausted or a non-retryable error occurs.
        """
        last_error = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = self.bedrock.converse(
                    modelId=model_id,
                    messages=messages,
                    system=system,
                    inferenceConfig=inference_config,
                )
                return response
            except ClientError as e:
                error_code = e.response["Error"]["Code"]
                last_error = e
                if error_code in ("ThrottlingException", "ServiceUnavailableException"):
                    wait = RETRY_BACKOFF_BASE * (2 ** (attempt - 1))
                    logger.warning(
                        f"Bedrock converse attempt {attempt}/{MAX_RETRIES} "
                        f"failed with {error_code}, retrying in {wait}s"
                    )
                    time.sleep(wait)
                else:
                    logger.error(f"Bedrock converse failed: {error_code} - {e}")
                    raise AWSServiceError("Bedrock", "converse", str(e))
            except Exception as e:
                logger.error(f"Bedrock converse unexpected error: {e}")
                raise AWSServiceError("Bedrock", "converse", str(e))

        logger.error(f"Bedrock converse exhausted {MAX_RETRIES} retries")
        raise AWSServiceError("Bedrock", "converse", str(last_error))

    def _build_system_prompt(self, descriptive_summary: str) -> list[dict]:
        """Build the Converse API system parameter with architectural context.

        Returns a list like [{"text": "..."}] for the system parameter.
        """
        prompt = (
            "You are a friendly architectural design assistant for DraftBridge.\n\n"
            f"## Current Design\n{descriptive_summary}\n\n"
            "## Rules\n"
            "- Keep responses SHORT — 2-3 sentences max. Be conversational, not academic.\n"
            "- Acknowledge the change, briefly note its impact, and ask if they want more changes.\n"
            "- Do NOT write long paragraphs or bullet-point lists unless the user asks for detail.\n"
            "- Have a back-and-forth conversation. Do NOT assume the user is done after one message.\n"
            "- ONLY when the user EXPLICITLY asks to generate the final render "
            "(e.g., 'generate it', 'render it', 'go ahead and generate', 'create the render'), "
            "include the exact tag [READY_TO_RENDER] and list the refinements in a short bullet list.\n"
            "- Do NOT include [READY_TO_RENDER] for casual feedback like 'looks good', 'great', 'nice'. "
            "The user may still want more changes.\n"
        )
        return [{"text": prompt}]

    def _detect_confirmation(self, assistant_text: str, user_message: str) -> bool:
        """Detect if the user has explicitly confirmed the design is ready for rendering.

        Only triggers on explicit generation requests, not casual positive feedback.
        Checks for [READY_TO_RENDER] tag in assistant response as primary signal,
        and explicit user phrases as secondary signal.
        """
        if "[READY_TO_RENDER]" in assistant_text:
            return True
        lower_message = user_message.lower().strip()
        for phrase in CONFIRMATION_PHRASES:
            if phrase in lower_message:
                return True
        return False

    def _build_refined_prompt(self, descriptive_summary: str, messages: list[dict]) -> str:
        """Build a coherent refined prompt by asking the LLM to consolidate all refinements.

        Instead of naively concatenating raw user messages, we ask the text model
        to produce a single, coherent architectural description that integrates
        the original design with all requested changes. This gives Nova Canvas
        and Nova Reel a clear, unified prompt.
        """
        # Collect all user refinement messages (exclude the final confirmation trigger)
        user_messages = [msg for msg in messages if msg["role"] == "user"]
        refinements = []
        for msg in user_messages[:-1] if len(user_messages) > 1 else user_messages:
            content = msg["content"]
            if isinstance(content, list):
                content = content[0].get("text", "") if content else ""
            if content and content.strip():
                refinements.append(content.strip())

        if not refinements:
            return descriptive_summary[:380]

        refinement_text = "; ".join(refinements)

        # Ask the LLM to produce a single coherent description.
        # Must stay under ~380 chars so the video prompt (which adds framing)
        # fits within Nova Reel's 512-char limit.
        consolidation_messages = [
            {
                "role": "user",
                "content": [{"text": (
                    f"Original design: {descriptive_summary[:300]}\n"
                    f"User requested changes: {refinement_text}\n\n"
                    "Write a single, coherent architectural description (under 350 characters) "
                    "that combines the original design with ALL the requested changes. "
                    "Be specific and visual. Do not use bullet points. "
                    "Just output the description, nothing else."
                )}],
            }
        ]

        try:
            response = self.converse_bedrock(
                model_id=settings.bedrock_text_model,
                messages=consolidation_messages,
                system=[{"text": "You produce concise architectural descriptions for image generation. Stay under 350 characters."}],
                inference_config={"maxTokens": 150, "temperature": 0.3, "topP": 0.9},
            )
            consolidated = response["output"]["message"]["content"][0]["text"].strip()
            # Hard cap at 380 to leave room for video framing
            consolidated = consolidated[:380]
            logger.info(f"Consolidated refined prompt ({len(consolidated)} chars): {consolidated[:150]}...")
            return consolidated
        except Exception as e:
            # Fallback: use the old concatenation approach if LLM call fails
            logger.warning(f"Failed to consolidate refined prompt, using fallback: {e}")
            summary_short = descriptive_summary[:150] if descriptive_summary else "architectural space"
            return f"{summary_short}. Changes: {refinement_text}"[:380]

    def send_message(
        self, design_id: str, user_message: str, descriptive_summary: str
    ) -> ChatResponse:
        """Send a user message and get the assistant response.

        1. Load conversation history from DynamoDB
        2. Convert DB records to Converse API format
        3. Append the new user message
        4. Call converse_bedrock with full history
        5. Detect confirmation and build refined_prompt if confirmed
        6. Save both user and assistant messages to DynamoDB
        7. Return ChatResponse

        If converse_bedrock fails, no messages are saved (preserves history).
        """
        # 1. Load existing conversation history
        db_messages = self.db.get_chat_messages(design_id)

        # 2. Convert DB records to Converse API format
        messages = [
            {"role": record["role"], "content": [{"text": record["content"]}]}
            for record in db_messages
        ]

        # 3. Append the new user message
        messages.append({"role": "user", "content": [{"text": user_message}]})

        # 4. Build system prompt and call Converse API
        system = self._build_system_prompt(descriptive_summary)
        response = self.converse_bedrock(
            model_id=settings.bedrock_text_model,
            messages=messages,
            system=system,
            inference_config={
                "maxTokens": 512,
                "temperature": 0.5,
                "topP": 0.9,
            },
        )

        # 5. Extract assistant text
        assistant_text = response["output"]["message"]["content"][0]["text"]

        # 6. Detect confirmation
        confirmed = self._detect_confirmation(assistant_text, user_message)

        # 7. Build refined_prompt if confirmed
        refined_prompt = None
        if confirmed:
            # Include the new user + assistant messages in the full list
            all_messages = messages + [
                {"role": "assistant", "content": [{"text": assistant_text}]}
            ]
            refined_prompt = self._build_refined_prompt(
                descriptive_summary, all_messages
            )

        # 8. Generate UUIDs for both messages
        user_message_id = str(uuid4())
        assistant_message_id = str(uuid4())
        now = datetime.now(timezone.utc)

        # 9. Save both messages to DynamoDB
        self.db.save_chat_message(design_id, user_message_id, "user", user_message)
        self.db.save_chat_message(
            design_id, assistant_message_id, "assistant", assistant_text
        )

        # 10. Return ChatResponse
        assistant_chat_message = ChatMessage(
            message_id=assistant_message_id,
            design_id=design_id,
            role="assistant",
            content=assistant_text,
            created_at=now,
        )
        return ChatResponse(
            message=assistant_chat_message,
            ready_to_render=confirmed,
            refined_prompt=refined_prompt,
        )

    def get_history(self, design_id: str) -> list[ChatMessage]:
        """Load full conversation history from DynamoDB, ordered by SK."""
        db_messages = self.db.get_chat_messages(design_id)
        return [
            ChatMessage(
                message_id=record["message_id"],
                design_id=record["design_id"],
                role=record["role"],
                content=record["content"],
                created_at=record["created_at"],
            )
            for record in db_messages
        ]
