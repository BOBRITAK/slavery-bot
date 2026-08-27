def plural_rabs(count: int) -> str:
    last2 = count % 100
    if 11 <= last2 <= 19:
        return "рабов"
    last1 = count % 10
    if last1 == 1:
        return "раб"
    if 2 <= last1 <= 4:
        return "раба"
    return "рабов"