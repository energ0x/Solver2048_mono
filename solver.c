#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <math.h>

#define TT_SIZE (16777216) // 16 million
#define TT_MASK (TT_SIZE - 1)

typedef struct {
    uint64_t key;
    float    value;
    int      depth;
    uint8_t  flag;
} TTEntry;

static TTEntry *tt = NULL;

#define ROW_MASK 0xFFFFULL

static uint64_t row_left_table[65536];
static uint64_t row_right_table[65536];
static float row_eval_table[65536];

static uint64_t transpose(uint64_t x) {
    uint64_t a1 = x & 0xF0F00F0FF0F00F0FULL;
    uint64_t a2 = x & 0x0000F0F00000F0F0ULL;
    uint64_t a3 = x & 0x0F0F00000F0F0000ULL;
    uint64_t a  = a1 | (a2 << 12) | (a3 >> 12);
    uint64_t b1 = a & 0xFF00FF0000FF00FFULL;
    uint64_t b2 = a & 0x00FF00FF00000000ULL;
    uint64_t b3 = a & 0x00000000FF00FF00ULL;
    return b1 | (b2 >> 24) | (b3 << 24);
}

static inline uint16_t get_row(uint64_t board, int row) {
    return (board >> (row * 16)) & ROW_MASK;
}

static void init_tables(void) {
    static int done = 0;
    if (done) return;
    done = 1;

    for (int row = 0; row < 65536; row++) {
        int cells[4];
        for (int i = 0; i < 4; i++) cells[i] = (row >> (i * 4)) & 0xF;

        /* LEFT */
        int res[4] = {0}, merged[4] = {0}, pos = 0;
        for (int i = 0; i < 4; i++) {
            if (cells[i] == 0) continue;
            if (pos > 0 && res[pos-1] == cells[i] && !merged[pos-1]) {
                res[pos-1]++;
                merged[pos-1] = 1;
            } else {
                res[pos] = cells[i];
                merged[pos] = 0;
                pos++;
            }
        }
        uint64_t left = 0;
        for (int i = 0; i < 4; i++) left |= ((uint64_t)res[i] << (i * 4));
        row_left_table[row] = left;

        /* RIGHT */
        int rc[4] = {cells[3], cells[2], cells[1], cells[0]};
        int rr[4] = {0}, rm[4] = {0}, p = 0;
        for (int i = 0; i < 4; i++) {
            if (rc[i] == 0) continue;
            if (p > 0 && rr[p-1] == rc[i] && !rm[p-1]) {
                rr[p-1]++;
                rm[p-1] = 1;
            } else {
                rr[p] = rc[i];
                rm[p] = 0;
                p++;
            }
        }
        uint64_t right = 0;
        for (int i = 0; i < 4; i++) right |= ((uint64_t)rr[3-i] << (i * 4));
        row_right_table[row] = right;

        /* EVALUATION */
        float eval = 0.0f;
        int empty = 0;
        for (int i = 0; i < 4; i++) {
            if (cells[i] == 0) empty++;
        }
        // 900 for empty cell (1800 total when row + col)
        eval += 900.0f * empty;

        // Monotonicity (decreasing is good)
        for (int i = 0; i < 3; i++) {
            if (cells[i] != 0 && cells[i+1] != 0) {
                if (cells[i+1] > cells[i]) {
                    int d = cells[i+1] - cells[i];
                    eval -= 50.0f * (d * d * d * d);
                }
            }
        }

        // Smoothness
        for (int i = 0; i < 3; i++) {
            if (cells[i] != 0 && cells[i+1] != 0) {
                int d = cells[i] - cells[i+1];
                if (d < 0) d = -d;
                eval -= 10.0f * d;
            }
        }

        // Adjacent 1024
        for (int i = 0; i < 3; i++) {
            if (cells[i] == 10 && cells[i+1] == 10) {
                eval -= 50000.0f;
            }
        }

        row_eval_table[row] = eval;
    }
}

static uint64_t execute_move_left(uint64_t board) {
    uint64_t r = 0;
    for (int i = 0; i < 4; i++) {
        uint16_t row = get_row(board, i);
        r |= (row_left_table[row] << (i * 16));
    }
    return r;
}

static uint64_t execute_move_right(uint64_t board) {
    uint64_t r = 0;
    for (int i = 0; i < 4; i++) {
        uint16_t row = get_row(board, i);
        r |= (row_right_table[row] << (i * 16));
    }
    return r;
}

static uint64_t execute_move_up(uint64_t board) {
    uint64_t t = transpose(board);
    t = execute_move_left(t);
    return transpose(t);
}

static uint64_t execute_move_down(uint64_t board) {
    uint64_t t = transpose(board);
    t = execute_move_right(t);
    return transpose(t);
}

