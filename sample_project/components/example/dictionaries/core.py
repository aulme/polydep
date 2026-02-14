def pick(data: dict, keys: set) -> dict:
    return {k: v for k, v in data.items() if k in keys}


def omit(data: dict, keys: set) -> dict:
    return {k: v for k, v in data.items() if k not in keys}
