import base64
import json
from datetime import datetime, timezone

from app.agents.base_agent import BaseAgent
from app.config import settings
from app.models.sketch import (
    ArchitecturalElement,
    Room,
    SketchAnalysis,
    TextBlock,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)


def _safe_float(value) -> float | None:
    """Convert a value to float, returning None if it's not a valid number."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _clean_numeric_dict(d) -> dict[str, float] | None:
    """Sanitize a dict so all values are floats. Drops None/non-numeric entries.

    Returns None if the input isn't a dict or has no valid numeric entries.
    """
    if not isinstance(d, dict):
        return None
    cleaned = {}
    for k, v in d.items():
        f = _safe_float(v)
        if f is not None:
            cleaned[k] = f
    return cleaned if cleaned else None


TEXT_EXTRACTION_PROMPT = """Look at this architectural sketch image and extract ALL text annotations, labels, measurements, and notes written on it.

Return a JSON array of objects, each with:
- "text": the exact text string found
- "confidence": your confidence 0-100 that you read it correctly

Return ONLY valid JSON array, no markdown fences or extra text. If no text is found, return []."""

ARCHITECTURE_ANALYSIS_PROMPT = """Analyze this architectural sketch image. Identify and return a JSON object with:
1. "rooms": array of objects with "name" (string), "area" (number or null), "dimensions" (object with width/height in feet or null), and "elements" (array of architectural elements in that room)
2. "architectural_elements": array of objects with "type" (e.g. wall, door, window, staircase), "label" (string), "dimensions" (object or null), "position" (object or null)
3. "spatial_relationships": array of objects with "from" (string), "to" (string), "relationship" (string, e.g. "adjacent_to", "connected_by_door", "above")

Also consider these text annotations extracted from the sketch:
{text_annotations}

