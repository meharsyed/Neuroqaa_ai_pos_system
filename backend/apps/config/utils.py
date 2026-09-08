def get_setting(key: str, default: str = "") -> str:
    """Return the stored value for `key`, or `default` if not found."""
    from .models import Setting

    try:
        return Setting.objects.get(key=key).value
    except Setting.DoesNotExist:
        return default


def get_all_settings() -> dict[str, str]:
    """Return all settings as a dict {key: value}."""
    from .models import Setting

    return {s.key: s.value for s in Setting.objects.all()}
