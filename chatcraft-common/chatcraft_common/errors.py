"""Standard error codes and exceptions for ChatCraft services."""

from fastapi import HTTPException


class ErrorCode:
    # Auth errors
    AUTH_INVALID_CREDENTIALS = "AUTH_001"
    AUTH_TOKEN_EXPIRED = "AUTH_002"
    AUTH_TOKEN_INVALID = "AUTH_003"
    AUTH_INSUFFICIENT_PERMISSIONS = "AUTH_004"

    # Organization errors
    ORG_NOT_FOUND = "ORG_001"
    ORG_USER_NOT_FOUND = "ORG_002"
    ORG_USER_ALREADY_EXISTS = "ORG_003"

    # Document errors
    DOC_NOT_FOUND = "DOC_001"
    DOC_UPLOAD_FAILED = "DOC_002"
    DOC_PROCESSING_FAILED = "DOC_003"
    DOC_UNSUPPORTED_TYPE = "DOC_004"
    DOC_SIZE_EXCEEDED = "DOC_005"

    # Workspace errors
    WS_NOT_FOUND = "WS_001"
    WS_ACCESS_DENIED = "WS_002"
    WS_LIMIT_EXCEEDED = "WS_003"
    WS_DOCUMENT_NOT_IN_WORKSPACE = "WS_004"

    # Query errors
    QUERY_NO_DOCUMENTS = "QUERY_001"
    QUERY_LIMIT_EXCEEDED = "QUERY_002"
    QUERY_LLM_ERROR = "QUERY_003"

    # Billing errors
    BILL_SUBSCRIPTION_NOT_FOUND = "BILL_001"
    BILL_PAYMENT_FAILED = "BILL_002"
    BILL_LIMIT_EXCEEDED = "BILL_003"


class ChatCraftException(HTTPException):
    """Base exception with structured error response."""

    def __init__(self, status_code: int, code: str, message: str, details: dict | None = None):
        self.error_code = code
        self.error_message = message
        self.error_details = details or {}
        super().__init__(
            status_code=status_code,
            detail={
                "error": {
                    "code": code,
                    "message": message,
                    "details": details or {},
                }
            },
        )


class NotFoundException(ChatCraftException):
    def __init__(self, code: str, message: str):
        super().__init__(status_code=404, code=code, message=message)


class ForbiddenException(ChatCraftException):
    def __init__(self, message: str = "Access denied"):
        super().__init__(
            status_code=403,
            code=ErrorCode.AUTH_INSUFFICIENT_PERMISSIONS,
            message=message,
        )


class ConflictException(ChatCraftException):
    def __init__(self, code: str, message: str):
        super().__init__(status_code=409, code=code, message=message)


class LimitExceededException(ChatCraftException):
    def __init__(self, code: str, message: str, details: dict | None = None):
        super().__init__(status_code=429, code=code, message=message, details=details)
