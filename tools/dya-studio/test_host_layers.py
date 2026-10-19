"""Exercise production host-layer apply logic with stable IDs and a held Fn."""
from pathlib import Path
import subprocess

source = Path("modules/default-layer/src/default_layer.c").read_text()
start = source.index("static zmk_keymap_layer_id_t managed_layer")
end = source.index("static int32_t resolve_value", start)
stub = r"""
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
typedef uint8_t zmk_keymap_layer_id_t;
#define ZMK_KEYMAP_LAYER_ID_INVAL 255
#define ZMK_KEYMAP_LAYERS_LEN 4
#define ZMK_DEFAULT_LAYER_UNSET -1
#define ZMK_DEFAULT_LAYER_OS_DETECTION -2
#define LOG_WRN(...)
struct zmk_endpoint_instance {int unused;};
static uint8_t order[] = {0, 2, 3, 1};
static unsigned state = 3, locks;
static int activation_error;
static uint8_t zmk_keymap_layer_default(void) {return 0;}
static uint8_t zmk_keymap_layer_index_to_id(int index) {
 return index >= 0 && index < 4 ? order[index] : 255;
}
static int zmk_keymap_layer_activate(uint8_t id, bool locking) {
 if (activation_error) return -1;
 state |= 1u << id; if(locking) locks |= 1u << id; return 0;
}
static int zmk_keymap_layer_deactivate(uint8_t id, bool locking) {
 state &= ~(1u << id); if(locking) locks &= ~(1u << id); return 0;
}
"""
validation = source[source.index("static bool is_valid_layer_value"):source.index("static void resolve_and_apply")]
test = r"""
static void select_layer(int index) {
 apply_layer((struct zmk_endpoint_instance){0}, 1, index, index, "test");
}
int main(void) {
 assert(is_valid_layer_value(-1, false));
 assert(is_valid_layer_value(-2, true));
 assert(!is_valid_layer_value(-2, false));
 assert(!is_valid_layer_value(4, true));
 order[3] = 255; assert(!is_valid_layer_value(3, true)); order[3] = 1;
 select_layer(0); assert(state == 3); /* Initial unset/default preserves held Fn. */
 select_layer(1); assert(state == 7 && locks == 4); /* Index 1 is stable ID 2. */
 select_layer(1); assert(state == 7); /* Repeated OS/settings notification. */
 select_layer(2); assert(state == 11 && locks == 8); /* Release former host only. */
 order[1] = 3; order[2] = 2;
 select_layer(2); assert(state == 7 && locks == 4); /* Reorder uses stable old ID. */
 select_layer(0); assert(state == 3 && locks == 0); /* Return to default. */
 activation_error = 1; select_layer(1); assert(state == 3);
 activation_error = 0; select_layer(1); assert(state == 11);
 select_layer(99); assert(state == 3); /* Deleted/invalid target falls back. */
 puts("Host layer transitions / held Fn / reorder / error fallback: PASS");
}
"""
subprocess.run(
    ["wsl", "--", "bash", "-lc",
     "gcc -std=c11 -Wall -Wextra -Werror -Wno-unused-parameter -x c -o /tmp/cleave-host-layers - && /tmp/cleave-host-layers"],
    input=(stub + validation + source[start:end] + test).encode(), check=True,
)
