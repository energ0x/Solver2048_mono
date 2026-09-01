import numpy as np
import expectimax

board = np.array([
    [0, 0, 0, 4],
    [0, 0, 2, 8],
    [2, 2, 8, 4],
    [4, 16, 2, 8]
], dtype=np.int32)

print("Testing board:")
print(board)

best_move = expectimax.find_best_move(board, depth=10)
DIRECTION_NAMES = {0: "UP", 1: "DOWN", 2: "LEFT", 3: "RIGHT"}
print(f"C solver via find_best_move returns: {best_move} ({DIRECTION_NAMES.get(best_move, 'UNKNOWN')})")
