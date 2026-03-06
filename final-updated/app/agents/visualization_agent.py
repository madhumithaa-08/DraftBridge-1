import base64
from datetime import datetime, timezone
from uuid import uuid4

from botocore.exceptions import ClientError

from app.agents.base_agent import BaseAgent
from app.config import settings
from app.models.render import RenderRequest, RenderResponse
from app.models.sketch import SketchAnalysis
from app.models.video import VideoResponse
from app.utils.errors import AWSServiceError
from app.utils.logging import get_logger

logger = get_logger(__name__)


class VisualizationAgent(BaseAgent):
    """Agent for render generation (Nova Canvas) and video generation (Nova Reel)."""

    def generate_render(self, analysis: SketchAnalysis, options: RenderRequest) -> RenderResponse:
        """Generate a photorealistic render via Nova Canvas.

        Builds a prompt from the sketch analysis and render options, invokes
        Nova Canvas, stores the resulting image in S3, and saves metadata.

        Args:
            analysis: The sketch analysis containing rooms and elements.
            options: Render customization options (style, materials, lighting).

        Returns:
            RenderResponse with render details and presigned image URL.
        """
        render_id = str(uuid4())
        design_id = analysis.design_id

        prompt = self.build_render_prompt(analysis, options)
        logger.info(f"Generating render {render_id} for design {design_id}")

        body = {
            "taskType": "TEXT_IMAGE",
            "textToImageParams": {"text": prompt},
            "imageGenerationConfig": {
                "numberOfImages": 1,
                "width": 1024,
                "height": 1024,
            },
        }

        response = self.invoke_bedrock(settings.bedrock_image_model, body)

        images = response.get("images", [])
        if not images:
            raise AWSServiceError("Bedrock", "invoke_model", "No images returned from Nova Canvas")

        image_bytes = base64.b64decode(images[0])

        s3_key = self.storage.store_file(
            image_bytes, "renders/", f"{render_id}.png", "image/png"
        )

        self.db.save_render_metadata(
            design_id, render_id, s3_key, prompt, options.style
        )

        image_url = self.storage.generate_presigned_url(s3_key)

        return RenderResponse(
            render_id=render_id,
            design_id=design_id,
            image_url=image_url,
            s3_key=s3_key,
            prompt_used=prompt,
            created_at=datetime.now(timezone.utc),
        )

    def build_render_prompt(self, analysis: SketchAnalysis, options: RenderRequest) -> str:
        """Construct a detailed prompt from analysis data and render options.

        Args:
            analysis: The sketch analysis with rooms and architectural elements.
            options: Render customization (style, materials, lighting).

        Returns:
            A prompt string for Nova Canvas.
        """
        room_descriptions = []
        for room in analysis.rooms:
            desc = room.name
            if room.area:
                desc += f" ({room.area} sq ft)"
            if room.elements:
                element_names = [e.label or e.type for e in room.elements]
                desc += f" with {', '.join(element_names)}"
            room_descriptions.append(desc)

        rooms_text = "; ".join(room_descriptions) if room_descriptions else "an architectural space"

        materials_text = ""
        if options.materials:
            material_parts = [f"{k}: {v}" for k, v in options.materials.items()]
            materials_text = f" Materials: {', '.join(material_parts)}."

        prompt = (
            f"Create a {options.style} architectural visualization of a space with: "
            f"{rooms_text}.{materials_text} Lighting: {options.lighting}."
        )

        return prompt

    def generate_video(self, analysis: SketchAnalysis, design_id: str) -> VideoResponse:
        """Start async video generation via Nova Reel.

        Builds a video prompt from the analysis, starts an async Bedrock
        invocation, and saves metadata with status=processing.

        Args:
            analysis: The sketch analysis containing rooms and elements.
            design_id: The design identifier.

        Returns:
            VideoResponse with status="processing" and the invocation ARN.
        """
        video_id = str(uuid4())

        prompt = self._build_video_prompt(analysis)
        logger.info(f"Starting video generation {video_id} for design {design_id}")

        s3_output = f"s3://{settings.s3_bucket_name}/videos/{design_id}/{video_id}/"

        body = {
            "taskType": "TEXT_VIDEO",
            "textToVideoParams": {"text": prompt},
            "videoGenerationConfig": {
                "durationSeconds": 6,
                "fps": 24,
                "dimension": "1280x720",
            },
        }

        invocation_arn = self.invoke_bedrock_async(
            settings.bedrock_video_model, body, s3_output
        )

        self.db.save_video_metadata(
            design_id, video_id, status="processing", invocation_arn=invocation_arn
        )

        return VideoResponse(
            video_id=video_id,
            design_id=design_id,
            status="processing",
            invocation_arn=invocation_arn,
            created_at=datetime.now(timezone.utc),
        )

    def check_video_status(self, invocation_arn: str, video_id: str, design_id: str) -> VideoResponse:
        """Poll Nova Reel job status and update metadata accordingly.

        Args:
            invocation_arn: The ARN from the async invocation.
            video_id: The video identifier.
            design_id: The design identifier.

        Returns:
            VideoResponse with current status and video URL if complete.
        """
        try:
            response = self.bedrock.get_async_invoke(invocationArn=invocation_arn)
        except ClientError as e:
            logger.error(f"Bedrock get_async_invoke failed: {e}")
            raise AWSServiceError("Bedrock", "get_async_invoke", str(e))

        status = response.get("status", "InProgress")
        now = datetime.now(timezone.utc)

        if status == "Completed":
            s3_key = f"videos/{design_id}/{video_id}/output.mp4"
            self.db.save_video_metadata(
                design_id, video_id, status="complete", s3_key=s3_key
            )
            video_url = self.storage.generate_presigned_url(s3_key)
            return VideoResponse(
                video_id=video_id,
                design_id=design_id,
                status="complete",
                video_url=video_url,
                s3_key=s3_key,
                invocation_arn=invocation_arn,
                created_at=now,
            )
        elif status == "Failed":
            self.db.save_video_metadata(
                design_id, video_id, status="failed"
            )
            return VideoResponse(
                video_id=video_id,
                design_id=design_id,
                status="failed",
                invocation_arn=invocation_arn,
                created_at=now,
            )
        else:
            return VideoResponse(
                video_id=video_id,
                design_id=design_id,
                status="processing",
                invocation_arn=invocation_arn,
                created_at=now,
            )

    def _build_video_prompt(self, analysis: SketchAnalysis) -> str:
        """Construct a video prompt from the sketch analysis.

        Args:
            analysis: The sketch analysis with rooms and elements.

        Returns:
            A prompt string for Nova Reel.
        """
        room_names = [room.name for room in analysis.rooms]
        element_types = list({e.type for e in analysis.architectural_elements})

        rooms_text = ", ".join(room_names) if room_names else "an architectural space"
        elements_text = ", ".join(element_types) if element_types else "standard architectural features"

        return (
            f"A smooth walkthrough video of an architectural space featuring: {rooms_text}. "
            f"The space includes {elements_text}. "
            "Camera moves slowly through the space showing each room in detail with natural lighting."
        )
