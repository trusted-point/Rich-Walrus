def covert_seconds_to_dhm(seconds: int, granularity=4) -> str:
    intervals = (
        ('days', 86400),
        ('hours', 3600),
        ('m', 60),
        ('s', 1),
    )
    result = []

    for name, count in intervals:
        value = seconds // count
        if value:
            seconds -= value * count
            if value == 1:
                name = name.rstrip('s')
            result.append("{} {}".format(value, name))
    return ', '.join(result[:granularity])