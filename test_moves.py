import numpy as np
from expectimax import _np_to_bb, _expectimax, _MOVES

board = np.array([
    [256, 4, 512, 1024],
    [32, 128, 64, 32],
    [2, 16, 32, 16],
    [0, 4, 8, 4]
])
bb = _np_to_bb(board)

for i, mf in enumerate(_MOVES):
    moved, _ = mf(bb)
    if moved == bb:
        print(f"Move {i} is invalid")
    else:
        val = _expectimax(moved, 6, False)
        print(f"Move {i} val = {val}")
