def tile_score(val):
    if val <= 2: return 0
    k = 0
    temp = val
    while temp > 1:
        temp //= 2
        k += 1
    return (k - 1) * val

max_board = [1024] * 15 + [512]
total_score = sum(tile_score(v) for v in max_board)
print(f"Max theoretical score with 15x1024 and 1x512: {total_score}")

typical_board = [1024, 1024, 1024, 1024, 512, 256, 128, 64, 32, 16, 8, 4, 4, 2, 2, 2]
print(f"Score with 4x1024 and others: {sum(tile_score(v) for v in typical_board)}")
