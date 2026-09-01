import numpy as np
import random
import time
from game_logic import move_board, is_game_over, get_empty_cells, board_changed
import expectimax

_EMPTIES = [0] * 65536

def _build_new_heur():
    for rv in range(65536):
        c0 = (rv >> 12) & 0xF
        c1 = (rv >> 8) & 0xF
        c2 = (rv >> 4) & 0xF
        c3 = rv & 0xF
        cells = [c0, c1, c2, c3]

        score = 0.0
        empties = sum(1 for x in cells if x == 0)
        _EMPTIES[rv] = empties

        # Adj Penalty (>= 256 is log >= 8)
        for i in range(3):
            if cells[i] >= 8 and cells[i] == cells[i+1]:
                score -= 1000000.0

        # Farm Bonus (< 256)
        for i in range(3):
            if cells[i] != 0 and cells[i] == cells[i+1] and cells[i] < 8:
                score += (cells[i] ** 2.0) * 50.0

        # Mild monotonicity/smoothness to organize small tiles
        inc = dec = 0
        for i in range(3):
            if cells[i] > cells[i + 1]:
                dec += (cells[i] ** 3.0) - (cells[i + 1] ** 3.0)
            elif cells[i] < cells[i + 1]:
                inc += (cells[i + 1] ** 3.0) - (cells[i] ** 3.0)
        score -= min(inc, dec) * 20.0

        expectimax._HEUR[rv] = score

_build_new_heur()

def new_evaluate(b):
    mx = expectimax._get_max_log(b)
    if mx >= 11:
        return -1e18
        
    r0 = (b >> 48) & 0xFFFF
    r1 = (b >> 32) & 0xFFFF
    r2 = (b >> 16) & 0xFFFF
    r3 = b & 0xFFFF

    total_empty = _EMPTIES[r0] + _EMPTIES[r1] + _EMPTIES[r2] + _EMPTIES[r3]
    if total_empty == 0:
        can_move = False
        for mf in expectimax._MOVES:
            if mf(b)[0] != b:
                can_move = True
                break
        if not can_move:
            return -1e18

    heur = expectimax._HEUR[r0] + expectimax._HEUR[r1] + expectimax._HEUR[r2] + expectimax._HEUR[r3]
    for c in range(4):
        s = (3 - c) << 2
        col = (((b >> (48 + s)) & 0xF) << 12 |
               ((b >> (32 + s)) & 0xF) << 8 |
               ((b >> (16 + s)) & 0xF) << 4 |
               ((b >> s) & 0xF))
        heur += expectimax._HEUR[col]

    # Free bonus
    heur += (2.0 ** total_empty) * 500.0

    # Dist
    if mx >= 8:
        mx_coords = []
        mx2_coords = []
        tmp = b
        for pos in range(16):
            val = tmp & 0xF
            if val == mx:
                mx_coords.append((pos // 4, pos % 4))
            elif val == mx - 1:
                mx2_coords.append((pos // 4, pos % 4))
            tmp >>= 4
            
        if len(mx_coords) >= 2:
            max_dist = 0
            for i in range(len(mx_coords)):
                for j in range(i+1, len(mx_coords)):
                    d = abs(mx_coords[i][0] - mx_coords[j][0]) + abs(mx_coords[i][1] - mx_coords[j][1])
                    if d > max_dist: max_dist = d
            heur += max_dist * 200000.0
        elif mx_coords and mx2_coords:
            max_dist = 0
            for c1 in mx_coords:
                for c2 in mx2_coords:
                    d = abs(c1[0] - c2[0]) + abs(c1[1] - c2[1])
                    if d > max_dist: max_dist = d
            heur += max_dist * 100000.0

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

print('Бенчмарк v8 (Custom Dist/Farm/Adj) — 5 ігор:')
results = []
for i in range(5):
    t0 = time.time()
    max_tile, moves, score = simulate_game(depth=3)
    elapsed = time.time() - t0
    results.append((max_tile, moves, score))
    print(f'  Гра {i+1}: макс={max_tile}, ходів={moves}, очки={score}, час={elapsed:.1f}с')

print(f'\nСередній ходів: {sum(r[1] for r in results)/len(results):.0f}')
print(f'Середні очки: {sum(r[2] for r in results)/len(results):.0f}')
