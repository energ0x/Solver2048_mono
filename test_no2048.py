import numpy as np
import random
import time
from game_logic import move_board, is_game_over, get_empty_cells, board_changed

# Patch expectimax for NO 2048
import expectimax
old_evaluate = expectimax._evaluate

def new_evaluate(b):
    # Check if 2048 (log=11) exists
    tmp = b
    for _ in range(16):
        if (tmp & 0xF) >= 11:
            return -1e18
        tmp >>= 4
    return old_evaluate(b)

expectimax._evaluate = new_evaluate

random.seed(42)

def add_random_tile(board):
    empty = get_empty_cells(board)
    if not empty: return board
    r, c = random.choice(empty)
    board[r][c] = 2 if random.random() < 0.9 else 4
    return board

def simulate_game(depth=3):
    board = np.zeros((4,4), dtype=int)
    board = add_random_tile(board)
    board = add_random_tile(board)
    moves = 0
    score = 0
    while not is_game_over(board):
        move = expectimax.find_best_move(board, depth=depth)
        if move == -1 or move not in [0,1,2,3]: break
        new_board, merge_score = move_board(board, move)
        if not board_changed(board, new_board): break
        board = new_board
        score += merge_score
        
        # Check if 2048 was reached
        if np.max(board) >= 2048:
            break
            
        board = add_random_tile(board)
        moves += 1
    return int(np.max(board)), moves, score

print('Бенчмарк v5 (NO 2048) — 5 ігор:')
results = []
for i in range(5):
    t0 = time.time()
    max_tile, moves, score = simulate_game(depth=3)
    elapsed = time.time() - t0
    results.append((max_tile, moves, score))
    print(f'  Гра {i+1}: макс={max_tile}, ходів={moves}, очки={score}, час={elapsed:.1f}с')

print(f'\nСередній ходів: {sum(r[1] for r in results)/len(results):.0f}')
print(f'Середні очки: {sum(r[2] for r in results)/len(results):.0f}')
