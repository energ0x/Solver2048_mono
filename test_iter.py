import numpy as np
import expectimax

board = np.array([
    [0, 0, 0, 4],
    [0, 0, 2, 8],
    [2, 2, 8, 4],
    [4, 16, 2, 8]
], dtype=np.int32)

for r in range(4):
    for c in range(4):
        print(f"r={r} c={c} val={board[r,c]}")
