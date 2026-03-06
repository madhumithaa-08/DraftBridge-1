import json
from datetime import datetime, timezone
from uuid import uuid4

from app.agents.base_agent import BaseAgent
from app.config import settings
from app.models.compliance import (
    AccessibilityReport,
    ComplianceReport,
    EnergyReport,
    Violation,
)
from app.models.sketch import SketchAnalysis
from app.utils.logging import get_logger

logger = get_logger(__name__)


COMPLIANCE_PROMPT = """You are a building code compliance expert. Analyze the following architectural design against these building codes: {codes}.

Design details:
- Rooms: {rooms}
- Architectural elements: {elements}
- Dimensions: {dimensions}

Check against {code_names} and return a JSON object with:
{{
  "overall_pass": true/false,
  "compliance_score": 0-100,
  "violations": [
    {{
      "code_category": "string (which code was violated)",
      "severity": "critical|high|medium|low",
      "description": "string",
      "location": "string or null",
      "remediation": "string"
    }}
  ],
  "checked_codes": ["list of code names checked"]
}}

Return ONLY valid JSON, no markdown fences or extra text."""


ACCESSIBILITY_PROMPT = """You are an ADA accessibility compliance expert. Analyze the following architectural design for ADA compliance.

Design details:
- Rooms: {rooms}
- Architectural elements: {elements}
- Dimensions: {dimensions}

Focus on:
- Doorway widths (minimum 32 inches clear width)
- Ramp requirements (slopes, handrails)
- Clearances (turning radius, maneuvering space)
- Bathroom accessibility (grab bars, clearances)
- Hallway widths
- Threshold heights

Return a JSON object with:
{{
  "ada_compliant": true/false,
  "issues": [
    {{
      "category": "string",
      "description": "string",
      "location": "string",
      "severity": "critical|high|medium|low"
    }}
  ],
  "remediation_suggestions": ["list of suggestions"]
}}

Return ONLY valid JSON, no markdown fences or extra text."""


ENERGY_PROMPT = """You are an energy efficiency expert. Analyze the following architectural design for energy efficiency.

Design details:
- Rooms: {rooms}
- Architectural elements: {elements}
- Dimensions: {dimensions}

Focus on:
- Window-to-wall ratio and placement
- Insulation considerations
- HVAC efficiency based on layout
- Building orientation and natural lighting
- Thermal bridging risks

Return a JSON object with:
{{
  "efficiency_score": 0-100,
  "findings": [
    {{
      "category": "string",
      "description": "string",
      "impact": "high|medium|low"
    }}
  ],
  "recommendations": ["list of improvement recommendations"]
}}

Return ONLY valid JSON, no markdown fences or extra text."""


