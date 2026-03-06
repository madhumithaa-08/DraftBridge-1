class DraftBridgeError(Exception):
    """Base error for all DraftBridge errors."""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class UnsupportedFormatError(DraftBridgeError):
    def __init__(self, format: str, supported: set[str]):
        super().__init__(
            f"Unsupported format: {format}. Supported: {', '.join(sorted(supported))}",
            status_code=400,
        )


class DesignNotFoundError(DraftBridgeError):
    def __init__(self, design_id: str):
        super().__init__(f"Design not found: {design_id}", status_code=404)


class AWSServiceError(DraftBridgeError):
    def __init__(self, service: str, operation: str, detail: str):
        super().__init__(
            f"AWS {service} error during {operation}: {detail}",
            status_code=500,
        )


class VersionNotFoundError(DraftBridgeError):
    def __init__(self, design_id: str, version: int):
        super().__init__(
            f"Version {version} not found for design {design_id}",
            status_code=404,
        )
