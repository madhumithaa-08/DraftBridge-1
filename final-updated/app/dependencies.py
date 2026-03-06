import boto3
from functools import lru_cache

from fastapi import Depends

from app.config import settings
from app.agents.sketch_agent import SketchAgent
from app.agents.visualization_agent import VisualizationAgent
from app.agents.compliance_agent import ComplianceAgent
from app.agents.export_agent import ExportAgent
from app.services.storage_service import StorageService
from app.services.database_service import DatabaseService
from app.services.version_control_service import VersionControlService


@lru_cache
def get_s3_client():
    return boto3.client("s3", region_name=settings.aws_region)


@lru_cache
def get_dynamodb_resource():
    return boto3.resource("dynamodb", region_name=settings.aws_region)


@lru_cache
def get_bedrock_client():
    return boto3.client("bedrock-runtime", region_name=settings.aws_region)


def get_storage_service(s3_client=Depends(get_s3_client)) -> StorageService:
    return StorageService(s3_client, settings.s3_bucket_name)


def get_database_service(
    dynamodb=Depends(get_dynamodb_resource),
) -> DatabaseService:
    return DatabaseService(dynamodb, settings.dynamodb_table_name)


def get_version_control_service(
    db_service: DatabaseService = Depends(get_database_service),
) -> VersionControlService:
    return VersionControlService(db_service)


def get_sketch_agent(
    bedrock=Depends(get_bedrock_client),
    storage=Depends(get_storage_service),
    db=Depends(get_database_service),
) -> SketchAgent:
    return SketchAgent(bedrock, storage, db)


def get_visualization_agent(
    bedrock=Depends(get_bedrock_client),
    storage=Depends(get_storage_service),
    db=Depends(get_database_service),
) -> VisualizationAgent:
    return VisualizationAgent(bedrock, storage, db)


def get_compliance_agent(
    bedrock=Depends(get_bedrock_client),
    storage=Depends(get_storage_service),
    db=Depends(get_database_service),
) -> ComplianceAgent:
    return ComplianceAgent(bedrock, storage, db)


def get_export_agent(
    bedrock=Depends(get_bedrock_client),
    storage=Depends(get_storage_service),
    db=Depends(get_database_service),
) -> ExportAgent:
    return ExportAgent(bedrock, storage, db)