class ComplianceAgent(BaseAgent):
    """Agent for building code compliance, ADA accessibility, and energy efficiency analysis."""

    def _summarize_analysis(self, analysis: SketchAnalysis) -> dict[str, str]:
        """Extract room names, element types, and dimensions from analysis for prompts."""
        room_parts = []
        for room in analysis.rooms:
            desc = room.name
            if room.area:
                desc += f" ({room.area} sq ft)"
            if room.dimensions:
                dims = ", ".join(f"{k}: {v}" for k, v in room.dimensions.items())
                desc += f" [{dims}]"
            if room.elements:
                elem_names = [e.label or e.type for e in room.elements]
                desc += f" with {', '.join(elem_names)}"
            room_parts.append(desc)

        element_parts = []
        for elem in analysis.architectural_elements:
            desc = f"{elem.type}: {elem.label}"
            if elem.dimensions:
                dims = ", ".join(f"{k}: {v}" for k, v in elem.dimensions.items())
                desc += f" [{dims}]"
            element_parts.append(desc)

        dims_text = json.dumps(analysis.raw_dimensions) if analysis.raw_dimensions else "No raw dimensions available"

        return {
            "rooms": "; ".join(room_parts) if room_parts else "No rooms identified",
            "elements": "; ".join(element_parts) if element_parts else "No elements identified",
            "dimensions": dims_text,
        }

    def _build_nova_text_body(self, prompt: str, system_text: str, max_tokens: int = 4096) -> dict:
        """Build a Nova-format request body for text-only prompts."""
        return {
            "schemaVersion": "messages-v1",
            "system": [{"text": system_text}],
            "messages": [
                {
                    "role": "user",
                    "content": [{"text": prompt}],
                }
            ],
            "inferenceConfig": {
                "maxTokens": max_tokens,
                "temperature": 0.3,
                "topP": 0.9,
            },
        }

    def _parse_bedrock_response(self, response: dict) -> dict:
        """Extract and parse JSON from Nova Bedrock response text."""
        # Nova format: response["output"]["message"]["content"][0]["text"]
        raw_text = ""
        try:
            raw_text = response["output"]["message"]["content"][0]["text"]
        except (KeyError, IndexError, TypeError):
            # Fallback: try Claude-style format
            for content_block in response.get("content", []):
                if content_block.get("type") == "text":
                    raw_text += content_block.get("text", "")

        # Strip markdown fences if present
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
            logger.warning("Bedrock response was not valid JSON, returning empty dict")
            return {}

    def check_compliance(self, analysis: SketchAnalysis, codes: list[str]) -> ComplianceReport:
        """Check design against specified building codes."""
        report_id = str(uuid4())
        design_id = analysis.design_id
        logger.info(f"Running compliance check {report_id} for design {design_id} against {codes}")

        summary = self._summarize_analysis(analysis)
        code_names = ", ".join(codes)

        prompt = COMPLIANCE_PROMPT.format(
            codes=code_names,
            rooms=summary["rooms"],
            elements=summary["elements"],
            dimensions=summary["dimensions"],
            code_names=code_names,
        )

        body = self._build_nova_text_body(
            prompt=prompt,
            system_text="You are a building code compliance expert. Return only valid JSON.",
        )

        response = self.invoke_bedrock(settings.bedrock_text_model, body)
        data = self._parse_bedrock_response(response)

        violations = []
        for v in data.get("violations", []):
            if not isinstance(v, dict):
                logger.warning(f"Skipping non-dict violation: {type(v)}")
                continue
            violations.append(Violation(
                code_category=v.get("code_category", "unknown"),
                severity=v.get("severity", "medium"),
                description=v.get("description", ""),
                location=v.get("location"),
                remediation=v.get("remediation", ""),
            ))

        report = ComplianceReport(
            report_id=report_id,
            design_id=design_id,
            version=1,
            overall_pass=data.get("overall_pass", False),
            compliance_score=float(data.get("compliance_score", 0)),
            violations=violations,
            checked_codes=data.get("checked_codes", codes),
            generated_at=datetime.now(timezone.utc),
        )

        self.db.save_compliance_report(
            design_id=design_id,
            report_id=report_id,
            report_type="building_code",
            report_data=report.model_dump(mode="json"),
            version=report.version,
        )

        return report

    def validate_accessibility(self, analysis: SketchAnalysis) -> AccessibilityReport:
        """Validate ADA accessibility standards for a design."""
        report_id = str(uuid4())
        design_id = analysis.design_id
        logger.info(f"Running ADA validation {report_id} for design {design_id}")

        summary = self._summarize_analysis(analysis)

        prompt = ACCESSIBILITY_PROMPT.format(
            rooms=summary["rooms"],
            elements=summary["elements"],
            dimensions=summary["dimensions"],
        )

        body = self._build_nova_text_body(
            prompt=prompt,
            system_text="You are an ADA accessibility compliance expert. Return only valid JSON.",
        )

        response = self.invoke_bedrock(settings.bedrock_text_model, body)
        data = self._parse_bedrock_response(response)

        report = AccessibilityReport(
            report_id=report_id,
            design_id=design_id,
            version=1,
            ada_compliant=data.get("ada_compliant", False),
            issues=data.get("issues", []),
            remediation_suggestions=data.get("remediation_suggestions", []),
            generated_at=datetime.now(timezone.utc),
        )

        self.db.save_compliance_report(
            design_id=design_id,
            report_id=report_id,
            report_type="ada",
            report_data=report.model_dump(mode="json"),
            version=report.version,
        )

        return report

    def analyze_energy(self, analysis: SketchAnalysis) -> EnergyReport:
        """Analyze energy efficiency of a design."""
        report_id = str(uuid4())
        design_id = analysis.design_id
        logger.info(f"Running energy analysis {report_id} for design {design_id}")

        summary = self._summarize_analysis(analysis)

        prompt = ENERGY_PROMPT.format(
            rooms=summary["rooms"],
            elements=summary["elements"],
            dimensions=summary["dimensions"],
        )

        body = self._build_nova_text_body(
            prompt=prompt,
            system_text="You are an energy efficiency expert. Return only valid JSON.",
        )

        response = self.invoke_bedrock(settings.bedrock_text_model, body)
        data = self._parse_bedrock_response(response)

        report = EnergyReport(
            report_id=report_id,
            design_id=design_id,
            version=1,
            efficiency_score=float(data.get("efficiency_score", 0)),
            findings=data.get("findings", []),
            recommendations=data.get("recommendations", []),
            generated_at=datetime.now(timezone.utc),
        )

        self.db.save_compliance_report(
            design_id=design_id,
            report_id=report_id,
            report_type="energy",
            report_data=report.model_dump(mode="json"),
            version=report.version,
        )

        return report
