import json
import uuid
from datetime import datetime, timezone

from app.agents.base_agent import BaseAgent
from app.models.export import ExportRequest, ExportResponse
from app.models.sketch import SketchAnalysis
from app.utils.errors import UnsupportedFormatError
from app.utils.logging import get_logger

logger = get_logger(__name__)

CONTENT_TYPES = {
    "DXF": "application/dxf",
    "DWG": "application/acad",
    "RVT": "application/octet-stream",
    "IFC": "application/x-step",
}


class ExportAgent(BaseAgent):
    """Handles CAD/BIM file generation from architectural analysis data."""

    SUPPORTED_FORMATS = {"DWG", "DXF", "RVT", "IFC"}

    def export(self, analysis: SketchAnalysis, format: str, design_id: str) -> ExportResponse:
        """Generate export file in requested format, store in S3, save metadata."""
        fmt = format.upper()
        if fmt not in self.SUPPORTED_FORMATS:
            raise UnsupportedFormatError(format, self.SUPPORTED_FORMATS)

        export_id = str(uuid.uuid4())

        generators = {
            "DXF": self.generate_dxf,
            "DWG": self.generate_dwg,
            "RVT": self.generate_rvt,
            "IFC": self.generate_ifc,
        }
        file_bytes = generators[fmt](analysis)

        content_type = CONTENT_TYPES[fmt]
        s3_key = self.storage.store_file(
            file_bytes, "exports/", f"{export_id}.{fmt.lower()}", content_type
        )

        self.db.save_export_metadata(design_id, export_id, fmt, s3_key, "complete")

        download_url = self.storage.generate_presigned_url(s3_key)

        now = datetime.now(timezone.utc)
        return ExportResponse(
            export_id=export_id,
            design_id=design_id,
            format=fmt,
            status="complete",
            download_url=download_url,
            s3_key=s3_key,
            created_at=now,
        )

    def generate_dxf(self, analysis: SketchAnalysis) -> bytes:
        """Generate a minimal DXF file from architectural elements.

        Produces valid DXF with HEADER, ENTITIES (LINE entities for walls),
        and EOF sections using plain text format.
        """
        lines: list[str] = []

        # HEADER section
        lines.extend([
            "0", "SECTION",
            "2", "HEADER",
            "9", "$ACADVER",
            "1", "AC1009",
            "0", "ENDSEC",
        ])

        # ENTITIES section
        lines.extend(["0", "SECTION", "2", "ENTITIES"])

        for room in analysis.rooms:
            dims = room.dimensions or {}
            width = dims.get("width", 10.0)
            height = dims.get("height", 10.0)
            x_off = dims.get("x", 0.0)
            y_off = dims.get("y", 0.0)

            corners = [
                (x_off, y_off),
                (x_off + width, y_off),
                (x_off + width, y_off + height),
                (x_off, y_off + height),
            ]
            for i in range(4):
                x1, y1 = corners[i]
                x2, y2 = corners[(i + 1) % 4]
                lines.extend([
                    "0", "LINE",
                    "8", room.name,
                    "10", str(x1), "20", str(y1), "30", "0.0",
                    "11", str(x2), "21", str(y2), "31", "0.0",
                ])

        for elem in analysis.architectural_elements:
            pos = elem.position or {}
            x = pos.get("x", 0.0)
            y = pos.get("y", 0.0)
            dims = elem.dimensions or {}
            w = dims.get("width", 1.0)
            lines.extend([
                "0", "LINE",
                "8", elem.type,
                "10", str(x), "20", str(y), "30", "0.0",
                "11", str(x + w), "21", str(y), "31", "0.0",
            ])

        lines.extend(["0", "ENDSEC"])

        # EOF
        lines.extend(["0", "EOF"])

        return "\n".join(lines).encode("utf-8")

    def generate_dwg(self, analysis: SketchAnalysis) -> bytes:
        """Generate DWG-compatible bytes.

        DWG is a proprietary Autodesk format. For MVP, we produce a
        DXF-compatible payload with a DWG header marker. In production
        this would use a proper DWG conversion library.
        """
        dxf_bytes = self.generate_dxf(analysis)
        header = b"DWG-MVP-HEADER\n"
        return header + dxf_bytes

    def generate_rvt(self, analysis: SketchAnalysis) -> bytes:
        """Generate a structured JSON representation for RVT.

        RVT is a proprietary Revit format. For MVP we produce a JSON
        document describing the architectural elements in a Revit-like
        structure that could be imported by a conversion tool.
        """
        data = {
            "format": "RVT-JSON",
            "version": "1.0",
            "design_id": analysis.design_id,
            "rooms": [
                {
                    "name": room.name,
                    "area": room.area,
                    "dimensions": room.dimensions,
                    "elements": [
                        {"type": e.type, "label": e.label, "dimensions": e.dimensions, "position": e.position}
                        for e in room.elements
                    ],
                }
                for room in analysis.rooms
            ],
            "elements": [
                {"type": e.type, "label": e.label, "dimensions": e.dimensions, "position": e.position}
                for e in analysis.architectural_elements
            ],
        }
        return json.dumps(data, indent=2, default=str).encode("utf-8")

    def generate_ifc(self, analysis: SketchAnalysis) -> bytes:
        """Generate a basic IFC-STEP format file with room and element data.

        Produces a minimal IFC 2x3 STEP file with HEADER and DATA sections.
        """
        lines: list[str] = []

        # IFC STEP header
        lines.append("ISO-10303-21;")
        lines.append("HEADER;")
        lines.append("FILE_DESCRIPTION(('DraftBridge IFC Export'),'2;1');")
        lines.append(f"FILE_NAME('{analysis.design_id}.ifc','',('DraftBridge'),(''),'',' ','');")
        lines.append("FILE_SCHEMA(('IFC2X3'));")
        lines.append("ENDSEC;")
        lines.append("DATA;")

        entity_id = 1

        # Project
        lines.append(f"#{entity_id}=IFCPROJECT('{analysis.design_id}',#0,'DraftBridge Export',$,$,$,$,$,$);")
        project_id = entity_id
        entity_id += 1

        # Rooms as IfcSpace
        for room in analysis.rooms:
            area_str = str(room.area) if room.area else "0.0"
            lines.append(
                f"#{entity_id}=IFCSPACE('{room.name}',#{project_id},'{room.name}',$,$,$,$,{area_str},$);")
            room_entity_id = entity_id
            entity_id += 1

            # Elements within room
            for elem in room.elements:
                lines.append(
                    f"#{entity_id}=IFCBUILDINGELEMENT('{elem.label}',#{room_entity_id},'{elem.type}',$,$,$,$,$);")
                entity_id += 1

        # Top-level elements
        for elem in analysis.architectural_elements:
            lines.append(
                f"#{entity_id}=IFCBUILDINGELEMENT('{elem.label}',#{project_id},'{elem.type}',$,$,$,$,$);")
            entity_id += 1

        lines.append("ENDSEC;")
        lines.append("END-ISO-10303-21;")

        return "\n".join(lines).encode("utf-8")
