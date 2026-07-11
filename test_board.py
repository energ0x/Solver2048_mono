import numpy as np
import time
from expectimax import find_best_move, _evaluate, _np_to_bb

board = np.array([
    [256, 4, 512, 1024],
    [32, 128, 64, 32],
    [2, 16, 32, 16],
    [0, 4, 8, 4]
])

print("Board:")
print(board)

bb = _np_to_bb(board)
print(f"Evaluate: {_evaluate(bb)}")

t0 = time.time()
best_move = find_best_move(board, depth=3)
elapsed = time.time() - t0

moves = ["UP", "DOWN", "LEFT", "RIGHT"]
print(f"Best move: {moves[best_move]} in {elapsed:.4f}s")
