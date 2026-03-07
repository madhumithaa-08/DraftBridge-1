"""Property-based tests for the sketch-to-video workflow.

Each test corresponds to a correctness property from the design document.
Uses Hypothesis for property-based testing with moto for AWS mocking.
"""

import base64
import json
import time
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import boto3
import pytest
from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st
from moto import mock_aws

from app.agents.chat_agent import ChatAgent, CONFIRMATION_PHRASES
from app.agents.sketch_agent import SketchAgent
from app.agents.visualization_agent import VisualizationAgent
from app.models.render import RenderRequest
from app.models.sketch import ArchitecturalElement, Room, SketchAnalysis, TextBlock
from app.services.database_service import DatabaseService
from app.services.storage_service import StorageService
from app.utils.errors import AWSServiceError


# ---------------------------------------------------------------------------
# Hypothesis strategies for generating test data
# ---------------------------------------------------------------------------

room_name_strategy = st.sampled_from([
    "Living Room", "Kitchen", "Bedroom", "Bathroom", "Office",
    "Dining Room", "Hallway", "Garage", "Balcony", "Closet",
])

element_type_strategy = st.sampled_from([
    "window", "door", "wall", "staircase", "column", "beam", "railing",
])

room_strategy = st.builds(
    Room,
    name=room_name_strategy,
    area=st.floats(min_value=5.0, max_value=200.0, allow_nan=False),
    dimensions=st.just({"width": 5.0, "length": 5.0}),
    elements=st.lists(
        st.builds(
            ArchitecturalElement,
            type=element_type_strategy,
            label=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("L",))),
        ),
        min_size=0,
        max_size=3,
    ),
)

sketch_analysis_strategy = st.builds(
    SketchAnalysis,
    design_id=st.from_regex(r"design-[a-z0-9]{4,8}", fullmatch=True),
    rooms=st.lists(room_strategy, min_size=1, max_size=5),
    architectural_elements=st.lists(
        st.builds(
            ArchitecturalElement,
            type=element_type_strategy,
            label=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("L",))),
        ),
        min_size=1,
        max_size=5,
    ),
    text_annotations=st.just([]),
    spatial_relationships=st.just([]),
    raw_dimensions=st.just({}),
    descriptive_summary=st.just(""),
    analyzed_at=st.just(datetime.now(timezone.utc)),
)

chat_message_strategy = st.fixed_dictionaries({
    "role": st.sampled_from(["user", "assistant"]),
    "content": st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z"))),
})