static int can_move(uint64_t board) {
    if (execute_move_left(board)  != board) return 1;
    if (execute_move_right(board) != board) return 1;
    uint64_t t = transpose(board);
    if (execute_move_left(t)      != t)     return 1;
    if (execute_move_right(t)     != t)     return 1;
    return 0;
}

static int get_max_log(uint64_t board) {
    int max = 0;
    for (int i = 0; i < 16; i++) {
        int v = (board >> (i * 4)) & 0xF;
        if (v > max) max = v;
    }
    return max;
}

static float evaluate(uint64_t board) {
    if (!can_move(board)) return 0.0f;
    if (get_max_log(board) >= 11) return -INFINITY;

    float score = 0.0f;
    uint64_t t = transpose(board);

    for (int i = 0; i < 4; i++) {
        score += row_eval_table[(board >> (i * 16)) & 0xFFFF];
        score += row_eval_table[(t >> (i * 16)) & 0xFFFF];
    }

    // Global corner penalty
    int max_log = get_max_log(board);
    if ((board & 0xF) != max_log) { // (0,0) is bits 0-3
        score -= 500000.0f;
    }

    return score;
}

static void init_tt(void) {
    if (!tt) tt = (TTEntry*)calloc(TT_SIZE, sizeof(TTEntry));
}

static inline int tt_idx(uint64_t k) {
    return (int)((k ^ (k >> 32)) & TT_MASK);
}

static float expectimax(uint64_t board, int depth, int is_player) {
    if (get_max_log(board) >= 11) return -INFINITY;
    if (!can_move(board)) return 0.0f;
    if (depth <= 0) return evaluate(board);

    int idx = tt_idx(board);
    if (tt[idx].key == board && tt[idx].flag && tt[idx].depth >= depth)
        return tt[idx].value;

    float result;

    if (is_player) {
        result = -INFINITY;
        uint64_t m[4] = {
            execute_move_up(board),
            execute_move_down(board),
            execute_move_left(board),
            execute_move_right(board)
        };
        for (int i = 0; i < 4; i++) {
            if (m[i] == board) continue;
            float v = expectimax(m[i], depth - 1, 0);
            if (v > result) result = v;
        }
    } else {
        int empty_pos[16], n = 0;
        for (int i = 0; i < 16; i++) {
            if (((board >> (i * 4)) & 0xF) == 0) {
                empty_pos[n++] = i;
            }
        }
        if (n == 0) return evaluate(board);

        result = 0.0f;
        float p2 = 0.9f / n;
        float p4 = 0.1f / n;

        for (int i = 0; i < n; i++) {
            int pos = empty_pos[i];
            uint64_t b2 = board | (1ULL << (pos * 4));
            uint64_t b4 = board | (2ULL << (pos * 4));
            result += p2 * expectimax(b2, depth - 1, 1);
            result += p4 * expectimax(b4, depth - 1, 1);
        }
    }

    tt[idx].key   = board;
    tt[idx].value = result;
    tt[idx].depth = depth;
    tt[idx].flag  = 1;
    return result;
}

int solver_find_best_move(uint64_t board, int empty_cells) {
    init_tables();
    init_tt();

    int depth;
    if (empty_cells > 8)       depth = 4;
    else if (empty_cells >= 4) depth = 6;
    else if (empty_cells >= 1) depth = 10;
    else                       depth = 14;

    int best_move = -1;
    float best_val = -INFINITY;

    // MATCHES controller.py mapping EXACTLY
    // 0 = UP, 1 = DOWN, 2 = LEFT, 3 = RIGHT
    uint64_t m[4] = {
        execute_move_up(board),
        execute_move_down(board),
        execute_move_left(board),
        execute_move_right(board)
    };

    for (int i = 0; i < 4; i++) {
        if (m[i] == board) continue;
        if (get_max_log(m[i]) >= 11) continue;
        float v = expectimax(m[i], depth, 0);
        if (v > best_val) {
            best_val = v;
            best_move = i;
        }
    }

    return best_move;
}

uint64_t solver_board_to_bitboard(int *board) {
    uint64_t b = 0;
    for (int i = 0; i < 16; i++) {
        int v = board[i], logv = 0;
        if (v > 0) {
            while (v > 1) { logv++; v >>= 1; }
        }
        b |= ((uint64_t)logv << (i * 4));
    }
    return b;
}

void solver_bitboard_to_board(uint64_t b, int *board) {
    for (int i = 0; i < 16; i++) {
        int logv = (b >> (i * 4)) & 0xF;
        board[i] = logv ? (1 << logv) : 0;
    }
}

uint64_t solver_execute_move(uint64_t board, int direction) {
    init_tables();
    switch (direction) {
        case 0: return execute_move_up(board);
        case 1: return execute_move_down(board);
        case 2: return execute_move_left(board);
        case 3: return execute_move_right(board);
    }
    return board;
}
