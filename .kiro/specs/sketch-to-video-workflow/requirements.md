# Requirements Document

## Introduction

This feature enhances DraftBridge with an end-to-end sketch-to-video workflow. After uploading an architectural sketch, users receive a rich human-readable analysis summary, generate 3D renders, refine designs through a multi-turn chat conversation with an AI assistant, and produce walkthrough videos. The chat-based refinement collects all design changes through conversation and generates a single final render only when the user confirms, avoiding wasteful intermediate renders.

## Glossary

- **Sketch_Analysis_Service**: The backend component (SketchAgent) that analyzes uploaded architectural sketches using Bedrock Nova Lite vision capabilities, producing structured data and a descriptive summary.
- **Chat_Agent**: A new backend agent class inheriting BaseAgent that manages multi-turn design refinement conversations using the Bedrock Converse API.
- **Visualization_Agent**: The backend component (VisualizationAgent) that generates photorealistic 3D renders via Nova Canvas and walkthrough videos via Nova Reel.
- **Chat_Panel**: The frontend UI component that displays the multi-turn conversation between the user and the Chat_Agent for design refinement.
- **Refined_Prompt**: A render prompt constructed by the Chat_Agent from the original sketch analysis combined with all design refinements collected during the conversation.
- **Conversation_History**: The ordered list of user and assistant messages for a design session, stored in DynamoDB.
- **Design_Session**: A single design workflow instance identified by a design_id, encompassing sketch upload, analysis, chat refinement, render generation, and video generation.
- **Video_Status_Indicator**: A frontend UI element that displays the current state of an asynchronous Nova Reel video generation job via polling.

## Requirements

### Requirement 1: Enhanced Sketch Analysis with Descriptive Summary

**User Story:** As an architect, I want to see a human-readable description of my uploaded sketch, so that I can verify the AI correctly understood my design before proceeding.

#### Acceptance Criteria

1. WHEN a sketch is uploaded and analyzed, THE Sketch_Analysis_Service SHALL return a descriptive_summary field containing a human-readable paragraph describing the detected rooms, elements, materials, and spatial layout.
2. WHEN the Sketch_Analysis_Service generates a descriptive_summary, THE descriptive_summary SHALL reference specific rooms by name, list key architectural elements detected, and describe spatial relationships in natural language.
3. WHEN the analysis is complete, THE frontend SHALL display the descriptive_summary to the user above the structured analysis data.
4. IF the Sketch_Analysis_Service fails to generate a descriptive_summary, THEN THE Sketch_Analysis_Service SHALL return an empty string for the descriptive_summary field and still return the structured analysis data.

### Requirement 2: Chat-Based Design Refinement

**User Story:** As an architect, I want to have a multi-turn conversation with an AI assistant to refine my design, so that I can iteratively improve the visualization without generating a new render for every change.

#### Acceptance Criteria

1. WHEN a user sends a message in the Chat_Panel, THE Chat_Agent SHALL process the message using the Bedrock Converse API with the full Conversation_History for the Design_Session.
2. WHEN the Chat_Agent receives a user message containing design change requests (colors, materials, lighting, layout tweaks), THE Chat_Agent SHALL acknowledge the changes, explain how the changes will affect the design, and add the changes to the accumulated refinement context.
3. WHEN the Chat_Agent receives a user message that does not contain explicit change requests, THE Chat_Agent SHALL proactively suggest design improvements based on BIM rules, natural lighting best practices, and infrastructure guidelines.
4. THE Chat_Agent SHALL maintain a running list of all accepted design refinements within the Conversation_History for the Design_Session.
5. WHEN the user confirms the design is ready (e.g., "looks good, generate it"), THE Chat_Agent SHALL construct a Refined_Prompt combining the original sketch analysis with all accumulated refinements and return a signal indicating render generation should proceed.
6. THE Chat_Panel SHALL display each message from both the user and the Chat_Agent in chronological order with clear visual distinction between user messages and assistant messages.
7. WHILE a Chat_Agent response is being generated, THE Chat_Panel SHALL display a loading indicator.
8. IF the Bedrock Converse API call fails, THEN THE Chat_Agent SHALL return an error message to the user and preserve the Conversation_History so the user can retry.

### Requirement 3: Conversation Persistence

