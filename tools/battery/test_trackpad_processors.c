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

static bool fn;
static unsigned navigation_count;
static bool last_forward;
bool zmk_keymap_layer_active(unsigned layer) { assert(layer==1); return fn; }
void cleave_trackpad_navigate(bool forward) { navigation_count++; last_forward=forward; }
static void local_packet(int x, int y, int *horizontal, int *vertical) {
    struct input_event e={.type=INPUT_EV_REL,.code=INPUT_REL_X,.value=x};
    local_control_api.handle_event(NULL,&e,0,0,NULL);
    assert(fn ? e.value==0 : e.code==INPUT_REL_HWHEEL);
    *horizontal=e.value;
    e=(struct input_event){.type=INPUT_EV_REL,.code=INPUT_REL_Y,.value=y,.sync=true};
    local_control_api.handle_event(NULL,&e,0,0,NULL);
    assert(fn ? e.value==0 : e.code==INPUT_REL_WHEEL);
    *vertical=e.value;
    now+=10;
}
int main(void) {
    struct device right={&remote_pointer};
    assert(move(&right,1)==0 && move(&right,1)==0 && move(&right,1)==0);
    int h,v;
    local_packet(8,-8,&h,&v);assert(h==0 && v==0);
    assert(move(&right,1)==1); /* Local scrolling does not affect pointer fractions. */
    local_packet(8,-8,&h,&v);assert(h==1 && v==1);
    right.data=&remote_scroll;
    assert(scroll(&right)==0 && scroll(&right)==1);
    fn=true;
    right.data=&remote_pointer;
    assert(move(&right,10)==3); /* Fn must not suppress right cursor movement. */
    struct input_event button={.type=INPUT_EV_KEY,.code=1,.value=1,.sync=true};
    pointer_api.handle_event(&right,&button,0,0,NULL);
    assert(button.type==INPUT_EV_KEY && button.code==1 && button.value==1);
    local_packet(20,0,&h,&v);assert(navigation_count==0);
    local_packet(44,0,&h,&v);assert(navigation_count==1 && last_forward);
    for (int i=0;i<10;i++) local_packet(100,0,&h,&v);
    assert(navigation_count==1);
    now+=180;
    local_packet(-64,0,&h,&v);assert(navigation_count==2 && !last_forward);
    now+=180;
    local_packet(64,64,&h,&v);assert(navigation_count==2); /* Diagonal is not a swipe. */
    fn=false;local_packet(0,0,&h,&v);
    fn=true;local_packet(0,100,&h,&v);assert(navigation_count==2);
    now+=180;local_packet(32,0,&h,&v);
    fn=false;local_packet(0,0,&h,&v);
    fn=true;local_packet(32,0,&h,&v);assert(navigation_count==2); /* No Fn carry-over. */
    local_packet(32,0,&h,&v);assert(navigation_count==3 && last_forward);
    fn=false;
    local_packet(-16,16,&h,&v);assert(h==-1 && v==-1);
    fn=true;local_packet(32,0,&h,&v);
    cleave_trackpad_reset_local(); /* Fn released/repressed without intervening pad events. */
    local_packet(32,0,&h,&v);assert(navigation_count==3);
    puts("Local 2D scroll, Fn swipe direction/threshold/latch/rearm, right isolation: PASS");
}
