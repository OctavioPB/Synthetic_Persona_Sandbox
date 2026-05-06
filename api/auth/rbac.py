"""Role-Based Access Control — S9-02.

Roles (from least to most privileged):
    viewer    → read-only access to simulations, segments, campaigns
    analyst   → viewer + export
    marketer  → analyst + run simulations + write campaigns
    admin     → full access including org management and API key management
"""

from __future__ import annotations

from enum import StrEnum, auto


class Permission(StrEnum):
    # Simulations
    SIMULATIONS_READ   = auto()
    SIMULATIONS_RUN    = auto()

    # Segments
    SEGMENTS_READ      = auto()
    SEGMENTS_WRITE     = auto()

    # Campaigns
    CAMPAIGNS_READ     = auto()
    CAMPAIGNS_WRITE    = auto()

    # Org management
    ORG_MEMBERS_READ   = auto()
    ORG_MEMBERS_MANAGE = auto()
    ORG_KEYS_READ      = auto()
    ORG_KEYS_MANAGE    = auto()
    ORG_AUDIT_READ     = auto()
    ORG_DATA_DELETE    = auto()


_VIEWER_PERMISSIONS: frozenset[Permission] = frozenset({
    Permission.SIMULATIONS_READ,
    Permission.SEGMENTS_READ,
    Permission.CAMPAIGNS_READ,
})

_ANALYST_PERMISSIONS: frozenset[Permission] = _VIEWER_PERMISSIONS | frozenset({
    Permission.ORG_AUDIT_READ,
})

_MARKETER_PERMISSIONS: frozenset[Permission] = _ANALYST_PERMISSIONS | frozenset({
    Permission.SIMULATIONS_RUN,
    Permission.SEGMENTS_WRITE,
    Permission.CAMPAIGNS_WRITE,
    Permission.ORG_KEYS_READ,
})

_ADMIN_PERMISSIONS: frozenset[Permission] = frozenset(Permission)   # all permissions

ROLE_PERMISSIONS: dict[str, frozenset[Permission]] = {
    "viewer":   _VIEWER_PERMISSIONS,
    "analyst":  _ANALYST_PERMISSIONS,
    "marketer": _MARKETER_PERMISSIONS,
    "admin":    _ADMIN_PERMISSIONS,
}


def has_permission(role: str, permission: Permission) -> bool:
    """Return True if `role` is granted `permission`."""
    return permission in ROLE_PERMISSIONS.get(role, frozenset())