**User Story:** As an architect, I want my chat conversation to be saved, so that I can return to a design session and see the refinement history.

#### Acceptance Criteria

1. WHEN a user sends a message in the Chat_Panel, THE Chat_Agent SHALL store the user message in the Conversation_History in DynamoDB under the Design_Session.
2. WHEN the Chat_Agent generates a response, THE Chat_Agent SHALL store the assistant message in the Conversation_History in DynamoDB under the Design_Session.
3. WHEN a user opens the Chat_Panel for an existing Design_Session, THE Chat_Panel SHALL load and display the full Conversation_History from DynamoDB.
4. THE Conversation_History SHALL use the existing DynamoDB single-table design with PK=DESIGN#{design_id} and SK=CHAT#{message_id} for each message.

### Requirement 4: Refined Render Generation

**User Story:** As an architect, I want to generate a single final 3D render that incorporates all my chat-based refinements, so that I get a visualization matching my refined vision without wasting compute on intermediate renders.

#### Acceptance Criteria

1. WHEN the Chat_Agent signals that the user has confirmed the design, THE frontend SHALL call the Visualization_Agent to generate a render using the Refined_Prompt.
2. THE Visualization_Agent SHALL accept a Refined_Prompt as an alternative to building a prompt from raw analysis data alone.
3. WHEN the refined render is generated, THE Visualization_Agent SHALL store the render in S3 and save metadata in DynamoDB following the existing render storage pattern.
4. WHEN the refined render is complete, THE frontend SHALL display the rendered image to the user.
5. IF the refined render generation fails, THEN THE Visualization_Agent SHALL return an error and THE frontend SHALL display the error message and allow the user to retry.

### Requirement 5: Video Walkthrough Generation

**User Story:** As an architect, I want to generate a walkthrough video of my final design, so that I can present the space to clients in an immersive format.

#### Acceptance Criteria

1. WHEN the user clicks "Generate Video" after a render is displayed, THE frontend SHALL call the Visualization_Agent to start an asynchronous Nova Reel video generation job.
2. THE Visualization_Agent SHALL generate a 6-second walkthrough video at 1280x720 resolution and 24fps using Nova Reel.
3. WHILE the video generation job is in progress, THE Video_Status_Indicator SHALL poll the backend at regular intervals and display the current job status to the user.
4. WHEN the video generation job completes successfully, THE frontend SHALL display the video with playback controls.
5. WHEN the video generation job completes successfully, THE Visualization_Agent SHALL store the video URL and metadata in DynamoDB following the existing video storage pattern.
6. IF the video generation job fails, THEN THE Video_Status_Indicator SHALL display an error message and allow the user to retry.

### Requirement 6: Chat API Endpoint

**User Story:** As a frontend developer, I want a dedicated chat API endpoint, so that the Chat_Panel can communicate with the Chat_Agent.

#### Acceptance Criteria

1. THE backend SHALL expose a POST /api/chat/{design_id}/messages endpoint that accepts a user message and returns the Chat_Agent response.
2. THE backend SHALL expose a GET /api/chat/{design_id}/messages endpoint that returns the full Conversation_History for a Design_Session.
3. WHEN the POST endpoint receives a message, THE endpoint SHALL validate that the design_id corresponds to an existing design.
4. WHEN the POST endpoint receives a message and the Chat_Agent response indicates the user confirmed the design, THE response SHALL include a ready_to_render flag set to true and the Refined_Prompt.
5. IF the design_id does not correspond to an existing design, THEN THE endpoint SHALL return a 404 error response.

### Requirement 7: End-to-End Workflow UI Flow

**User Story:** As an architect, I want a seamless step-by-step workflow from sketch upload to video generation, so that I can move through each stage without confusion.

#### Acceptance Criteria

1. WHEN a sketch analysis is complete, THE frontend SHALL display the descriptive_summary and a "Generate 3D Visualization" button.
2. WHEN a 3D render is displayed, THE frontend SHALL show the Chat_Panel alongside the render for design refinement.
3. WHEN a refined render is displayed, THE frontend SHALL show a "Generate Video" button.
4. THE frontend SHALL visually indicate the current workflow stage (analysis, render, chat refinement, refined render, video generation).
5. WHILE a render is being generated, THE frontend SHALL display a loading state and disable the generation button to prevent duplicate requests.
