from __future__ import annotations

import hashlib
import os
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from flask import current_app

from app.services.cg_bank_statement_service import cg_md5_file


@dataclass(frozen=True)
class DraftInfo:
    token: str
    tmp_path: str
    original_filename: str
    file_hash: str
    created_at: float


def _draft_root() -> str:
    # Keep drafts under instance/tmp/cg_bank_statement_drafts
    root = os.path.join(current_app.root_path, "instance", "tmp", "cg_bank_statement_drafts")
    os.makedirs(root, exist_ok=True)
    return root


def _token_for(file_hash: str, filename: str) -> str:
    seed = f"{file_hash}|{filename}|{time.time()}|{os.getpid()}"
    return hashlib.md5(seed.encode("utf-8")).hexdigest()


def create_draft_from_upload(file_storage) -> DraftInfo:
    """Persist uploaded file to a temp draft and return token.

    This is intentionally *not* persisted in DB.
    """

    filename = file_storage.filename or ""
    tmp_dir = _draft_root()

    # Save first for hashing
    tmp_name = f"draft_{datetime.now().timestamp()}_{os.getpid()}.pdf"
    tmp_path = os.path.join(tmp_dir, tmp_name)
    file_storage.save(tmp_path)

    file_hash = cg_md5_file(tmp_path)
    token = _token_for(file_hash, filename)

    # Rename to stable token-based name
    final_path = os.path.join(tmp_dir, f"{token}.pdf")
    os.replace(tmp_path, final_path)

    return DraftInfo(
        token=token,
        tmp_path=final_path,
        original_filename=filename,
        file_hash=file_hash,
        created_at=time.time(),
    )


def resolve_draft_path(token: str) -> Optional[str]:
    path = os.path.join(_draft_root(), f"{token}.pdf")
    return path if os.path.exists(path) else None


def delete_draft(token: str) -> None:
    path = resolve_draft_path(token)
    if not path:
        return
    try:
        os.remove(path)
    except Exception:
        current_app.logger.warning("删除draft失败: %s", path)


def compute_draft_hash(token: str) -> Optional[str]:
    path = resolve_draft_path(token)
    if not path:
        return None
    try:
        return cg_md5_file(path)
    except Exception:
        return None


def cleanup_expired_drafts(ttl_seconds: int = 24 * 3600) -> int:
    """Best-effort cleanup for old drafts; returns removed file count."""

    root = _draft_root()
    now = time.time()
    removed = 0
    for name in os.listdir(root):
        if not name.endswith(".pdf"):
            continue
        path = os.path.join(root, name)
        try:
            st = os.stat(path)
            if now - st.st_mtime > ttl_seconds:
                os.remove(path)
                removed += 1
        except Exception:
            continue
    return removed

