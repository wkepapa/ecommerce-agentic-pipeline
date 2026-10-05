"""Exception hierarchy. `recoverable` decides whether the retry mechanism may retry."""


class WorkflowError(Exception):
    recoverable = False


class TransientToolError(WorkflowError):
    """Temporary tool failure (network glitch, rate limit). Retry is allowed."""
    recoverable = True


class ToolTimeoutError(TransientToolError):
    """Tool did not answer in time. Treated as recoverable."""


class PermanentToolError(WorkflowError):
    """Tool/data problem that retrying cannot fix (unknown tool, missing source)."""


class InvalidInputError(WorkflowError):
    """User query or task definition is unusable."""


class MissingDataError(WorkflowError):
    """Required product information is missing."""


class UnauthorizedToolAccess(WorkflowError):
    """An agent tried to call a tool outside its role."""


class UnauthorizedStateWrite(WorkflowError):
    """An agent tried to modify shared state it does not own (or a locked key)."""


class PromptInjectionDetected(WorkflowError):
    """Raised only in strict mode; default behaviour is to strip the injected text."""


class ValidationFailure(WorkflowError):
    pass


class WorkflowAbort(WorkflowError):
    """Supervisor/orchestrator decided the workflow cannot continue."""

    def __init__(self, message, status="aborted"):
        super().__init__(message)
        self.status = status
