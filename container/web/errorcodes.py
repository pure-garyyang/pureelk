
from enum import Enum


class ErrorCodes(Enum):
    RequireFieldMissing = "require-field-missing"
    InvalidInput = "invalid-input"
    ArrayNotFound = "array-not-found"
    ArrayError = "array-error"
    ArrayIdMismatch = "array-id-mismatch"
    ArrayAlreadyExists = "array-already-exists"
    MonitorNotFound = "monitor-not-found"
    MonitorAlreadyExists = "monitor-already-exists"


