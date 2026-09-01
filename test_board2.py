import numpy as np
import expectimax
import ctypes

board = np.array([
    [0, 0, 0, 4],
    [0, 0, 2, 8],
    [2, 2, 8, 4],
    [4, 16, 2, 8]
], dtype=np.int32)

print("Testing board:")
print(board)

print("Is C solver loaded:", expectimax._c_solver is not None)

DIRECTION_NAMES = {0: "UP", 1: "DOWN", 2: "LEFT", 3: "RIGHT"}

# Test C solver specifically
if expectimax._c_solver:
    bb = expectimax._np_to_bb(board)
    empty_cells = expectimax._count_empty(bb)
    c_best_move = expectimax._c_solver.solver_find_best_move(bb, empty_cells)
    print(f"C solver returns: {c_best_move} ({DIRECTION_NAMES.get(c_best_move, 'UNKNOWN')})")
    
# Temporarily disable C solver to test Python fallback
_old_c = expectimax._c_solver
expectimax._c_solver = None
py_best_move = expectimax.find_best_move(board, depth=3)
expectimax._c_solver = _old_c

print(f"Py solver returns: {py_best_move} ({DIRECTION_NAMES.get(py_best_move, 'UNKNOWN')})")
