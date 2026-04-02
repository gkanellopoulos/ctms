"""Change taxonomy and version logic (Section 5)."""

from __future__ import annotations

from typing import Any

from ctms._types import BREAKING_FIELDS, SEMANTIC_FIELDS, ManifestVersion
from ctms.errors import VersionRegressionError


def classify_change(
    old_surface: dict[str, Any],
    new_surface: dict[str, Any],
) -> str:
    """Compare two signing surfaces and classify the change (Section 5.1).

    Returns "none", "breaking", or "semantic".
    """
    changed_fields: set[str] = set()

    all_keys = set(old_surface.keys()) | set(new_surface.keys())
    for key in all_keys:
        old_val = old_surface.get(key)
        new_val = new_surface.get(key)
        if old_val != new_val:
            changed_fields.add(key)

    if not changed_fields:
        return "none"

    if changed_fields & BREAKING_FIELDS:
        return "breaking"

    if changed_fields & SEMANTIC_FIELDS:
        return "semantic"

    # Fields outside both sets should not be in the signing surface,
    # but if they somehow are, treat as breaking to be safe.
    return "breaking"


def next_version(
    current: ManifestVersion,
    change_type: str,
) -> ManifestVersion:
    """Compute next version based on change type (Section 5.2).

    "breaking" -> major+1, minor=0
    "semantic" -> same major, minor+1
    "none" -> raises ValueError
    """
    if change_type == "breaking":
        return ManifestVersion(major=current.major + 1, minor=0)
    elif change_type == "semantic":
        return ManifestVersion(major=current.major, minor=current.minor + 1)
    else:
        raise ValueError(f"No version increment needed for change type: {change_type}")


def validate_version_progression(
    previous: ManifestVersion,
    proposed: ManifestVersion,
) -> None:
    """Validate that proposed version is strictly greater than previous (Section 5.3).

    Raises VersionRegressionError if not.
    """
    if not proposed > previous:
        raise VersionRegressionError(
            f"Version {proposed} is not greater than {previous}",
        )
