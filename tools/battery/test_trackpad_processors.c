/* Exercise the firmware processors with interleaved input from two devices. */
#include <assert.h>
#include <stdio.h>
#include "../../src/trackpad_pointer.c"
static int64_t now = 1000;
static struct cleave_trackpad_config cfg = {30, 0, 300, 1, 100};
int64_t k_uptime_get(void) { return now; }
void cleave_trackpad_get(struct cleave_trackpad_config *out, uint32_t *generation) {
    *out = cfg;
    *generation = 1;
}
static int move(struct device *dev, int x) {
    struct input_event e = {.type=INPUT_EV_REL, .code=INPUT_REL_X, .value=x};
    pointer_api.handle_event(dev, &e, 0, 0, NULL);
    int result = e.value;
    e = (struct input_event){.type=INPUT_EV_REL, .code=INPUT_REL_Y, .sync=true};
    pointer_api.handle_event(dev, &e, 0, 0, NULL);
    now += 10;
    return result;
}
static int scroll(struct device *dev) {
    struct input_event e = {.type=INPUT_EV_REL, .code=INPUT_REL_Y, .value=-8, .sync=true};
    scroll_api.handle_event(dev, &e, 0, 0, NULL);
    assert(e.code == INPUT_REL_WHEEL);
    now += 10;
    return e.value;
}
int main(void) {
    struct device right={&remote_pointer}, left={&local_pointer};
    assert(move(&right,1)==0 && move(&right,1)==0 && move(&right,1)==0);
    assert(move(&left,1)==0); /* Must not inherit the right pad's 0.9 remainder. */
    assert(move(&right,1)==1);
    remote_pointer=(struct pointer_state){0};
    local_pointer=(struct pointer_state){0};
    cfg.speed=200; cfg.acceleration=100;
    move(&right,100); move(&right,100);
    assert(move(&left,1)==2); /* Must not inherit right's acceleration. */
    right.data=&remote_scroll; left.data=&local_scroll;
    assert(scroll(&right)==0 && scroll(&left)==0);
    assert(scroll(&right)==1 && scroll(&left)==1);
    puts("Independent left/right acceleration and fractional cursor/scroll state: PASS");
}
