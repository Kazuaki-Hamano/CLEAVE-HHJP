/* SPDX-License-Identifier: MIT */
#include <zephyr/kernel.h>
#include <drivers/input_processor.h>
#include "trackpad_settings.h"
#include "trackpad_math.h"

/* Both axes in a packet use the same gain, derived from the preceding packet.
 * This adds one sample of smoothing without changing the pointer's direction. */
struct pointer_state {
    int32_t x, y, remainder[2];
    int64_t last;
    uint32_t velocity, gain, generation;
    bool packet;
};
static struct pointer_state pointer;
static int pointer_process(const struct device *dev, struct input_event *event,
                           uint32_t p1, uint32_t p2,
                           struct zmk_input_processor_state *state) {
    ARG_UNUSED(dev); ARG_UNUSED(p1); ARG_UNUSED(p2); ARG_UNUSED(state);
    if (event->type != INPUT_EV_REL ||
        (event->code != INPUT_REL_X && event->code != INPUT_REL_Y)) {
        return ZMK_INPUT_PROC_CONTINUE;
    }
    struct cleave_trackpad_config cfg;
    uint32_t generation;
    cleave_trackpad_get(&cfg, &generation);
    int64_t now = k_uptime_get();
    if (generation != pointer.generation || now - pointer.last > 150) {
        pointer = (struct pointer_state){.generation = generation, .last = now};
    }
    if (!pointer.packet) {
        pointer.gain = trackpad_gain(pointer.velocity, cfg.acceleration, cfg.maximum);
        pointer.packet = true;
    }
    bool is_y = event->code == INPUT_REL_Y;
    if (is_y) { pointer.y = event->value; } else { pointer.x = event->value; }
    event->value = trackpad_scale(event->value, cfg.speed, pointer.gain,
                                  &pointer.remainder[is_y]);
    if (event->sync) {
        uint32_t dt = CLAMP(now - pointer.last, 1, 100);
        uint32_t distance = trackpad_isqrt(pointer.x * pointer.x + pointer.y * pointer.y);
        uint32_t velocity = MIN(distance * 10u / dt, 1000u);
        pointer.velocity = (pointer.velocity + velocity) / 2;
        pointer.last = now;
        pointer.x = pointer.y = 0;
        pointer.packet = false;
    }
    return ZMK_INPUT_PROC_CONTINUE;
}
static const struct zmk_input_processor_driver_api pointer_api = {
    .handle_event = pointer_process,
};
DEVICE_DT_DEFINE(DT_NODELABEL(trackpad_speed), NULL, NULL, NULL, NULL,
                 POST_KERNEL, CONFIG_KERNEL_INIT_PRIORITY_DEFAULT, &pointer_api);

static int scroll_process(const struct device *dev, struct input_event *event,
                          uint32_t p1, uint32_t p2,
                          struct zmk_input_processor_state *state) {
    ARG_UNUSED(dev); ARG_UNUSED(p1); ARG_UNUSED(p2); ARG_UNUSED(state);
    static int32_t remainder;
    static int64_t last;
    static uint32_t previous_generation;
    if (event->type != INPUT_EV_REL) { return ZMK_INPUT_PROC_CONTINUE; }
    if (event->code == INPUT_REL_X) { event->value = 0; }
    else if (event->code == INPUT_REL_Y) {
        struct cleave_trackpad_config cfg;
        uint32_t generation;
        cleave_trackpad_get(&cfg, &generation);
        int64_t now = k_uptime_get();
        if (generation != previous_generation || now - last > 150) { remainder = 0; }
        previous_generation = generation;
        last = now;
        event->code = INPUT_REL_WHEEL;
        event->value = trackpad_scroll(event->value, cfg.scroll, &remainder);
    }
    return ZMK_INPUT_PROC_CONTINUE;
}
static const struct zmk_input_processor_driver_api scroll_api = {
    .handle_event = scroll_process,
};
DEVICE_DT_DEFINE(DT_NODELABEL(trackpad_scroll), NULL, NULL, NULL, NULL,
                 POST_KERNEL, CONFIG_KERNEL_INIT_PRIORITY_DEFAULT, &scroll_api);
