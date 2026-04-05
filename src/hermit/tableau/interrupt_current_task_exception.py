"""Exception raised when the current tableau reasoning task is interrupted."""


class InterruptCurrentTaskException(RuntimeError):
    """Exception raised when the current tableau reasoning task is interrupted.

    This exception is used to signal that the reasoning process should be
    halted due to an external interrupt request.
    """

    pass
