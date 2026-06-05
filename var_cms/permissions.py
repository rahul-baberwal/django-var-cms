"""
var_cms/permissions.py
======================
Role-based permission system for django-var-cms.

RolePermission  — defines what a named role can do
GroupPermission — same but matches Django auth groups
UserPermission  — per-user overrides (highest priority)

Resolution order: UserPermission > GroupPermission > RolePermission > deny
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union


ACTIONS = ("add", "list", "view", "edit", "delete")


@dataclass
class RolePermission:
    """
    Map a role name (string) to a set of allowed actions.

    The role name is matched against:
      1. "superuser"          — request.user.is_superuser
      2. Django group names   — request.user.groups
      3. Custom role logic    — override VarCMSModelAdmin._get_user_role()
    """
    role: str
    add: bool    = False
    list: bool   = True
    view: bool   = True
    edit: bool   = False
    delete: bool = False

    def allows(self, action: str) -> bool:
        return bool(getattr(self, action, False))


@dataclass
class GroupPermission(RolePermission):
    """Alias — identical to RolePermission, role matches a Django group name."""
    pass


@dataclass
class UserPermission:
    """
    Per-user permission override (matched by username or user pk).
    Takes priority over all role/group permissions.
    """
    username: str
    add: bool    = False
    list: bool   = True
    view: bool   = True
    edit: bool   = False
    delete: bool = False

    def allows(self, action: str) -> bool:
        return bool(getattr(self, action, False))


def resolve_permission(
    permissions: List[Union[RolePermission, UserPermission]],
    role: str,
    action: str,
    username: str = "",
) -> bool:
    """
    Walk the permission list and return True if allowed.
    UserPermission (matched by username) takes priority.
    """
    if action not in ACTIONS:
        return False

    # 1. User-level overrides first
    for perm in permissions:
        if isinstance(perm, UserPermission) and perm.username == username:
            return perm.allows(action)

    # 2. Role / group match
    for perm in permissions:
        if isinstance(perm, RolePermission) and perm.role == role:
            return perm.allows(action)

    # 3. Default deny
    return False


def resolve_editable_fields(
    role_editable_fields: Dict[str, Union[List[str], str]],
    role: str,
) -> Union[List[str], str]:
    """
    Return the editable fields for a given role.
    Falls back to "__all__" for superuser if not explicitly set.
    """
    if role in role_editable_fields:
        return role_editable_fields[role]
    if role == "superuser":
        return "__all__"
    # Check wildcard
    if "*" in role_editable_fields:
        return role_editable_fields["*"]
    return []   # deny all edits for unknown roles


def permission_summary(permissions: List[RolePermission]) -> List[Dict]:
    """Return a list of dicts for rendering a permission table in templates."""
    return [
        {
            "role": p.role,
            "add": p.add,
            "list": p.list,
            "view": p.view,
            "edit": p.edit,
            "delete": p.delete,
        }
        for p in permissions
        if isinstance(p, (RolePermission, UserPermission))
    ]
