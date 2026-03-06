import json
import time

from botocore.exceptions import ClientError

from app.utils.errors import AWSServiceError
from app.utils.logging import get_logger

logger = get_logger(__name__)

MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 1.0


class BaseAgent:
    """Base class for all DraftBridge agents.

    Provides shared Bedrock invocation logic with retry and error handling.
    All methods are synchronous — FastAPI handles threading for sync endpoints.
    """

    def __init__(self, bedrock_client, storage_service, database_service):
        self.bedrock = bedrock_client
        self.storage = storage_service
        self.db = database_service

    def invoke_bedrock(self, model_id: str, body: dict) -> dict:
        """Invoke a Bedrock model synchronously with retry logic.

        Args:
            model_id: The Bedrock model identifier.
            body: The request body dict (will be JSON-serialized).

        Returns:
            Parsed JSON response from the model.

        Raises:
            AWSServiceError: If all retries are exhausted or a non-retryable error occurs.
        """
        last_error = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = self.bedrock.invoke_model(
                    modelId=model_id,
                    body=json.dumps(body),
                    contentType="application/json",
                    accept="application/json",
                )
                response_body = json.loads(response["body"].read())
                return response_body
            except ClientError as e:
                error_code = e.response["Error"]["Code"]
                last_error = e
                if error_code in ("ThrottlingException", "ServiceUnavailableException"):
                    wait = RETRY_BACKOFF_BASE * (2 ** (attempt - 1))
                    logger.warning(
                        f"Bedrock invoke_model attempt {attempt}/{MAX_RETRIES} "
                        f"failed with {error_code}, retrying in {wait}s"
                    )
                    time.sleep(wait)
                else:
                    logger.error(f"Bedrock invoke_model failed: {error_code} - {e}")
                    raise AWSServiceError("Bedrock", "invoke_model", str(e))
            except Exception as e:
                logger.error(f"Bedrock invoke_model unexpected error: {e}")
                raise AWSServiceError("Bedrock", "invoke_model", str(e))

        logger.error(f"Bedrock invoke_model exhausted {MAX_RETRIES} retries")
        raise AWSServiceError("Bedrock", "invoke_model", str(last_error))

    def invoke_bedrock_async(self, model_id: str, body: dict, s3_output: str) -> str:
        """Start an async Bedrock invocation (for Nova Reel).

        Args:
            model_id: The Bedrock model identifier.
            body: The model input dict.
            s3_output: S3 URI for output data.

        Returns:
            The invocation ARN for polling status.

        Raises:
            AWSServiceError: If the async invocation fails.
        """
        try:
            response = self.bedrock.start_async_invoke(
                modelId=model_id,
                modelInput=body,
                outputDataConfig={"s3OutputDataConfig": {"s3Uri": s3_output}},
            )
            invocation_arn = response["invocationArn"]
            logger.info(f"Started async Bedrock invocation: {invocation_arn}")
            return invocation_arn
        except ClientError as e:
            logger.error(f"Bedrock start_async_invoke failed: {e}")
            raise AWSServiceError("Bedrock", "start_async_invoke", str(e))
        except Exception as e:
            logger.error(f"Bedrock start_async_invoke unexpected error: {e}")
            raise AWSServiceError("Bedrock", "start_async_invoke", str(e))
