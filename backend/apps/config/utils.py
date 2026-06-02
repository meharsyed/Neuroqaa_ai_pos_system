def get_setting(key: str, default: str = "") -> str:
    """Return the stored value for `key`, or `default` if not found."""
    from .models import Setting
    try:
        return Setting.objects.get(key=key).value
    except Setting.DoesNotExist:
        return default