uuid_strategy = st.from_regex(r"[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}", fullmatch=True)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def aws_env(aws_credentials):
    """Provide mocked AWS services for property tests."""
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="test-bucket")
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        dynamodb.create_table(
            TableName="test-designs",
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        storage = StorageService(s3, "test-bucket")
        db = DatabaseService(dynamodb, "test-designs")
        bedrock = MagicMock()
        yield s3, dynamodb, storage, db, bedrock


# ===========================================================================
# Property 1: Descriptive summary references analysis content
# Feature: sketch-to-video-workflow, Property 1: Descriptive summary references analysis content
# ===========================================================================

class TestProperty1SummaryReferencesAnalysis:
    @given(analysis=sketch_analysis_strategy)
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_summary_contains_room_names_and_element_types(self, analysis, aws_env):
        _, _, storage, db, bedrock = aws_env

        room_names = [r.name for r in analysis.rooms]
        element_types = list({e.type for e in analysis.architectural_elements})

        # Build a summary that includes all room names and at least one element type
        summary_text = f"This design features {', '.join(room_names)} with {', '.join(element_types)}."

        bedrock.invoke_model.return_value = {
            "body": MagicMock(read=lambda: json.dumps(
                {"output": {"message": {"content": [{"text": summary_text}]}}}
            ).encode())
        }

        agent = SketchAgent(bedrock, storage, db)
        result = agent._generate_descriptive_summary(analysis)

        assert isinstance(result, str)
        assert len(result) > 0
        for room_name in room_names:
            assert room_name in result


# ===========================================================================
# Property 2: Summary failure graceful degradation
# Feature: sketch-to-video-workflow, Property 2: Summary failure graceful degradation
# ===========================================================================

class TestProperty2SummaryGracefulDegradation:
    @given(analysis=sketch_analysis_strategy)
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_summary_failure_returns_empty_string_with_valid_analysis(self, analysis, aws_env):
        _, _, storage, db, bedrock = aws_env
        bedrock.invoke_model.side_effect = Exception("Bedrock unavailable")

        agent = SketchAgent(bedrock, storage, db)
        result = agent._generate_descriptive_summary(analysis)

        assert result == ""
        # Original analysis should still be valid
        assert len(analysis.rooms) >= 1
        assert len(analysis.architectural_elements) >= 1
        assert analysis.design_id is not None


# ===========================================================================
# Property 3: Full conversation history sent to Converse API
# Feature: sketch-to-video-workflow, Property 3: Full conversation history sent to Converse API
# ===========================================================================

class TestProperty3FullHistorySentToConverse:
    @given(
        prior_messages=st.lists(chat_message_strategy, min_size=0, max_size=10),
        new_message=st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=("L", "N", "Z"))),
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_converse_receives_n_plus_1_messages(self, prior_messages, new_message, aws_env):
        _, _, storage, db, bedrock = aws_env
        agent = ChatAgent(bedrock, storage, db)

        design_id = f"design-{uuid4().hex[:8]}"

        # Ensure alternating user/assistant pattern for valid conversation
        valid_messages = []
        for i, msg in enumerate(prior_messages):
            role = "user" if i % 2 == 0 else "assistant"
            valid_messages.append({"role": role, "content": msg["content"]})

        # Save prior messages to DB
        for i, msg in enumerate(valid_messages):
            msg_id = str(uuid4())
            db.save_chat_message(design_id, msg_id, msg["role"], msg["content"])
            time.sleep(0.001)  # Ensure distinct timestamps

        bedrock.converse.return_value = {
            "output": {"message": {"content": [{"text": "Noted."}]}},
            "stopReason": "end_turn",
        }

        agent.send_message(design_id, new_message, "A modern apartment")

        call_args = bedrock.converse.call_args
        messages_sent = call_args.kwargs.get("messages") or call_args[1].get("messages")

        expected_count = len(valid_messages) + 1  # prior + new user message
        assert len(messages_sent) == expected_count
        # Last message should be the new user message
        last_msg = messages_sent[-1]
        assert last_msg["role"] == "user"
        assert last_msg["content"] == [{"text": new_message}]


# ===========================================================================
# Property 4: Chat message persistence round-trip
# Feature: sketch-to-video-workflow, Property 4: Chat message persistence round-trip
# ===========================================================================

