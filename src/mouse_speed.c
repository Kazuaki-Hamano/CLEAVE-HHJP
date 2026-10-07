/* SPDX-License-Identifier: MIT */
#include <zephyr/device.h>
#include <zephyr/sys/atomic.h>
#include <drivers/behavior.h>
#include <drivers/input_processor.h>
#include <dt-bindings/zmk/keys.h>
#include <zmk/behavior.h>
#include <zmk/hid.h>

/* Mode 0/1/2: 300/600/1200 at the base movement speed of 600.
 * Commands 3/4 are held precision/boost keys, without sending Shift/Alt to the host.
 * Selection is intentionally RAM-only and starts at normal after reboot. */
static atomic_t selected_mode = ATOMIC_INIT(1);
static atomic_t precision_held;
static atomic_t boost_held;

static int speed_pressed(struct zmk_behavior_binding *binding,
                         struct zmk_behavior_binding_event event) {
    switch (binding->param1) {
    case 0: case 1: case 2:
        atomic_set(&selected_mode, binding->param1);
        break;
    case 3:
        atomic_inc(&precision_held);
        break;
    case 4:
        atomic_inc(&boost_held);
        break;
    default:
        return -EINVAL;
    }
    return ZMK_BEHAVIOR_OPAQUE;
}

static int speed_released(struct zmk_behavior_binding *binding,
                          struct zmk_behavior_binding_event event) {
    if (binding->param1 == 3 && atomic_get(&precision_held) > 0) {
        atomic_dec(&precision_held);
    } else if (binding->param1 == 4 && atomic_get(&boost_held) > 0) {
        atomic_dec(&boost_held);
    }
    return ZMK_BEHAVIOR_OPAQUE;
}

#if IS_ENABLED(CONFIG_ZMK_BEHAVIOR_METADATA)
static const struct behavior_parameter_value_metadata speed_values[] = {
    {.display_name = "Slow", .type = BEHAVIOR_PARAMETER_VALUE_TYPE_VALUE, .value = 0},
    {.display_name = "Normal", .type = BEHAVIOR_PARAMETER_VALUE_TYPE_VALUE, .value = 1},
    {.display_name = "Fast", .type = BEHAVIOR_PARAMETER_VALUE_TYPE_VALUE, .value = 2},
    {.display_name = "Hold precision", .type = BEHAVIOR_PARAMETER_VALUE_TYPE_VALUE, .value = 3},
    {.display_name = "Hold boost", .type = BEHAVIOR_PARAMETER_VALUE_TYPE_VALUE, .value = 4},
};
static const struct behavior_parameter_metadata_set speed_sets[] = {{
    .param1_values = speed_values, .param1_values_len = ARRAY_SIZE(speed_values),
}};
static const struct behavior_parameter_metadata speed_metadata = {
    .sets = speed_sets, .sets_len = ARRAY_SIZE(speed_sets),
};
#endif

static const struct behavior_driver_api speed_api = {
    .binding_pressed = speed_pressed,
    .binding_released = speed_released,
#if IS_ENABLED(CONFIG_ZMK_BEHAVIOR_METADATA)
    .parameter_metadata = &speed_metadata,
#endif
};

BEHAVIOR_DT_DEFINE(DT_NODELABEL(mouse_speed), NULL, NULL, NULL, NULL, POST_KERNEL,
                   CONFIG_KERNEL_INIT_PRIORITY_DEFAULT, &speed_api);

/* Fixed denominator 8 preserves fractional movement across speed changes.
 * Separate X/Y remainders keep very slow movement smooth and unbiased. */
static int32_t remainders[2];
static int scale_movement(const struct device *dev, struct input_event *event,
                          uint32_t param1, uint32_t param2,
                          struct zmk_input_processor_state *state) {
    if (event->type != INPUT_EV_REL ||
        (event->code != INPUT_REL_X && event->code != INPUT_REL_Y)) {
        return ZMK_INPUT_PROC_CONTINUE;
    }
    const zmk_mod_flags_t mods = zmk_hid_get_explicit_mods();
    int numerator = 4 << atomic_get(&selected_mode);
    if (atomic_get(&precision_held) || (mods & (MOD_LSFT | MOD_RSFT))) {
        numerator /= 4;
    } else if (atomic_get(&boost_held) || (mods & (MOD_LALT | MOD_RALT))) {
        numerator *= 2;
    }
    const int axis = event->code == INPUT_REL_X ? 0 : 1;
    const int32_t scaled = event->value * numerator + remainders[axis];
    event->value = scaled / 8;
    remainders[axis] = scaled - event->value * 8;
    return ZMK_INPUT_PROC_CONTINUE;
}

static const struct zmk_input_processor_driver_api scaler_api = {
    .handle_event = scale_movement,
};
DEVICE_DT_DEFINE(DT_NODELABEL(mouse_speed_scaler), NULL, NULL, NULL, NULL, POST_KERNEL,
                  CONFIG_KERNEL_INIT_PRIORITY_DEFAULT, &scaler_api);
