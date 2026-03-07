# Implementation Plan: Sketch-to-Video Workflow

## Overview

Incrementally build the sketch-to-video pipeline: start with backend data models and persistence, then agents, then API routes, then frontend components, wiring everything together at the end. Each task builds on the previous so there's no orphaned code.

## Tasks

- [x] 1. Add chat Pydantic models and extend existing models
  - [x] 1.1 Create `final-updated/app/models/chat.py` with ChatMessageRequest, ChatMessage, ChatResponse, ChatHistoryResponse
    - ChatMessageRequest: `message: str` with non-empty validation
    - ChatMessage: `message_id`, `design_id`, `role` (Literal["user","assistant"]), `content`, `created_at`
    - ChatResponse: `message: ChatMessage`, `ready_to_render: bool = False`, `refined_prompt: str | None = None`
    - ChatHistoryResponse: `design_id: str`, `messages: list[ChatMessage]`
    - _Requirements: 2.5, 2.6, 3.3, 6.1, 6.4_

  - [x] 1.2 Add `descriptive_summary: str = ""` field to SketchAnalysis in `final-updated/app/models/sketch.py`
    - _Requirements: 1.1, 1.4_

  - [x] 1.3 Add `refined_prompt: str | None = None` field to RenderRequest in `final-updated/app/models/render.py`
    - _Requirements: 4.1, 4.2_

- [x] 2. Extend DatabaseService with chat persistence methods
  - [x] 2.1 Add `save_chat_message(design_id, message_id, role, content)` to `final-updated/app/services/database_service.py`
    - PK=DESIGN#{design_id}, SK=CHAT#{iso_timestamp}#{message_id}
    - Store message_id, design_id, role, content, created_at
    - _Requirements: 3.1, 3.2, 3.4_

  - [x] 2.2 Add `get_chat_messages(design_id)` to `final-updated/app/services/database_service.py`
    - Query with PK=DESIGN#{design_id} and SK begins_with("CHAT#")
    - Return messages in chronological order (SK sort)
    - _Requirements: 3.3, 3.4_

  - [ ]* 2.3 Write property test for chat message persistence round-trip
    - **Property 4: Chat message persistence round-trip**
    - **Validates: Requirements 2.4, 3.1, 3.2, 3.3, 3.4**
    - File: `final-updated/tests/test_properties/test_sketch_to_video_properties.py`
    - Use Hypothesis to generate random sequences of user/assistant messages, save them, load them, and verify order, role, content, and key pattern

  - [ ]* 2.4 Write unit tests for DatabaseService chat methods
    - File: `final-updated/tests/test_services/test_database_chat.py`
    - Test save and retrieve single message, multiple messages ordering, empty history
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 3. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Enhance SketchAgent with descriptive summary generation
  - [x] 4.1 Add `_generate_descriptive_summary(analysis)` method to SketchAgent in `final-updated/app/agents/sketch_agent.py`
    - Call Nova Lite with a prompt referencing rooms, elements, materials, spatial relationships
    - Return empty string on any failure (graceful degradation)
    - _Requirements: 1.1, 1.2, 1.4_

  - [x] 4.2 Integrate `_generate_descriptive_summary` into the existing `analyze()` method
    - Call after structured analysis is complete
    - Set `descriptive_summary` on the SketchAnalysis result
    - Wrap in try/except so failures don't break the analysis pipeline
    - _Requirements: 1.1, 1.4_

  - [ ]* 4.3 Write property test for descriptive summary references analysis content
    - **Property 1: Descriptive summary references analysis content**
    - **Validates: Requirements 1.1, 1.2**
    - Generate random SketchAnalysis with rooms and elements, verify summary is non-empty and references room names and element types

  - [ ]* 4.4 Write property test for summary failure graceful degradation
    - **Property 2: Summary failure graceful degradation**
    - **Validates: Requirements 1.4**
    - Mock Nova Lite to raise, verify SketchAnalysis still has valid structured data and descriptive_summary == ""

  - [ ]* 4.5 Write unit tests for SketchAgent summary generation
    - File: `final-updated/tests/test_agents/test_sketch_agent_summary.py`
    - Test minimal analysis (one room), complex analysis (multiple rooms/elements), failure case
    - _Requirements: 1.1, 1.2, 1.4_

- [x] 5. Implement ChatAgent
  - [x] 5.1 Create `final-updated/app/agents/chat_agent.py` with ChatAgent class inheriting BaseAgent
    - Implement `converse_bedrock(model_id, messages, system, inference_config)` with retry logic
    - Implement `_build_system_prompt(descriptive_summary)` with architectural context and refinement instructions
    - Implement `_detect_confirmation(assistant_text, user_message)` with keyword matching + [READY_TO_RENDER] signal
    - Implement `_build_refined_prompt(descriptive_summary, messages)` to combine summary with accumulated refinements
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [x] 5.2 Implement `send_message(design_id, user_message, descriptive_summary)` in ChatAgent
    - Load conversation history from DynamoDB
    - Append user message, call converse_bedrock with full history
    - Detect confirmation, build refined_prompt if confirmed
    - Save user and assistant messages to DynamoDB
    - Return ChatResponse with ready_to_render and refined_prompt when applicable
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.8, 3.1, 3.2_

  - [x] 5.3 Implement `get_history(design_id)` in ChatAgent
    - Load messages from DatabaseService, convert to ChatMessage models
    - _Requirements: 3.3_

  - [ ]* 5.4 Write property test for full conversation history sent to Converse API
    - **Property 3: Full conversation history sent to Converse API**
    - **Validates: Requirements 2.1**
    - Generate random N-message history, send new message, verify Converse API receives N+1 messages in order

  - [ ]* 5.5 Write property test for confirmation produces render signal
    - **Property 5: Confirmation produces render signal with refined prompt**
    - **Validates: Requirements 2.5, 6.4**
    - Generate conversations ending with confirmation phrases, verify ready_to_render=True and non-empty refined_prompt

  - [ ]* 5.6 Write property test for API failure preserves conversation history
    - **Property 6: API failure preserves conversation history**
    - **Validates: Requirements 2.8**
    - Mock Bedrock to fail, verify DynamoDB state unchanged after the failed call

  - [ ]* 5.7 Write unit tests for ChatAgent
    - File: `final-updated/tests/test_agents/test_chat_agent.py`
    - Test confirmation detection with various phrasings, system prompt content, Converse API message format, error handling
    - _Requirements: 2.1, 2.2, 2.3, 2.5, 2.8_

