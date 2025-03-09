import numba

def price_adapter(price: str) -> int:
    return int(1000 * float(price))

def size_adapter(size: str) -> int:
    return int(100 * float(size))