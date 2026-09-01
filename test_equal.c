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
    uint64_t md = execute_move_down(bb);
    printf("bb = %llx\n", (unsigned long long)bb);
    printf("md = %llx\n", (unsigned long long)md);
    printf("equal? %d\n", bb == md);
    return 0;
}