class TestProperty4ChatPersistenceRoundTrip:
    @given(
        messages=st.lists(
            st.tuples(
                st.sampled_from(["user", "assistant"]),
                st.text(min_size=1, max_size=200, alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z"))),
            ),
            min_size=1,
            max_size=10,
        ),
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_saved_messages_retrieved_in_order_with_correct_fields(self, messages, aws_env):
        _, _, storage, db, _ = aws_env
        design_id = f"design-{uuid4().hex[:8]}"

        msg_ids = []
        for role, content in messages:
            msg_id = str(uuid4())
            msg_ids.append(msg_id)
            db.save_chat_message(design_id, msg_id, role, content)
            time.sleep(0.001)  # Ensure distinct timestamps for ordering

        retrieved = db.get_chat_messages(design_id)

        assert len(retrieved) == len(messages)
        for i, (expected_role, expected_content) in enumerate(messages):
            assert retrieved[i]["role"] == expected_role
            assert retrieved[i]["content"] == expected_content
            assert retrieved[i]["design_id"] == design_id
            assert retrieved[i]["PK"] == f"DESIGN#{design_id}"
            assert retrieved[i]["SK"].startswith("CHAT#")

        # Verify chronological order
        for i in range(len(retrieved) - 1):
            assert retrieved[i]["SK"] < retrieved[i + 1]["SK"]


# ===========================================================================
# Property 5: Confirmation produces render signal with refined prompt
# Feature: sketch-to-video-workflow, Property 5: Confirmation produces render signal
# ===========================================================================

class TestProperty5ConfirmationProducesRenderSignal:
    @given(
        phrase=st.sampled_from(CONFIRMATION_PHRASES),
        summary=st.text(min_size=10, max_size=200, alphabet=st.characters(whitelist_categories=("L", "N", "Z"))),
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_confirmation_phrase_triggers_ready_to_render(self, phrase, summary, aws_env):
        _, _, storage, db, bedrock = aws_env
        agent = ChatAgent(bedrock, storage, db)
        design_id = f"design-{uuid4().hex[:8]}"

        # Mock converse to return a response with READY_TO_RENDER
        bedrock.converse.side_effect = [
            {
                "output": {"message": {"content": [{"text": "Great! [READY_TO_RENDER] Generating now."}]}},
                "stopReason": "end_turn",
            },
            # Second call for building refined prompt
            {
                "output": {"message": {"content": [{"text": f"A refined design based on {summary[:50]}"}]}},
                "stopReason": "end_turn",
            },
        ]

        response = agent.send_message(design_id, phrase, summary)

        assert response.ready_to_render is True
        assert response.refined_prompt is not None
        assert len(response.refined_prompt) > 0


# ===========================================================================
# Property 6: API failure preserves conversation history
# Feature: sketch-to-video-workflow, Property 6: API failure preserves conversation history
# ===========================================================================

class TestProperty6FailurePreservesHistory:
    @given(
        prior_count=st.integers(min_value=0, max_value=5),
    )
    @settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_bedrock_failure_leaves_history_unchanged(self, prior_count, aws_env):
        _, _, storage, db, bedrock = aws_env
        agent = ChatAgent(bedrock, storage, db)
        design_id = f"design-{uuid4().hex[:8]}"

        # Save some prior messages
        for i in range(prior_count):
            role = "user" if i % 2 == 0 else "assistant"
            db.save_chat_message(design_id, str(uuid4()), role, f"Message {i}")
            time.sleep(0.001)

        before = db.get_chat_messages(design_id)
        assert len(before) == prior_count

        # Make converse fail
        bedrock.converse.side_effect = Exception("Bedrock down")

        with pytest.raises(AWSServiceError):
            agent.send_message(design_id, "New message", "summary")

        after = db.get_chat_messages(design_id)
        assert len(after) == prior_count
        for b, a in zip(before, after):
            assert b["content"] == a["content"]
            assert b["role"] == a["role"]


# ===========================================================================
# Property 7: Refined prompt passthrough to Nova Canvas
# Feature: sketch-to-video-workflow, Property 7: Refined prompt passthrough to Nova Canvas
# ===========================================================================

class TestProperty7RefinedPromptPassthrough:
    @given(
        prompt=st.text(min_size=5, max_size=500, alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z"))),
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_refined_prompt_passed_identically_to_nova_canvas(self, prompt, aws_env):
        s3, _, storage, db, bedrock = aws_env
        agent = VisualizationAgent(bedrock, storage, db)

        fake_image = base64.b64encode(b"fake-png").decode()
        bedrock.invoke_model.return_value = {
            "body": MagicMock(read=lambda: json.dumps({"images": [fake_image]}).encode())
        }

        design_id = f"design-{uuid4().hex[:8]}"
        response = agent.generate_refined_render(prompt, design_id)

        call_args = bedrock.invoke_model.call_args
        body = json.loads(call_args.kwargs.get("body", call_args[1].get("body", "{}")))
        sent_prompt = body["textToImageParams"]["text"]

        # For prompts under 1024 chars, should be identical
        if len(prompt) <= 1024:
            assert sent_prompt == prompt
        else:
            # Truncated but starts with the same content
            assert prompt.startswith(sent_prompt.rstrip("...").rstrip())


# ===========================================================================
# Property 8: Render metadata persistence
# Feature: sketch-to-video-workflow, Property 8: Render metadata persistence
# ===========================================================================

class TestProperty8RenderMetadataPersistence:
    @given(
        prompt=st.text(min_size=5, max_size=200, alphabet=st.characters(whitelist_categories=("L", "N", "Z"))),
    )
    @settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_refined_render_persists_to_s3_and_dynamodb(self, prompt, aws_env):
        s3, _, storage, db, bedrock = aws_env
        agent = VisualizationAgent(bedrock, storage, db)

        fake_image = base64.b64encode(b"test-image-data").decode()
        bedrock.invoke_model.return_value = {
            "body": MagicMock(read=lambda: json.dumps({"images": [fake_image]}).encode())
        }

        design_id = f"design-{uuid4().hex[:8]}"
        response = agent.generate_refined_render(prompt, design_id)

        # Verify S3 has the image
        obj = s3.get_object(Bucket="test-bucket", Key=response.s3_key)
        assert obj["Body"].read() == b"test-image-data"

        # Verify DynamoDB has the metadata
        items = db.get_item_by_sk_prefix(design_id, "RENDER#")
        assert len(items) == 1
        assert items[0]["design_id"] == design_id
        assert items[0]["s3_key"] == response.s3_key
        assert items[0]["prompt_used"] == prompt


# ===========================================================================
# Property 9: Video generation parameters invariant
# Feature: sketch-to-video-workflow, Property 9: Video generation parameters invariant
# ===========================================================================

class TestProperty9VideoParamsInvariant:
    @given(analysis=sketch_analysis_strategy)
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_video_always_uses_6s_24fps_1280x720(self, analysis, aws_env):
        _, _, storage, db, bedrock = aws_env
        agent = VisualizationAgent(bedrock, storage, db)

        bedrock.start_async_invoke.return_value = {
            "invocationArn": f"arn:aws:bedrock:us-east-1:123:async/{uuid4().hex}"
        }

        agent.generate_video(analysis, analysis.design_id)

        call_args = bedrock.start_async_invoke.call_args
        body = call_args.kwargs.get("modelInput", call_args[1].get("modelInput", {}))
        config = body["videoGenerationConfig"]

        assert config["durationSeconds"] == 6
        assert config["fps"] == 24
        assert config["dimension"] == "1280x720"


# ===========================================================================
# Property 10: Video metadata persistence on completion
# Feature: sketch-to-video-workflow, Property 10: Video metadata persistence on completion
# ===========================================================================

class TestProperty10VideoMetadataOnCompletion:
    @given(analysis=sketch_analysis_strategy)
    @settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_completed_video_updates_dynamodb_with_complete_status(self, analysis, aws_env):
        s3, _, storage, db, bedrock = aws_env
        agent = VisualizationAgent(bedrock, storage, db)

        video_id = str(uuid4())
        design_id = analysis.design_id
        invocation_arn = f"arn:aws:bedrock:us-east-1:123:async/{uuid4().hex}"

        # Save initial processing metadata
        db.save_video_metadata(design_id, video_id, "processing", invocation_arn=invocation_arn)

        # Put a fake video file in S3 so _find_video_file works
        video_key = f"videos/{design_id}/{video_id}/output.mp4"
        s3.put_object(Bucket="test-bucket", Key=video_key, Body=b"fake-video")

        # Mock get_async_invoke to return Completed
        bedrock.get_async_invoke.return_value = {"status": "Completed"}

        result = agent.check_video_status(invocation_arn, video_id, design_id)

        assert result.status == "complete"
        assert result.s3_key is not None
        assert result.s3_key.endswith(".mp4")

        # Verify DynamoDB was updated
        items = db.get_item_by_sk_prefix(design_id, "VIDEO#")
        # Find the latest entry (there may be two: processing + complete)
        complete_items = [i for i in items if i.get("status") == "complete"]
        assert len(complete_items) >= 1
        assert complete_items[0]["s3_key"] is not None


# ===========================================================================
# Property 11: Non-existent design returns 404
# Feature: sketch-to-video-workflow, Property 11: Non-existent design returns 404
# ===========================================================================

class TestProperty11NonExistentDesign404:
    """Non-existent design IDs must return 404 on chat endpoints.

    Note: We use parametrize with several random UUIDs instead of Hypothesis
    @given because the async test_client fixture (which wraps mock_aws) does
    not survive across Hypothesis examples.
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize("design_id", [
        "00000000-0000-4000-8000-000000000000",
        "aaaaaaaa-bbbb-4ccc-9ddd-eeeeeeeeeeee",
        "12345678-1234-4234-8234-123456789abc",
        "deadbeef-dead-4ead-beef-deadbeefcafe",
        "abcdef01-2345-4678-9abc-def012345678",
    ])
    async def test_chat_endpoints_return_404_for_random_uuid(self, design_id, test_client):
        post_response = await test_client.post(
            f"/api/chat/{design_id}/messages",
            json={"message": "Hello"},
        )
        assert post_response.status_code == 404

        get_response = await test_client.get(f"/api/chat/{design_id}/messages")
        assert get_response.status_code == 404
