"""Custom exception classes for Graph Intelligence platform."""

class GraphIntelligenceError(Exception):
    """Base error for all graph intelligence domain errors."""
    def __init__(self, message: str, error_code: str = "INTERNAL_ERROR"):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


class DatabaseUnavailable(GraphIntelligenceError):
    """Raised when FalkorDB connection fails or query times out."""
    def __init__(self, message: str = "Database service is unavailable"):
        super().__init__(message, error_code="DATABASE_UNAVAILABLE")


class ValidationError(GraphIntelligenceError):
    """Raised when input validation fails."""
    def __init__(self, message: str):
        super().__init__(message, error_code="INVALID_INPUT")


class EntityNotFoundError(GraphIntelligenceError):
    """Raised when a requested entity cannot be resolved."""
    def __init__(self, message: str):
        super().__init__(message, error_code="UNKNOWN_ENTITY")


class UnauthorizedScopeError(GraphIntelligenceError):
    """Raised when access to a resource is unauthorized."""
    def __init__(self, message: str = "Access unauthorized"):
        super().__init__(message, error_code="UNAUTHORIZED_SCOPE")


class ConflictError(GraphIntelligenceError):
    """Raised when an update conflicts with the current resource version."""
    def __init__(self, message: str = "Resource version conflict"):
        super().__init__(message, error_code="CONFLICT")


class DepthLimitExceeded(GraphIntelligenceError):
    """Raised when requested traversal depth exceeds hard bounds."""
    def __init__(self, message: str = "Depth limit exceeded"):
        super().__init__(message, error_code="DEPTH_LIMIT")
