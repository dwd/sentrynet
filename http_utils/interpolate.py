

def interpolate(value, keys: dict[str, str]):
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, dict):
        return {k: interpolate(v, keys) for k, v in value.items()}
    if isinstance(value, list):
        return [interpolate(v, keys) for v in value]
    if isinstance(value, str):
        if value in keys:
            return keys[value]
        return value.format_map(keys)
