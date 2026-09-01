#include <stdio.h>
#include <stdint.h>

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

void print_board(uint64_t b) {
    for (int r=0; r<4; r++) {
        for (int c=0; c<4; c++) {
            printf("%x ", (int)((b >> ((r*4+c)*4)) & 0xF));
        }
        printf("\n");
    }
    printf("\n");
}

int main() {
    uint64_t b = 0x0123456789ABCDEFULL; // Wait, row 0 is MSB or LSB?
    // Let's set it explicitly:
    // (r,c) = i. Bit shift = i*4
    uint64_t b2 = 0;
    for (int i=0; i<16; i++) {
        b2 |= ((uint64_t)i) << (i*4);
    }
    printf("Original:\n");
    print_board(b2);
    
    printf("Transposed:\n");
    print_board(transpose(b2));
    
    return 0;
}
