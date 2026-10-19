#pragma once
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#define ARG_UNUSED(x) (void)(x)
#define MIN(a,b) ((a) < (b) ? (a) : (b))
#define CLAMP(x,lo,hi) MIN(((x) < (lo) ? (lo) : (x)),hi)
int64_t k_uptime_get(void);
#define DEVICE_DT_DEFINE(...)
