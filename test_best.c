#include <stdio.h>
#include <stdint.h>
#include "solver.c"

int main() {
    init_tables();
    int board_arr[16] = {0,0,0,2, 0,0,1,3, 1,1,3,2, 2,4,1,3};
    uint64_t bb = 0;
    for(int i=0; i<16; i++) {
        bb |= ((uint64_t)board_arr[i] << (i*4));
    }
    int best = solver_find_best_move(bb, 2);
    printf("Best move inside C: %d\n", best);
    return 0;
}
