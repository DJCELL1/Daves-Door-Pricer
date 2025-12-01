def greedy_stock(total_m):
    L54 = 5.4
    L21 = 2.1

    if total_m <= 0:
        return 0, 0, 0.0

    n54 = int(total_m // L54)
    rem = total_m - n54 * L54
    n21 = int(rem // L21)
    waste = rem - n21 * L21

    return n54, n21, waste
