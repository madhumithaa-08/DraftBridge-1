from datetime import datetime

from app.models.version import DesignVersion, VersionDiff
from app.services.database_service import DatabaseService
from app.utils.errors import VersionNotFoundError
from app.utils.logging import get_logger

logger = get_logger(__name__)


class VersionControlService:
    """Manages design version history."""

    def __init__(self, database_service: DatabaseService):
        self.db = database_service

    def create_version(self, design_id: str, change_description: str) -> DesignVersion:
        """Snapshot current design state as a new version."""
        # Get current design to snapshot analysis state
        design = self.db.get_design(design_id)
        analysis_snapshot = design.get("analysis_data")

        # Determine next version number from existing versions
        existing_versions = self.db.get_versions(design_id)
        next_version = len(existing_versions) + 1

        # Create the version record in DynamoDB
        item = self.db.create_version(
            design_id=design_id,
            version_number=next_version,
            change_description=change_description,
            analysis_snapshot=analysis_snapshot,
        )

        return DesignVersion(
            design_id=item["design_id"],
            version=item["version"],
            change_description=item["change_description"],
            analysis_snapshot=item.get("analysis_snapshot"),
            created_at=datetime.fromisoformat(item["created_at"]),
        )

    def get_history(self, design_id: str) -> list[DesignVersion]:
        """Get version history for a design, ordered by version number ascending."""
        items = self.db.get_versions(design_id)
        return [
            DesignVersion(
                design_id=item["design_id"],
                version=item["version"],
                change_description=item["change_description"],
                analysis_snapshot=item.get("analysis_snapshot"),
                renders=item.get("renders", []),
                compliance_reports=item.get("compliance_reports", []),
                created_at=datetime.fromisoformat(item["created_at"]),
            )
            for item in items
        ]

    def get_version(self, design_id: str, version: int) -> DesignVersion:
        """Get full design state at a specific version."""
        item = self.db.get_version(design_id, version)
        if not item:
            raise VersionNotFoundError(design_id, version)
        return DesignVersion(
            design_id=item["design_id"],
            version=item["version"],
            change_description=item["change_description"],
            analysis_snapshot=item.get("analysis_snapshot"),
            renders=item.get("renders", []),
            compliance_reports=item.get("compliance_reports", []),
            created_at=datetime.fromisoformat(item["created_at"]),
        )

    def compare_versions(self, design_id: str, v1: int, v2: int) -> VersionDiff:
        """Compare two versions and return differences."""
        version_a = self.get_version(design_id, v1)
        version_b = self.get_version(design_id, v2)

        changes: list[dict] = []

        # If same version, return empty changes
        if v1 == v2:
            return VersionDiff(
                design_id=design_id,
                version_a=v1,
                version_b=v2,
                changes=changes,
            )

        snapshot_a = version_a.analysis_snapshot or {}
        snapshot_b = version_b.analysis_snapshot or {}

        # Find all keys across both snapshots
        all_keys = set(snapshot_a.keys()) | set(snapshot_b.keys())
        for key in sorted(all_keys):
            old_value = snapshot_a.get(key)
            new_value = snapshot_b.get(key)
            if old_value != new_value:
                changes.append({
                    "field": key,
                    "old_value": old_value,
                    "new_value": new_value,
                })

        return VersionDiff(
            design_id=design_id,
            version_a=v1,
            version_b=v2,
            changes=changes,
        )
