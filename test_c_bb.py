import numpy as np
import expectimax
import ctypes

board = np.array([
    [0, 0, 0, 4],
    [0, 0, 2, 8],
    [2, 2, 8, 4],
    [4, 16, 2, 8]
], dtype=np.int32)

c_bb = 0
for r in range(4):
    for c in range(4):
        val = int(board[r, c])
        if val > 0:
            log_val = val.bit_length() - 1
            c_bb |= (log_val << ((r * 4 + c) * 4))

print(f"c_bb in python = {c_bb:x}")
best = expectimax._c_solver.solver_find_best_move(c_bb, 2)
print("direct C call best =", best)
