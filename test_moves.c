#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>

#define ROW_MASK 0xFFFFULL

static uint64_t row_left_table[65536];
static uint64_t row_right_table[65536];
static int row_score_table[65536];

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
    for (int row = 0; row < 65536; row++) {
        int cells[4];
        for (int i = 0; i < 4; i++) cells[i] = (row >> (i * 4)) & 0xF;
        int res[4] = {0}, merged[4] = {0}, pos = 0, score = 0;
        for (int i = 0; i < 4; i++) {
            if (cells[i] == 0) continue;
            if (pos > 0 && res[pos-1] == cells[i] && !merged[pos-1]) {
                res[pos-1]++;
                merged[pos-1] = 1;
                score += (1 << res[pos-1]);
            } else {
                res[pos] = cells[i];
                merged[pos] = 0;
                pos++;
            }
        }
        uint64_t left = 0;
        for (int i = 0; i < 4; i++) left |= ((uint64_t)res[i] << (i * 4));
        row_left_table[row] = left;
        row_score_table[row] = score;

        int rc[4] = {cells[3], cells[2], cells[1], cells[0]};
        int rr[4] = {0}, rm[4] = {0}, p = 0, sc = 0;
        for (int i = 0; i < 4; i++) {
            if (rc[i] == 0) continue;
            if (p > 0 && rr[p-1] == rc[i] && !rm[p-1]) {
                rr[p-1]++;
                rm[p-1] = 1;
                sc += (1 << rr[p-1]);
            } else {
                rr[p] = rc[i];
                rm[p] = 0;
                p++;
            }
        }
        uint64_t right = 0;
        for (int i = 0; i < 4; i++) right |= ((uint64_t)rr[3-i] << (i * 4));
        row_right_table[row] = right;
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

void print_board(uint64_t b) {
    for (int r=0; r<4; r++) {
        for (int c=0; c<4; c++) {
            int v = (b >> ((r*4+c)*4)) & 0xF;
            printf("%4d ", v == 0 ? 0 : (1 << v));
        }
        printf("\n");
    }
}

int main() {
    init_tables();
    
    // Board from user
    // row 0: 0 0 0 4 -> log: 0 0 0 2
    // row 1: 0 0 2 8 -> log: 0 0 1 3
    // row 2: 2 2 8 4 -> log: 1 1 3 2
    // row 3: 4 16 2 8 -> log: 2 4 1 3
    
    uint64_t bb = 0;
    int board_arr[16] = {0,0,0,2, 0,0,1,3, 1,1,3,2, 2,4,1,3};
    for(int i=0; i<16; i++) {
        bb |= ((uint64_t)board_arr[i] << (i*4));
    }
    
    printf("Original:\n");
    print_board(bb);
    
    printf("\nLeft:\n");
    print_board(execute_move_left(bb));
    
    printf("\nRight:\n");
    print_board(execute_move_right(bb));
    
    printf("\nUp:\n");
    print_board(execute_move_up(bb));
    
    printf("\nDown:\n");
    print_board(execute_move_down(bb));
    
    return 0;
}
