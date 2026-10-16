#pragma once
typedef int atomic_t;
static inline int atomic_set(atomic_t *value, int next) {
    int previous=*value; *value=next; return previous;
}
static inline int atomic_clear(atomic_t *value) { return atomic_set(value,0); }
