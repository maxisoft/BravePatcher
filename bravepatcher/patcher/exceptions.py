from .models import PatchError


class PatchException(Exception):
    def __init__(self, patch_error: PatchError):
        self.error = patch_error


class MemorySearchException(Exception):
    pass


class MemorySearchNotFoundException(MemorySearchException):
    pass


class MemorySearchTooManyMatchException(MemorySearchException):
    pass