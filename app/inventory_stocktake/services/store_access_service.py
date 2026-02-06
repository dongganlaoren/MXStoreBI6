from __future__ import annotations

from typing import List, Optional, Tuple

from flask_login import current_user

from app.models.enums import RoleType
from app.models.store import Store


def get_accessible_stores() -> Tuple[List[Store], Optional[str], bool]:
    """Return (stores, default_store_id, locked).

    Rules:
      - ADMIN / HEAD_MANAGER: can access all stores, not locked.
      - Others: only their own store_id, locked.

    default_store_id:
      - If locked: user's store_id.
      - Else: user's store_id if present else first store.
    """

    role = getattr(current_user, "role", None)
    role_val = role.value if role else None

    is_admin_like = role_val in (RoleType.ADMIN.value, RoleType.HEAD_MANAGER.value)

    if is_admin_like:
        stores = Store.query.order_by(Store.store_id.asc()).all()
        default_store_id = getattr(current_user, "store_id", None) or (stores[0].store_id if stores else None)
        return stores, default_store_id, False

    # locked
    sid = getattr(current_user, "store_id", None)
    stores = []
    if sid:
        s = Store.query.filter_by(store_id=sid).first()
        if s:
            stores = [s]
    return stores, sid, True
