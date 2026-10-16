#include <assert.h>
#include <stdio.h>
#include "../../src/trackpad_math.h"
int main(void) {
    assert(trackpad_isqrt(0) == 0 && trackpad_isqrt(25) == 5);
    assert(trackpad_isqrt(3*3+4*4) == 5);
    assert(trackpad_gain(100, 0, 800) == 100);
    assert(trackpad_gain(10, 100, 800) == 200);
    assert(trackpad_gain(1000, 300, 300) == 300);
    assert(trackpad_gain(1000, 300, 100) == 100);
    int32_t remainder = 0, total = 0;
    for (int i = 0; i < 100; i++) { total += trackpad_scale(1, 25, 100, &remainder); }
    assert(total == 25 && remainder == 0);
    for (int i = 0; i < 100; i++) { total += trackpad_scale(-1, 25, 100, &remainder); }
    assert(total == 0 && remainder == 0);
    int32_t rx = 0, ry = 0;
    assert(trackpad_scale(30, 200, 300, &rx) == 180);
    assert(trackpad_scale(-40, 200, 300, &ry) == -240);
    puts("Trackpad speed, fractional movement, acceleration cap and symmetry: PASS");
}
