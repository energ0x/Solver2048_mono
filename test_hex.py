import numpy as np
import expectimax
import ctypes

board = np.array([
    [0, 0, 0, 4],
    [0, 0, 2, 8],
    [2, 2, 8, 4],
    [4, 16, 2, 8]
], dtype=np.int32)

bb = expectimax._np_to_bb(board)
print(f"bb in python = {bb:x}")
