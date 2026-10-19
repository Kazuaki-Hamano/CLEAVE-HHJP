/* SPDX-License-Identifier: MIT */
#include <zephyr/kernel.h>
#include <drivers/input_processor.h>
#include "trackpad_settings.h"
#include "trackpad_math.h"
#include <zmk/keymap.h>
#include <zephyr/sys/atomic.h>
#include "trackpad_navigation.h"

/* Both axes in a packet use the same gain, derived from the preceding packet.
 * This adds one sample of smoothing without changing the pointer's direction. */
struct pointer_state {
    int32_t x, y, remainder[2];
    int64_t last;
    uint32_t velocity, gain, generation;
    bool packet;
};
static struct pointer_state remote_pointer;
static int32_t native_remainder;
static uint32_t native_generation;
static int pointer_process(const struct device *dev, struct input_event *event,
                           uint32_t p1, uint32_t p2,
                           struct zmk_input_processor_state *state) {
    ARG_UNUSED(p1); ARG_UNUSED(p2); ARG_UNUSED(state);
    struct pointer_state *pointer = dev->data;
    if (event->type == INPUT_EV_REL && event->code == INPUT_REL_WHEEL) {
        struct cleave_trackpad_config cfg;
        uint32_t generation;
        cleave_trackpad_get(&cfg, &generation);
        if (generation != native_generation) {
            native_remainder = 0;
            native_generation = generation;
        }
        event->value = trackpad_scale(event->value, cfg.native_scroll, 100,
                                      &native_remainder);
        return ZMK_INPUT_PROC_CONTINUE;
    }
    if (event->type != INPUT_EV_REL ||
        (event->code != INPUT_REL_X && event->code != INPUT_REL_Y)) {
        return ZMK_INPUT_PROC_CONTINUE;
    }
    struct cleave_trackpad_config cfg;
    uint32_t generation;
    cleave_trackpad_get(&cfg, &generation);
    int64_t now = k_uptime_get();
    if (generation != pointer->generation || now - pointer->last > 150) {
        *pointer = (struct pointer_state){.generation = generation, .last = now};
    }
    if (!pointer->packet) {
        pointer->gain = trackpad_gain(pointer->velocity, cfg.acceleration, cfg.maximum);
        pointer->packet = true;
    }
    bool is_y = event->code == INPUT_REL_Y;
    if (is_y) { pointer->y = event->value; } else { pointer->x = event->value; }
    event->value = trackpad_scale(event->value, cfg.speed, pointer->gain,
                                  &pointer->remainder[is_y]);
    if (event->sync) {
        uint32_t dt = CLAMP(now - pointer->last, 1, 100);
        uint32_t distance = trackpad_isqrt(pointer->x * pointer->x + pointer->y * pointer->y);
        uint32_t velocity = MIN(distance * 10u / dt, 1000u);
        pointer->velocity = (pointer->velocity + velocity) / 2;
        pointer->last = now;
        pointer->x = pointer->y = 0;
        pointer->packet = false;
    }
    return ZMK_INPUT_PROC_CONTINUE;
}
static const struct zmk_input_processor_driver_api pointer_api = {
    .handle_event = pointer_process,
};
DEVICE_DT_DEFINE(DT_NODELABEL(trackpad_speed), NULL, NULL, &remote_pointer, NULL,
                 POST_KERNEL, CONFIG_KERNEL_INIT_PRIORITY_DEFAULT, &pointer_api);

struct scroll_state {
    int32_t remainder;
    int64_t last;
    uint32_t generation;
};
static struct scroll_state remote_scroll;

