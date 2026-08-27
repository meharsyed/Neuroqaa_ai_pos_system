"""
Lightweight activity logging. Call log_activity() at key service points.
The request parameter is optional — pass it from views to capture IP address.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def log_activity(
    action: str,
    *,
    user=None,
    details: dict | None = None,
    request=None,
) -> None:
    """
    Write a single ActivityLog record. Never raises — failures are logged to
    Django's error log so they don't interrupt the main transaction.
    """
    from .models import ActivityLog

    ip = ""
    if request:
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        ip = forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR", "")

    try:
        ActivityLog.objects.create(
            user=user,
            action=action,
            details=details or {},
            ip_address=ip,
        )
    except Exception:
        logger.exception("Failed to write activity log (action=%s)", action)