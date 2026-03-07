import io
import uuid
from datetime import datetime, timezone

import ezdxf

from app.agents.base_agent import BaseAgent
from app.models.export import ExportRequest, ExportResponse
from app.models.sketch import SketchAnalysis, Room, ArchitecturalElement
from app.utils.errors import UnsupportedFormatError
from app.utils.logging import get_logger

logger = get_logger(__name__)

CONTENT_TYPES = {
    "DXF": "application/dxf",
    "IFC": "application/x-step",
    "OBJ": "text/plain",
}

WALL_HEIGHT = 3.0  # meters


class ExportAgent(BaseAgent):
    """Handles CAD/BIM file generation from architectural analysis data."""

    SUPPORTED_FORMATS = {"DXF", "IFC", "OBJ"}

    def export(self, analysis: SketchAnalysis, format: str, design_id: str) -> ExportResponse:
        """Generate export file in requested format, store in S3, save metadata."""
        fmt = format.upper()
        if fmt not in self.SUPPORTED_FORMATS:
            raise UnsupportedFormatError(format, self.SUPPORTED_FORMATS)

        export_id = str(uuid.uuid4())

        generators = {
            "DXF": self.generate_dxf,
            "IFC": self.generate_ifc,
            "OBJ": self.generate_obj,
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

    # ── Helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _room_rect(room: Room) -> tuple[float, float, float, float]:
        """Return (x, y, width, height) for a room, with safe defaults."""
        dims = room.dimensions or {}
        x = float(dims.get("x", 0.0) or 0.0)
        y = float(dims.get("y", 0.0) or 0.0)
        w = float(dims.get("width", 4.0) or 4.0)
        h = float(dims.get("height", 4.0) or 4.0)
        return x, y, w, h

    @staticmethod
    def _elem_pos(elem: ArchitecturalElement) -> tuple[float, float, float]:
        """Return (x, y, width) for an element."""
        pos = elem.position or {}
        dims = elem.dimensions or {}
        x = float(pos.get("x", 0.0) or 0.0)
        y = float(pos.get("y", 0.0) or 0.0)
        w = float(dims.get("width", 1.0) or 1.0)
        return x, y, w

    # ── DXF (ezdxf) ─────────────────────────────────────────────────────

    def generate_dxf(self, analysis: SketchAnalysis) -> bytes:
        """Generate a proper DXF R2010 file using ezdxf.

        Creates layers per room, LINE entities for walls, TEXT for labels,
        and typed layers for architectural elements (doors, windows, etc.).
        """
        doc = ezdxf.new("R2010")
        msp = doc.modelspace()

        # Create element-type layers with distinct colors
        layer_colors = {"door": 1, "window": 3, "staircase": 5, "wall": 7}
        for lname, color in layer_colors.items():
            doc.layers.add(lname, color=color)

        for room in analysis.rooms:
            x, y, w, h = self._room_rect(room)
            layer_name = room.name.replace(" ", "_")

            # Create layer for this room (color 2 = yellow)
            if layer_name not in doc.layers:
                doc.layers.add(layer_name, color=2)

            # Four wall lines
            corners = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
            for i in range(4):
                msp.add_line(corners[i], corners[(i + 1) % 4], dxfattribs={"layer": layer_name})

            # Room label at center
            msp.add_text(
                room.name,
                dxfattribs={
                    "layer": layer_name,
                    "height": 0.3,
                    "insert": (x + w / 2, y + h / 2),
                },
            )

            # Dimension lines (width along bottom, height along left)
            msp.add_line((x, y - 0.5), (x + w, y - 0.5), dxfattribs={"layer": layer_name})
            msp.add_text(
                f"{w:.1f}m",
                dxfattribs={"layer": layer_name, "height": 0.2, "insert": (x + w / 2, y - 0.8)},
            )
            msp.add_line((x - 0.5, y), (x - 0.5, y + h), dxfattribs={"layer": layer_name})
            msp.add_text(
                f"{h:.1f}m",
                dxfattribs={"layer": layer_name, "height": 0.2, "insert": (x - 1.0, y + h / 2)},
            )

            # Elements within room
            for elem in room.elements:
                ex, ey, ew = self._elem_pos(elem)
                etype = elem.type.lower()
                elayer = etype if etype in layer_colors else layer_name
                msp.add_line((ex, ey), (ex + ew, ey), dxfattribs={"layer": elayer})
                msp.add_text(
                    elem.label or elem.type,
                    dxfattribs={"layer": elayer, "height": 0.15, "insert": (ex, ey + 0.2)},
                )

        # Top-level architectural elements
        for elem in analysis.architectural_elements:
            ex, ey, ew = self._elem_pos(elem)
            etype = elem.type.lower()
            elayer = etype if etype in layer_colors else "0"
            msp.add_line((ex, ey), (ex + ew, ey), dxfattribs={"layer": elayer})

        buf = io.BytesIO()
        doc.write(buf)
        return buf.getvalue()

    # ── IFC (ifcopenshell) ───────────────────────────────────────────────

    def generate_ifc(self, analysis: SketchAnalysis) -> bytes:
        """Generate a proper IFC2X3 file using ifcopenshell.

        Hierarchy: IfcProject → IfcSite → IfcBuilding → IfcBuildingStorey
        Rooms become IfcSpace, walls get extruded geometry via IfcWall.
        """
        import ifcopenshell
        import ifcopenshell.api

        ifc = ifcopenshell.api.run("project.create_file", version="IFC2X3")

        # Project hierarchy
        project = ifcopenshell.api.run("root.create_entity", ifc, ifc_class="IfcProject", name="DraftBridge Export")
        ifcopenshell.api.run("unit.assign_unit", ifc, project=project)
        ctx = ifcopenshell.api.run("context.add_context", ifc, context_type="Model")
        body_ctx = ifcopenshell.api.run(
            "context.add_context", ifc,
            context_type="Model",
            context_identifier="Body",
            target_view="MODEL_VIEW",
            parent=ctx,
        )

        site = ifcopenshell.api.run("root.create_entity", ifc, ifc_class="IfcSite", name="Site")
        building = ifcopenshell.api.run("root.create_entity", ifc, ifc_class="IfcBuilding", name="Building")
        storey = ifcopenshell.api.run(
            "root.create_entity", ifc, ifc_class="IfcBuildingStorey", name="Ground Floor"
        )

        ifcopenshell.api.run("aggregate.assign_object", ifc, relating_object=project, products=[site])
        ifcopenshell.api.run("aggregate.assign_object", ifc, relating_object=site, products=[building])
        ifcopenshell.api.run("aggregate.assign_object", ifc, relating_object=building, products=[storey])

        for room in analysis.rooms:
            x, y, w, h = self._room_rect(room)

            # IfcSpace for the room
            space = ifcopenshell.api.run(
                "root.create_entity", ifc, ifc_class="IfcSpace", name=room.name
            )
            ifcopenshell.api.run("spatial.assign_container", ifc, relating_structure=storey, products=[space])

            # Four walls around the room
            wall_thickness = 0.2
            wall_defs = [
                (f"{room.name}_Wall_S", x, y, w, wall_thickness),
                (f"{room.name}_Wall_N", x, y + h - wall_thickness, w, wall_thickness),
                (f"{room.name}_Wall_W", x, y, wall_thickness, h),
                (f"{room.name}_Wall_E", x + w - wall_thickness, y, wall_thickness, h),
            ]
            for wname, wx, wy, ww, wh in wall_defs:
                wall = ifcopenshell.api.run("root.create_entity", ifc, ifc_class="IfcWall", name=wname)
                ifcopenshell.api.run("spatial.assign_container", ifc, relating_structure=storey, products=[wall])
                ifcopenshell.api.run(
                    "geometry.edit_object_placement", ifc, product=wall, matrix=self._translation_matrix(wx, wy, 0)
                )
                rep = ifcopenshell.api.run(
                    "geometry.add_wall_representation", ifc,
                    context=body_ctx,
                    length=ww,
                    height=WALL_HEIGHT,
                    thickness=wh if ww > wh else ww,
                )
                ifcopenshell.api.run("geometry.assign_representation", ifc, product=wall, representation=rep)

        buf = io.BytesIO()
        ifc.write(buf)
        return buf.getvalue()

    @staticmethod
    def _translation_matrix(x: float, y: float, z: float):
        """Return a 4x4 numpy translation matrix for ifcopenshell placement."""
        import numpy as np
        m = np.eye(4)
        m[0, 3] = x
        m[1, 3] = y
        m[2, 3] = z
        return m

    # ── OBJ (pure text) ─────────────────────────────────────────────────

    def generate_obj(self, analysis: SketchAnalysis) -> bytes:
        """Generate a Wavefront OBJ file.

        Extrudes each room rectangle into a 3D box (4 walls + floor + ceiling).
        Groups are named per room for easy selection in Blender/SketchUp.
        """
        lines: list[str] = ["# DraftBridge OBJ Export"]
        vi = 1  # vertex index (OBJ is 1-based)

        for room in analysis.rooms:
            x, y, w, h = self._room_rect(room)
            z0 = 0.0
            z1 = WALL_HEIGHT

            lines.append(f"g {room.name.replace(' ', '_')}")

            # 8 vertices of the box (bottom 4, top 4)
            #  v0(x,y,z0)  v1(x+w,y,z0)  v2(x+w,y+h,z0)  v3(x,y+h,z0)
            #  v4(x,y,z1)  v5(x+w,y,z1)  v6(x+w,y+h,z1)  v7(x,y+h,z1)
            verts = [
                (x, y, z0), (x + w, y, z0), (x + w, y + h, z0), (x, y + h, z0),
                (x, y, z1), (x + w, y, z1), (x + w, y + h, z1), (x, y + h, z1),
            ]
            for vx, vy, vz in verts:
                lines.append(f"v {vx:.4f} {vy:.4f} {vz:.4f}")

            # 6 quad faces (floor, ceiling, 4 walls)
            v = vi  # base index for this room's vertices
            faces = [
                (v, v+1, v+2, v+3),         # floor
                (v+4, v+7, v+6, v+5),       # ceiling (reversed normal)
                (v, v+4, v+5, v+1),         # south wall
                (v+2, v+6, v+7, v+3),       # north wall
                (v, v+3, v+7, v+4),         # west wall
                (v+1, v+5, v+6, v+2),       # east wall
            ]
            for f in faces:
                lines.append(f"f {f[0]} {f[1]} {f[2]} {f[3]}")

            vi += 8

        return "\n".join(lines).encode("utf-8")