static int scroll_process(const struct device *dev, struct input_event *event,
                          uint32_t p1, uint32_t p2,
                          struct zmk_input_processor_state *state) {
    ARG_UNUSED(p1); ARG_UNUSED(p2); ARG_UNUSED(state);
    struct scroll_state *scroll = dev->data;
    if (event->type != INPUT_EV_REL) { return ZMK_INPUT_PROC_CONTINUE; }
    if (event->code == INPUT_REL_X) { event->value = 0; }
    else if (event->code == INPUT_REL_Y) {
        struct cleave_trackpad_config cfg;
        uint32_t generation;
        cleave_trackpad_get(&cfg, &generation);
        int64_t now = k_uptime_get();
        if (generation != scroll->generation || now - scroll->last > 150) { scroll->remainder = 0; }
        scroll->generation = generation;
        scroll->last = now;
        event->code = INPUT_REL_WHEEL;
        event->value = trackpad_scroll(event->value, cfg.scroll, &scroll->remainder);
    }
    return ZMK_INPUT_PROC_CONTINUE;
}
static const struct zmk_input_processor_driver_api scroll_api = {
    .handle_event = scroll_process,
};
DEVICE_DT_DEFINE(DT_NODELABEL(trackpad_scroll), NULL, NULL, &remote_scroll, NULL,
                 POST_KERNEL, CONFIG_KERNEL_INIT_PRIORITY_DEFAULT, &scroll_api);


struct local_control_state {
    int32_t remainder[2], x, y;
    int64_t last_motion;
    uint32_t generation;
    bool fn, fired;
};
static struct local_control_state local_control;
static atomic_t local_reset;
void cleave_trackpad_reset_local(void) { atomic_set(&local_reset, 1); }
static int local_control_process(const struct device *dev, struct input_event *event,
                                  uint32_t p1, uint32_t p2,
                                  struct zmk_input_processor_state *state) {
    ARG_UNUSED(dev); ARG_UNUSED(p1); ARG_UNUSED(p2); ARG_UNUSED(state);
    bool fn = zmk_keymap_layer_active(1);
    int64_t now = k_uptime_get();
    struct cleave_trackpad_config cfg;
    uint32_t generation;
    cleave_trackpad_get(&cfg, &generation);
    if (atomic_clear(&local_reset) || fn != local_control.fn || generation != local_control.generation) {
        local_control = (struct local_control_state){.fn=fn, .generation=generation};
    }
    if (event->type != INPUT_EV_REL ||
        (event->code != INPUT_REL_X && event->code != INPUT_REL_Y)) {
        return ZMK_INPUT_PROC_CONTINUE;
    }
    if (event->value) {
        if (now - local_control.last_motion >= 180) {
            local_control.x = local_control.y = 0;
            local_control.fired = false;
            local_control.remainder[0] = local_control.remainder[1] = 0;
        }
        local_control.last_motion = now;
    }
    bool y = event->code == INPUT_REL_Y;
    if (!fn) {
        event->code = y ? INPUT_REL_WHEEL : INPUT_REL_HWHEEL;
        event->value = trackpad_scroll(y ? event->value : -event->value,
                                      cfg.scroll, &local_control.remainder[y]);
    } else {
        if (!local_control.fired) {
            /* Bound accumulated movement even for long vertical strokes. */
            if (y) { local_control.y = CLAMP(local_control.y + event->value, -4096, 4096); }
            else { local_control.x = CLAMP(local_control.x + event->value, -4096, 4096); }
            int32_t x = local_control.x < 0 ? -local_control.x : local_control.x;
            int32_t v = local_control.y < 0 ? -local_control.y : local_control.y;
            if (event->sync && x >= 64 && x >= 2 * v) {
                cleave_trackpad_navigate(local_control.x > 0);
                local_control.fired = true;
            }
        }
        event->value = 0;
    }
    return ZMK_INPUT_PROC_CONTINUE;
}
static const struct zmk_input_processor_driver_api local_control_api = {
    .handle_event = local_control_process,
};
DEVICE_DT_DEFINE(DT_NODELABEL(trackpad_local_control), NULL, NULL, NULL, NULL,
                 POST_KERNEL, CONFIG_KERNEL_INIT_PRIORITY_DEFAULT, &local_control_api);
