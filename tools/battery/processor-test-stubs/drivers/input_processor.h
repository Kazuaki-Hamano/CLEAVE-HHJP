#pragma once
#include <zephyr/kernel.h>
struct device { void *data; };
struct input_event { uint8_t type; uint16_t code; int32_t value; bool sync; };
struct zmk_input_processor_state { unsigned unused; };
struct zmk_input_processor_driver_api {
    int (*handle_event)(const struct device *, struct input_event *, uint32_t, uint32_t,
                        struct zmk_input_processor_state *);
};
#define INPUT_EV_REL 2
#define INPUT_EV_KEY 1
#define INPUT_REL_X 0
#define INPUT_REL_Y 1
#define INPUT_REL_WHEEL 8
#define INPUT_REL_HWHEEL 6
#define ZMK_INPUT_PROC_CONTINUE 0
