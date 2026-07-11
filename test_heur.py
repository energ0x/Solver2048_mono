import numpy as np
import random
import time
from expectimax import find_best_move, _evaluate, _np_to_bb, _WROW

def test_fixed_wrow():
    # Overwrite _evaluate to use ONLY fixed WROW[0] + empty bonus scaled
    import expectimax
    def new_evaluate(b):
        is_empty = False
        tmp = b
        empty = 0
        for _ in range(16):
            if (tmp & 0xF) == 0:
                is_empty = True
                empty += 1
            tmp >>= 4
        
        if not is_empty:
            can_move = False
            for mf in expectimax._MOVES:
                if mf(b)[0] != b:
                    can_move = True
                    break
            if not can_move:
                return -1e18
                
        r0 = (b >> 48) & 0xFFFF
        r1 = (b >> 32) & 0xFFFF
        r2 = (b >> 16) & 0xFFFF
        r3 = b & 0xFFFF
        
        score = _WROW[0][0][r0] + _WROW[0][1][r1] + _WROW[0][2][r2] + _WROW[0][3][r3]
        
        # Penalize having tiles not in the snake order? The matrix does that.
        # Give bonus for empty cells (scaled by max tile to be relevant)
        max_log = expectimax._get_max_log(b)
        max_val = expectimax._POW[max_log]
        score += empty * max_val * 100.0  # arbitrary scale
        
        return score
        
    expectimax._evaluate = new_evaluate
    
    # Simulate a game
    random.seed(42)
    def add_random_tile(board):
        from game_logic import get_empty_cells
        empty_cells = get_empty_cells(board)
        if not empty_cells: return board
        r, c = random.choice(empty_cells)
        board[r][c] = 2 if random.random() < 0.9 else 4
        return board

    from game_logic import move_board, is_game_over, board_changed
    board = np.zeros((4,4), dtype=int)
    board = add_random_tile(board)
    board = add_random_tile(board)
    moves = 0
    while not is_game_over(board):
        move = expectimax.find_best_move(board, depth=3) # low depth for speed
        if move == -1 or move not in [0,1,2,3]: break
        new_board, _ = move_board(board, move)
        if not board_changed(board, new_board): break
        board = new_board
        board = add_random_tile(board)
        moves += 1
    return int(np.max(board)), moves

t0 = time.time()
m, moves = test_fixed_wrow()
print(f"Fixed WROW: Max={m}, Moves={moves}, Time={time.time()-t0:.1f}s")
