from itertools import count

_counter = count(1)

def next_id() -> int:
    return next(_counter)