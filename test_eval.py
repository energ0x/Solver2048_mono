import numpy as np
import random
import time
from game_logic import move_board, is_game_over, get_empty_cells, board_changed
import expectimax

# Patch expectimax to include corner penalty and remove 1024 merge bonus
def _build_new_heur():
    for rv in range(65536):
        c0 = (rv >> 12) & 0xF
        c1 = (rv >> 8) & 0xF
        c2 = (rv >> 4) & 0xF
        c3 = rv & 0xF
        cells = [c0, c1, c2, c3]

        score = 0.0

        # Порожні клітинки
        empty = sum(1 for x in cells if x == 0)
        score += empty * 1000.0 # Збільшимо вагу пустих клітинок

        # Монотонність
        inc = dec = 0
        for i in range(3):
            if cells[i] > cells[i + 1]:
                dec += (cells[i] ** 4.0) - (cells[i + 1] ** 4.0)
            elif cells[i] < cells[i + 1]:
                inc += (cells[i + 1] ** 4.0) - (cells[i] ** 4.0)
        score -= min(inc, dec) * 47.0

        # Гладкість
        for i in range(3):
            if cells[i] != 0 and cells[i + 1] != 0:
                score -= abs((cells[i] ** 3.5) - (cells[i + 1] ** 3.5)) * 11.0

        # Потенціал злиття (ТІЛЬКИ ДЛЯ ПЛИТОК < 1024)
        for i in range(3):
            if cells[i] != 0 and cells[i] == cells[i + 1]:
                if cells[i] < 10:  # < 1024
                    score += (cells[i] ** 1.0) * 700.0

        expectimax._HEUR[rv] = score

_build_new_heur()

old_evaluate = expectimax._evaluate
def new_evaluate(b):
    mx = expectimax._get_max_log(b)
    if mx >= 11:
        return -1e18
        
    r0 = (b >> 48) & 0xFFFF
    r1 = (b >> 32) & 0xFFFF
    r2 = (b >> 16) & 0xFFFF
    r3 = b & 0xFFFF

    heur = expectimax._HEUR[r0] + expectimax._HEUR[r1] + expectimax._HEUR[r2] + expectimax._HEUR[r3]
    for c in range(4):
        s = (3 - c) << 2
        col = (((b >> (48 + s)) & 0xF) << 12 |
               ((b >> (32 + s)) & 0xF) << 8 |
               ((b >> (16 + s)) & 0xF) << 4 |
               ((b >> s) & 0xF))
        heur += expectimax._HEUR[col]

    # Corner penalty
    if mx > 0:
        top_left = (b >> 60) & 0xF
        if top_left != mx:
            heur -= 500000.0
            
    return heur

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
        
        if np.max(board) >= 2048:
            break
            
        board = add_random_tile(board)
        moves += 1
    return int(np.max(board)), moves, score

print('Бенчмарк v6 (Corner penalty + No 1024 merge bonus) — 5 ігор:')
results = []
for i in range(5):
    t0 = time.time()
    max_tile, moves, score = simulate_game(depth=3)
    elapsed = time.time() - t0
    results.append((max_tile, moves, score))
    print(f'  Гра {i+1}: макс={max_tile}, ходів={moves}, очки={score}, час={elapsed:.1f}с')

print(f'\nСередній ходів: {sum(r[1] for r in results)/len(results):.0f}')
print(f'Середні очки: {sum(r[2] for r in results)/len(results):.0f}')
