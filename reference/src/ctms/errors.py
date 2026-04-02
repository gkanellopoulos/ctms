"""Typed failure exceptions for CTMS verification (Section 6.3)."""

from __future__ import annotations


class CTMSError(Exception):
    """Base class for all CTMS errors."""


class CanonicalizationError(CTMSError):
    """Raised when canonicalization fails."""


class DereferenceError(CanonicalizationError):
    """Raised when $ref resolution fails (external ref, cycle, invalid pointer)."""


class CTMSVerificationError(CTMSError):
    """Base class for all verification failures (Section 6.3)."""

    failure_type: str = "unknown"

    def __init__(
        self,
        message: str,
        subject_name: str | None = None,
        publisher_identity: str | None = None,
    ):
        super().__init__(message)
        self.subject_name = subject_name
        self.publisher_identity = publisher_identity


class ManifestDriftError(CTMSVerificationError):
    """Runtime metadata does not match signed canonical form."""

    failure_type = "manifest_drift"

    def __init__(
        self,
        message: str,
        expected_digest: str | None = None,
        actual_digest: str | None = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.expected_digest = expected_digest
        self.actual_digest = actual_digest


class SignatureFailureError(CTMSVerificationError):
    """Cryptographic signature is invalid."""
    failure_type = "signature_failure"


class CertificateFailureError(CTMSVerificationError):
    """Signing certificate cannot be validated."""

    failure_type = "certificate_failure"

    def __init__(self, message: str, certificate_details: str | None = None, **kwargs):
        super().__init__(message, **kwargs)
        self.certificate_details = certificate_details


class LogIntegrityFailureError(CTMSVerificationError):
    """Transparency log entry is missing or inconsistent."""
    failure_type = "log_integrity_failure"


class PublisherTrustFailureError(CTMSVerificationError):
    """Publisher identity is not trusted."""
    failure_type = "publisher_trust_failure"


class VersionRegressionError(CTMSVerificationError):
    """STM version is not greater than previously verified version."""
    failure_type = "version_regression"


class LogUnreachableError(CTMSVerificationError):
    """Transparency log cannot be contacted."""
    failure_type = "log_unreachable"