Return ONLY valid JSON, no markdown fences or extra text."""


def _media_type_to_nova_format(media_type: str) -> str:
    """Convert MIME type to Nova image format string."""
    mapping = {
        "image/png": "png",
        "image/jpeg": "jpeg",
        "image/jpg": "jpeg",
        "image/webp": "webp",
        "image/gif": "gif",
    }
    return mapping.get(media_type, "png")


class SketchAgent(BaseAgent):
    """Agent for sketch upload analysis using Bedrock vision for both text extraction and architectural analysis."""

    def __init__(self, bedrock_client, storage_service, database_service):
        super().__init__(bedrock_client, storage_service, database_service)

    def analyze(self, image_bytes: bytes, design_id: str, media_type: str = "image/png") -> SketchAnalysis:
        """Orchestrate text extraction and architectural analysis on a sketch."""
        logger.info(f"Starting sketch analysis for design {design_id}")

        text_blocks = self.extract_text(image_bytes, media_type)
        logger.info(f"Extracted {len(text_blocks)} text blocks from sketch")

        analysis = self.analyze_architecture(image_bytes, text_blocks, media_type)

        result = SketchAnalysis(
            design_id=design_id,
            rooms=analysis.get("rooms", []),
            architectural_elements=analysis.get("architectural_elements", []),
            text_annotations=text_blocks,
            spatial_relationships=analysis.get("spatial_relationships", []),
            analyzed_at=datetime.now(timezone.utc),
        )

        try:
            result.descriptive_summary = self._generate_descriptive_summary(result)
        except Exception as e:
            logger.warning(f"Failed to set descriptive summary: {e}")
            result.descriptive_summary = ""

        return result


    def _build_nova_image_body(self, image_bytes: bytes, media_type: str, prompt: str, system_text: str, max_tokens: int = 2048) -> dict:
        """Build a Nova-format request body with an image and text prompt."""
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        img_format = _media_type_to_nova_format(media_type)

        return {
            "schemaVersion": "messages-v1",
            "system": [{"text": system_text}],
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "image": {
                                "format": img_format,
                                "source": {"bytes": image_b64},
                            }
                        },
                        {"text": prompt},
                    ],
                }
            ],
            "inferenceConfig": {
                "maxTokens": max_tokens,
                "temperature": 0.3,
                "topP": 0.9,
            },
        }

    def extract_text(self, image_bytes: bytes, media_type: str = "image/png") -> list[TextBlock]:
        """Extract text annotations from a sketch image using Bedrock vision."""
        body = self._build_nova_image_body(
            image_bytes, media_type,
            prompt=TEXT_EXTRACTION_PROMPT,
            system_text="You are an expert at reading handwritten text and annotations on architectural sketches. Return only valid JSON.",
            max_tokens=2048,
        )

        response = self.invoke_bedrock(settings.bedrock_text_model, body)
        raw_text = self._extract_nova_text(response)

        items = self._parse_json(raw_text)
        if items is None:
            return []

        if not isinstance(items, list):
            logger.warning(f"Expected list from text extraction, got {type(items)}")
            return []

        text_blocks = []
        for item in items:
            if not isinstance(item, dict):
                logger.warning(f"Skipping non-dict text item: {type(item)}")
                continue
            text_blocks.append(
                TextBlock(
                    text=str(item.get("text", "")),
                    confidence=float(item.get("confidence", 80.0)),
                    bounding_box={"top": 0, "left": 0, "width": 0, "height": 0},
                )
            )
        return text_blocks

    def analyze_architecture(self, image_bytes: bytes, text_blocks: list[TextBlock], media_type: str = "image/png") -> dict:
        """Analyze architectural elements in a sketch via Bedrock."""
        text_summary = "\n".join(
            f"- \"{tb.text}\" (confidence: {tb.confidence:.1f}%)" for tb in text_blocks
        ) or "No text annotations found."

        prompt = ARCHITECTURE_ANALYSIS_PROMPT.format(text_annotations=text_summary)

        body = self._build_nova_image_body(
            image_bytes, media_type,
            prompt=prompt,
            system_text="You are an expert architect analyzing hand-drawn sketches. Return only valid JSON.",
            max_tokens=4096,
        )

        response = self.invoke_bedrock(settings.bedrock_text_model, body)
        raw_text = self._extract_nova_text(response)

        analysis = self._parse_json(raw_text)
        if analysis is None or not isinstance(analysis, dict):
            logger.warning(f"Expected dict from architecture analysis, got {type(analysis)}")
            analysis = {}

        rooms = []
        for r in analysis.get("rooms", []):
            if not isinstance(r, dict):
                logger.warning(f"Skipping non-dict room: {type(r)}")
                continue
            room_elements = []
            for e in r.get("elements", []):
                if isinstance(e, dict):
                    room_elements.append(ArchitecturalElement(
                        type=e.get("type", "unknown"),
                        label=e.get("label", ""),
                        dimensions=_clean_numeric_dict(e.get("dimensions")),
                        position=_clean_numeric_dict(e.get("position")),
                    ))
                elif isinstance(e, str):
                    room_elements.append(ArchitecturalElement(type="unknown", label=e))
                else:
                    logger.warning(f"Skipping unexpected element type: {type(e)}")
            rooms.append(Room(
                name=r.get("name", "Unknown"),
                area=_safe_float(r.get("area")),
                dimensions=_clean_numeric_dict(r.get("dimensions")),
                elements=room_elements,
            ))

        elements = []
        for e in analysis.get("architectural_elements", []):
            if isinstance(e, dict):
                elements.append(ArchitecturalElement(
                    type=e.get("type", "unknown"),
                    label=e.get("label", ""),
                    dimensions=_clean_numeric_dict(e.get("dimensions")),
                    position=_clean_numeric_dict(e.get("position")),
                ))
            elif isinstance(e, str):
                elements.append(ArchitecturalElement(type="unknown", label=e))
            else:
                logger.warning(f"Skipping unexpected element type: {type(e)}")

        relationships = []
        for rel in analysis.get("spatial_relationships", []):
            if isinstance(rel, dict):
                relationships.append({
                    "from": rel.get("from", ""),
                    "to": rel.get("to", ""),
                    "relationship": rel.get("relationship", ""),
                })
            else:
                logger.warning(f"Skipping non-dict relationship: {type(rel)}")

        return {
            "rooms": rooms,
            "architectural_elements": elements,
            "spatial_relationships": relationships,
        }

    def _generate_descriptive_summary(self, analysis: SketchAnalysis) -> str:
        """Generate a human-readable summary from structured analysis data.

        Calls Nova Lite with a text-only prompt referencing rooms, elements,
        materials, and spatial relationships. Returns empty string on any failure.
        """
        try:
            room_names = [r.name for r in analysis.rooms]
            element_types = list({e.type for e in analysis.architectural_elements})
            relationships = [
                f"{rel.get('from', '')} {rel.get('relationship', '')} {rel.get('to', '')}"
                for rel in analysis.spatial_relationships
            ]

            prompt_parts = ["Describe this architectural design in a single detailed paragraph."]
            if room_names:
                prompt_parts.append(f"Rooms detected: {', '.join(room_names)}.")
            if element_types:
                prompt_parts.append(f"Key architectural elements: {', '.join(element_types)}.")
            if relationships:
                prompt_parts.append(f"Spatial relationships: {'; '.join(relationships)}.")

            prompt = " ".join(prompt_parts)

            body = {
                "schemaVersion": "messages-v1",
                "system": [{"text": "You are an expert architect. Produce a concise, human-readable paragraph summarizing the architectural design based on the provided details."}],
                "messages": [{"role": "user", "content": [{"text": prompt}]}],
                "inferenceConfig": {"maxTokens": 1024, "temperature": 0.7, "topP": 0.9},
            }

            response = self.invoke_bedrock(settings.bedrock_text_model, body)
            summary = self._extract_nova_text(response)
            return summary if summary else ""
        except Exception as e:
            logger.warning(f"Failed to generate descriptive summary: {e}")
            return ""


    @staticmethod
    def _extract_nova_text(response: dict) -> str:
        """Extract text from a Nova response body."""
        try:
            return response["output"]["message"]["content"][0]["text"]
        except (KeyError, IndexError, TypeError):
            # Fallback: try Claude-style response format
            for block in response.get("content", []):
                if block.get("type") == "text":
                    return block.get("text", "")
            logger.warning("Could not extract text from Bedrock response")
            return ""

    @staticmethod
    def _parse_json(raw_text: str):
        """Parse JSON from model output, stripping markdown fences if needed."""
        try:
            return json.loads(raw_text)
        except json.JSONDecodeError:
            stripped = raw_text.strip()
            if stripped.startswith("```"):
                lines = stripped.split("\n")
                lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                stripped = "\n".join(lines)
                try:
                    return json.loads(stripped)
                except json.JSONDecodeError:
                    pass
            logger.warning("Bedrock response was not valid JSON")
            return None
