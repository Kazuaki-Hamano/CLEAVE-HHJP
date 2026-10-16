/* SPDX-License-Identifier: MIT */
#pragma once
#include <stdint.h>
#include <stdbool.h>

/* Integer square root avoids floating point and preserves direction-independent gain. */
static inline uint32_t trackpad_isqrt(uint32_t n) {
    uint32_t root = 0, bit = 1u << 30;
    while (bit > n) { bit >>= 2; }
    while (bit) {
        if (n >= root + bit) { n -= root + bit; root = (root >> 1) + bit; }
        else { root >>= 1; }
        bit >>= 2;
    }
    return root;
}
static inline uint32_t trackpad_gain(uint32_t velocity, uint16_t acceleration,
                                     uint16_t maximum) {
    /* velocity: counts per 10 ms. Strength 100% adds 1x at 10 counts/10ms. */
    uint32_t gain = 100u + (uint32_t)acceleration * velocity / 10u;
    return gain > maximum ? maximum : gain;
}
static inline int32_t trackpad_scale(int32_t value, uint16_t speed, uint32_t gain,
                                     int32_t *remainder) {
    int64_t scaled = (int64_t)value * speed * gain + *remainder;
    int32_t result = scaled / 10000;
    *remainder = scaled - (int64_t)result * 10000;
    return result;
}
