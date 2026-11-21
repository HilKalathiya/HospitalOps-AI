"""
HospitalOps AI — Search Filter Builder & RBAC Scope Enforcement.

Constructs secure server-side metadata filter expressions for ChromaDB.
Enforces role-based access classification:
- Role.ADMIN: PUBLIC, INTERNAL, RESTRICTED, CONFIDENTIAL
- Role.OPERATIONS_MANAGER: PUBLIC, INTERNAL, RESTRICTED
- Role.DOCTOR: PUBLIC, INTERNAL
Combines user-specified filters with server-derived authorization boundaries,
ensuring users can never elevate access by manipulating client requests.
"""

from __future__ import annotations

import logging
from typing import Any

from app.knowledge.retrieval.contracts import SearchFilters
from app.models.knowledge import AccessLevel
from app.models.user import Role, UserDocument

logger = logging.getLogger(__name__)

# Permitted access classifications by user role
ROLE_ACCESS_PERMISSIONS: dict[Role, list[AccessLevel]] = {
    Role.ADMIN: [
        AccessLevel.PUBLIC,
        AccessLevel.INTERNAL,
        AccessLevel.RESTRICTED,
        AccessLevel.CONFIDENTIAL,
    ],
    Role.OPERATIONS_MANAGER: [
        AccessLevel.PUBLIC,
        AccessLevel.INTERNAL,
        AccessLevel.RESTRICTED,
    ],
    Role.DOCTOR: [
        AccessLevel.PUBLIC,
        AccessLevel.INTERNAL,
    ],
}


class SearchFilterBuilder:
    """Builds authorized ChromaDB metadata filter dictionaries."""

    @classmethod
    def build_chroma_filters(
        cls,
        user: UserDocument | None = None,
        filters: SearchFilters | None = None,
    ) -> dict[str, Any] | None:
        """Convenience method returning the where_dict for ChromaDB queries."""
        where_dict, _, _ = cls.build_where_clause(filters=filters, user=user)
        return where_dict

    @classmethod
    def build_where_clause(
        cls,
        filters: SearchFilters | None = None,
        user: UserDocument | None = None,
    ) -> tuple[dict[str, Any] | None, dict[str, Any], bool]:
        """
        Construct ChromaDB filter dict and human-readable applied filters dict.

        Returns:
            (where_dict, applied_filters_dict, is_authorized)
            If is_authorized is False, the query should immediately return 0 results.
        """
        filters = filters or SearchFilters()
        conditions: list[dict[str, Any]] = []
        applied_filters: dict[str, Any] = {}

        # 1. Resolve authorized access levels based on user role
        user_role = user.role if user else Role.DOCTOR
        allowed_levels = ROLE_ACCESS_PERMISSIONS.get(
            user_role, [AccessLevel.PUBLIC, AccessLevel.INTERNAL]
        )

        # 2. Check if user explicitly requested access levels
        if filters.access_levels:
            # Intersect requested levels with allowed levels
            effective_levels = [lvl for lvl in filters.access_levels if lvl in allowed_levels]
            if not effective_levels:
                # User requested levels they are forbidden from seeing
                logger.warning(
                    "User %s (Role %s) requested forbidden access levels: %s",
                    user.user_id if user else "anonymous",
                    user_role,
                    filters.access_levels,
                )
                return None, {}, False
        else:
            effective_levels = allowed_levels

        # Format access_level filter for Chroma
        level_values = [lvl.value if hasattr(lvl, "value") else str(lvl) for lvl in effective_levels]
        if len(level_values) == 1:
            conditions.append({"access_level": {"$eq": level_values[0]}})
        else:
            conditions.append({"access_level": {"$in": level_values}})
        applied_filters["access_levels"] = level_values

        # 3. Document Category filter
        if filters.category:
            cat_val = filters.category.value if hasattr(filters.category, "value") else str(filters.category)
            conditions.append({"category": {"$eq": cat_val}})
            applied_filters["category"] = cat_val

        # 4. Specific Document ID filter
        if filters.document_id:
            conditions.append({"document_id": {"$eq": filters.document_id}})
            applied_filters["document_id"] = filters.document_id

        # 5. Specific Version filter
        if filters.version is not None:
            conditions.append({"version": {"$eq": int(filters.version)}})
            applied_filters["version"] = int(filters.version)

        # 6. Department Scoping
        # If user is scoped to a specific department (and not an admin)
        if user and user.department_id and user.role not in [Role.ADMIN, Role.OPERATIONS_MANAGER]:
            # User can view global documents (empty department) or their own department
            conditions.append(
                {"$or": [
                    {"department_id": {"$eq": ""}},
                    {"department_id": {"$eq": user.department_id}},
                ]}
            )
            applied_filters["department_scope"] = user.department_id
        elif filters.department_id:
            # User explicitly filtered by department
            conditions.append({"department_id": {"$eq": filters.department_id}})
            applied_filters["department_id"] = filters.department_id

        # 7. Assemble Chroma where clause
        if not conditions:
            return None, applied_filters, True

        if len(conditions) == 1:
            return conditions[0], applied_filters, True

        return {"$and": conditions}, applied_filters, True
