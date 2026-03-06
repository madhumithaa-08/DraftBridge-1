import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from boto3.dynamodb.conditions import Key

from app.utils.errors import AWSServiceError, DesignNotFoundError
from app.utils.logging import get_logger


def _floats_to_decimals(obj):
    """Recursively convert float values to Decimal for DynamoDB compatibility."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: _floats_to_decimals(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_floats_to_decimals(i) for i in obj]
    return obj

logger = get_logger(__name__)


class DatabaseService:
    """Handles DynamoDB operations for design metadata."""

    def __init__(self, dynamodb_resource, table_name: str):
        self.dynamodb = dynamodb_resource
        self.table_name = table_name
        self.table = dynamodb_resource.Table(table_name)

    def create_design(self, sketch_s3_key: str, user_id: str = "anonymous") -> str:
        """Create a new design record. Returns design_id."""
        design_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        try:
            self.table.put_item(Item={
                "PK": f"DESIGN#{design_id}",
                "SK": "METADATA",
                "design_id": design_id,
                "sketch_s3_key": sketch_s3_key,
                "status": "analyzing",
                "user_id": user_id,
                "created_at": now,
                "updated_at": now,
            })
        except Exception as e:
            logger.error(f"DynamoDB create_design failed: {e}")
            raise AWSServiceError("DynamoDB", "put_item", str(e))
        return design_id

    def get_design(self, design_id: str) -> dict[str, Any]:
        """Get design by ID."""
        try:
            response = self.table.get_item(Key={
                "PK": f"DESIGN#{design_id}",
                "SK": "METADATA",
            })
        except Exception as e:
            logger.error(f"DynamoDB get_design failed: {e}")
            raise AWSServiceError("DynamoDB", "get_item", str(e))
        item = response.get("Item")
        if not item:
            raise DesignNotFoundError(design_id)
        return item

    def update_design(self, design_id: str, updates: dict[str, Any]) -> None:
        """Update design fields."""
        now = datetime.now(timezone.utc).isoformat()
        updates["updated_at"] = now
        update_expr_parts = []
        expr_values = {}
        expr_names = {}
        for i, (k, v) in enumerate(updates.items()):
            attr_name = f"#attr{i}"
            attr_val = f":val{i}"
            update_expr_parts.append(f"{attr_name} = {attr_val}")
            expr_names[attr_name] = k
            expr_values[attr_val] = _floats_to_decimals(v)
        try:
            self.table.update_item(
                Key={"PK": f"DESIGN#{design_id}", "SK": "METADATA"},
                UpdateExpression="SET " + ", ".join(update_expr_parts),
                ExpressionAttributeNames=expr_names,
                ExpressionAttributeValues=expr_values,
            )
        except Exception as e:
            logger.error(f"DynamoDB update_design failed: {e}")
            raise AWSServiceError("DynamoDB", "update_item", str(e))

    def save_render_metadata(self, design_id: str, render_id: str, s3_key: str, prompt_used: str, style: str) -> None:
        """Save render metadata."""
        now = datetime.now(timezone.utc).isoformat()
        try:
            self.table.put_item(Item={
                "PK": f"DESIGN#{design_id}",
                "SK": f"RENDER#{render_id}",
                "render_id": render_id,
                "design_id": design_id,
                "s3_key": s3_key,
                "prompt_used": prompt_used,
                "style": style,
                "created_at": now,
            })
        except Exception as e:
            logger.error(f"DynamoDB save_render_metadata failed: {e}")
            raise AWSServiceError("DynamoDB", "put_item", str(e))

    def save_video_metadata(self, design_id: str, video_id: str, status: str, invocation_arn: str | None = None, s3_key: str | None = None) -> None:
        """Save video metadata."""
        now = datetime.now(timezone.utc).isoformat()
        item = {
            "PK": f"DESIGN#{design_id}",
            "SK": f"VIDEO#{video_id}",
            "video_id": video_id,
            "design_id": design_id,
            "status": status,
            "created_at": now,
        }
        if invocation_arn:
            item["invocation_arn"] = invocation_arn
        if s3_key:
            item["s3_key"] = s3_key
        try:
            self.table.put_item(Item=item)
        except Exception as e:
            logger.error(f"DynamoDB save_video_metadata failed: {e}")
            raise AWSServiceError("DynamoDB", "put_item", str(e))

    def save_compliance_report(self, design_id: str, report_id: str, report_type: str, report_data: dict, version: int) -> None:
        """Save compliance report linked to design."""
        now = datetime.now(timezone.utc).isoformat()
        try:
            self.table.put_item(Item=_floats_to_decimals({
                "PK": f"DESIGN#{design_id}",
                "SK": f"COMPLIANCE#{report_id}",
                "report_id": report_id,
                "design_id": design_id,
                "report_type": report_type,
                "report_data": report_data,
                "version": version,
                "created_at": now,
            }))
        except Exception as e:
            logger.error(f"DynamoDB save_compliance_report failed: {e}")
            raise AWSServiceError("DynamoDB", "put_item", str(e))

    def save_export_metadata(self, design_id: str, export_id: str, format: str, s3_key: str, status: str) -> None:
        """Save export metadata."""
        now = datetime.now(timezone.utc).isoformat()
        try:
            self.table.put_item(Item={
                "PK": f"DESIGN#{design_id}",
                "SK": f"EXPORT#{export_id}",
                "export_id": export_id,
                "design_id": design_id,
                "format": format,
                "s3_key": s3_key,
                "status": status,
                "created_at": now,
            })
        except Exception as e:
            logger.error(f"DynamoDB save_export_metadata failed: {e}")
            raise AWSServiceError("DynamoDB", "put_item", str(e))

    def get_versions(self, design_id: str) -> list[dict[str, Any]]:
        """Get all versions for a design, ordered by version number ascending."""
        try:
            response = self.table.query(
                KeyConditionExpression=Key("PK").eq(f"DESIGN#{design_id}") & Key("SK").begins_with("VERSION#"),
            )
        except Exception as e:
            logger.error(f"DynamoDB get_versions failed: {e}")
            raise AWSServiceError("DynamoDB", "query", str(e))
        items = response.get("Items", [])
        return sorted(items, key=lambda x: x.get("version", 0))

    def get_version(self, design_id: str, version: int) -> dict[str, Any] | None:
        """Get specific version."""
        try:
            response = self.table.get_item(Key={
                "PK": f"DESIGN#{design_id}",
                "SK": f"VERSION#{version}",
            })
        except Exception as e:
            logger.error(f"DynamoDB get_version failed: {e}")
            raise AWSServiceError("DynamoDB", "get_item", str(e))
        return response.get("Item")

    def create_version(self, design_id: str, version_number: int, change_description: str, analysis_snapshot: dict | None = None) -> dict[str, Any]:
        """Create a new version snapshot."""
        now = datetime.now(timezone.utc).isoformat()
        item = {
            "PK": f"DESIGN#{design_id}",
            "SK": f"VERSION#{version_number}",
            "design_id": design_id,
            "version": version_number,
            "change_description": change_description,
            "created_at": now,
        }
        if analysis_snapshot:
            item["analysis_snapshot"] = _floats_to_decimals(analysis_snapshot)
        try:
            self.table.put_item(Item=item)
        except Exception as e:
            logger.error(f"DynamoDB create_version failed: {e}")
            raise AWSServiceError("DynamoDB", "put_item", str(e))
        return item

    def get_item_by_sk_prefix(self, design_id: str, sk_prefix: str) -> list[dict[str, Any]]:
        """Generic query for items with a given SK prefix under a design."""
        try:
            response = self.table.query(
                KeyConditionExpression=Key("PK").eq(f"DESIGN#{design_id}") & Key("SK").begins_with(sk_prefix),
            )
        except Exception as e:
            logger.error(f"DynamoDB query failed: {e}")
            raise AWSServiceError("DynamoDB", "query", str(e))
        return response.get("Items", [])