- [x] 6. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Enhance VisualizationAgent with refined render method
  - [x] 7.1 Add `generate_refined_render(refined_prompt, design_id)` to VisualizationAgent in `final-updated/app/agents/visualization_agent.py`
    - Use refined_prompt directly as the Nova Canvas prompt (no prompt building)
    - Store render in S3 and save metadata in DynamoDB following existing pattern
    - _Requirements: 4.1, 4.2, 4.3_

  - [ ]* 7.2 Write property test for refined prompt passthrough
    - **Property 7: Refined prompt passthrough to Nova Canvas**
    - **Validates: Requirements 4.2**
    - Generate random prompt strings, verify the exact string is passed to invoke_model

  - [ ]* 7.3 Write property test for render metadata persistence
    - **Property 8: Render metadata persistence**
    - **Validates: Requirements 4.3**
    - Verify S3 contains render image and DynamoDB has RENDER# item with matching fields

  - [ ]* 7.4 Write property test for video generation parameters invariant
    - **Property 9: Video generation parameters invariant**
    - **Validates: Requirements 5.2**
    - Verify Nova Reel start_async_invoke receives durationSeconds=6, fps=24, dimension="1280x720"

  - [ ]* 7.5 Write property test for video metadata persistence on completion
    - **Property 10: Video metadata persistence on completion**
    - **Validates: Requirements 5.5**
    - Verify DynamoDB VIDEO# item has status="complete" and non-empty s3_key after successful job

  - [ ]* 7.6 Write unit tests for refined render and video generation
    - File: `final-updated/tests/test_agents/test_visualization_refined.py`
    - Test refined render with specific prompt, metadata storage, error propagation
    - _Requirements: 4.2, 4.3, 5.2, 5.5_

- [x] 8. Create chat router and wire dependencies
  - [x] 8.1 Add `get_chat_agent` factory to `final-updated/app/dependencies.py`
    - Inject bedrock client, storage service, database service into ChatAgent
    - _Requirements: 6.1_

  - [x] 8.2 Create `final-updated/app/routers/chat.py` with POST and GET endpoints
    - POST `/{design_id}/messages`: validate design_id exists, call ChatAgent.send_message, return ChatResponse
    - GET `/{design_id}/messages`: load history, return ChatHistoryResponse
    - Return 404 for non-existent design_id
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [x] 8.3 Register chat router in `final-updated/app/main.py`
    - Import and include the chat router
    - _Requirements: 6.1_

  - [x] 8.4 Update renders router to handle refined_prompt in RenderRequest
    - When refined_prompt is provided, call `generate_refined_render()` instead of `generate_render()`
    - _Requirements: 4.1, 4.2_

  - [ ]* 8.5 Write property test for non-existent design returns 404
    - **Property 11: Non-existent design returns 404**
    - **Validates: Requirements 6.3, 6.5**
    - Generate random UUIDs, verify both POST and GET return 404

  - [ ]* 8.6 Write unit tests for chat router
    - File: `final-updated/tests/test_routers/test_chat_router.py`
    - Test POST 200, POST 404, GET empty, GET ordered, POST 422 empty body
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 9. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Build frontend ChatPanel component
  - [x] 10.1 Create `final-updated/frontend/src/components/ChatPanel.tsx`
    - Display messages with visual distinction (user right-aligned, assistant left-aligned)
    - Text input with send button
    - Loading indicator while waiting for response
    - Load existing history on mount via GET /api/chat/{design_id}/messages
    - Detect ready_to_render in response and call onReadyToRender callback with refined_prompt
    - _Requirements: 2.6, 2.7, 3.3, 7.2_

- [x] 11. Build frontend VideoStatusIndicator component
  - [x] 11.1 Create `final-updated/frontend/src/components/VideoStatusIndicator.tsx`
    - Poll GET /api/videos/{video_id} at 5-second intervals
    - Show states: "Processing...", "Complete", "Failed"
    - On completion, render `<video>` element with playback controls
    - On failure, show error message with retry button
    - _Requirements: 5.3, 5.4, 5.6_

- [x] 12. Integrate workflow into SketchUploader
  - [x] 12.1 Update `final-updated/frontend/src/components/SketchUploader.tsx` with end-to-end workflow
    - After analysis: display descriptive_summary above structured data + "Generate 3D Visualization" button
    - After initial render: show ChatPanel alongside the render
    - After refined render: show "Generate Video" button
    - Add workflow stage indicator (analysis → render → chat refinement → refined render → video)
    - Loading states and button disabling during generation
    - _Requirements: 1.3, 7.1, 7.2, 7.3, 7.4, 7.5_

  - [x] 12.2 Wire ChatPanel's onReadyToRender to call POST /api/renders with refined_prompt
    - _Requirements: 4.1, 4.4_

  - [x] 12.3 Wire "Generate Video" button to call POST /api/videos and show VideoStatusIndicator
    - _Requirements: 5.1, 5.3, 5.4_

- [x] 13. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- All property tests go in `final-updated/tests/test_properties/test_sketch_to_video_properties.py`
