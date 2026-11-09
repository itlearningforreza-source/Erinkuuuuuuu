"""ERIN Core Exceptions."""

from typing import Any, Dict, Optional


class ERINException(Exception):
    """Base exception for ERIN application."""
    
    def __init__(
        self,
        message: str,
        code: str = "ERIN_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(ERINException):
    """Validation error."""
    
    def __init__(
        self,
        message: str = "Validation failed",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=422,
            details=details,
        )


class NotFoundError(ERINException):
    """Resource not found error."""
    
    def __init__(
        self,
        message: str = "Resource not found",
        resource_type: str = "resource",
        resource_id: Optional[str] = None,
    ):
        details = {"resource_type": resource_type}
        if resource_id:
            details["resource_id"] = resource_id
        super().__init__(
            message=message,
            code="NOT_FOUND",
            status_code=404,
            details=details,
        )


class AuthenticationError(ERINException):
    """Authentication error."""
    
    def __init__(
        self,
        message: str = "Authentication required",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code="UNAUTHORIZED",
            status_code=401,
            details=details,
        )


class AuthorizationError(ERINException):
    """Authorization error."""
    
    def __init__(
        self,
        message: str = "Insufficient permissions",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code="FORBIDDEN",
            status_code=403,
            details=details,
        )


class RateLimitError(ERINException):
    """Rate limit exceeded error."""
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        if retry_after:
            details["retry_after"] = retry_after
        super().__init__(
            message=message,
            code="RATE_LIMIT_EXCEEDED",
            status_code=429,
            details=details,
        )


class ConflictError(ERINException):
    """Resource conflict error."""
    
    def __init__(
        self,
        message: str = "Resource conflict",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code="CONFLICT",
            status_code=409,
            details=details,
        )


class BusinessLogicError(ERINException):
    """Business logic error."""
    
    def __init__(
        self,
        message: str = "Business logic violation",
        code: str = "BUSINESS_LOGIC_ERROR",
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code=code,
            status_code=status_code,
            details=details,
        )


class ExternalServiceError(ERINException):
    """External service error."""
    
    def __init__(
        self,
        message: str = "External service unavailable",
        service: str = "unknown",
        details: Optional[Dict[str, Any]] = None,
    ):
        details = details or {}
        details["service"] = service
        super().__init__(
            message=message,
            code="EXTERNAL_SERVICE_ERROR",
            status_code=503,
            details=details,
        )