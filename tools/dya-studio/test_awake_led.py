"""Compile the production LED state/renderer with deterministic GPIO/queue mocks."""
from pathlib import Path
import subprocess
import re

source = Path("src/status_led/widget.c").read_text()
def function(name):
    start = re.search(r"\b" + re.escape(name), source).start()
    start = source.rfind("\n", 0, start) + 1
    brace = source.index("{", start)
    depth = 1
    end = brace + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[start:end]

stub = r"""
#include <assert.h>
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <stdio.h>
#define IS_ENABLED(x) (x)
#define CONFIG_ZMK_BATTERY_REPORTING 1
#define CONFIG_RGBLED_WIDGET_BATTERY_LEVEL_HIGH 80
#define CONFIG_RGBLED_WIDGET_BATTERY_LEVEL_LOW 20
#define CONFIG_RGBLED_WIDGET_BATTERY_LEVEL_CRITICAL 5
#define CONFIG_RGBLED_WIDGET_BATTERY_COLOR_HIGH 2
#define CONFIG_RGBLED_WIDGET_BATTERY_COLOR_MEDIUM 3
#define CONFIG_RGBLED_WIDGET_BATTERY_COLOR_LOW 1
#define CONFIG_RGBLED_WIDGET_BATTERY_COLOR_CRITICAL 1
#define CONFIG_RGBLED_WIDGET_BATTERY_COLOR_MISSING 5
#define CONFIG_RGBLED_WIDGET_BATTERY_BLINK_MS 2000
#define CONFIG_RGBLED_WIDGET_INTERVAL_MS 500
#define CONFIG_RGBLED_WIDGET_SHOW_LAYER_COLORS 0
#define CONFIG_ZMK_SPLIT 1
#define SHOW_LAYER_COLORS (IS_ENABLED(CONFIG_RGBLED_WIDGET_SHOW_LAYER_COLORS)) && (!IS_ENABLED(CONFIG_ZMK_SPLIT) || IS_ENABLED(CONFIG_ZMK_SPLIT_ROLE_CENTRAL))
#define LOG_WRN(...)
#define LOG_INF(...)
#define LOG_BATTERY(...)
#define BUILD_ASSERT(c,...) _Static_assert(c, "build assertion")
#define K_MUTEX_DEFINE(n) static int n
#define K_FOREVER -1
#define K_NO_WAIT 0
#define K_MSEC(n) (n)
#define BIT(n) (1u << (n))
#define ZMK_LISTENER(...)
#define ZMK_SUBSCRIPTION(...)
typedef int atomic_t;
static int atomic_get(atomic_t *p) {return *p;}
static void atomic_set(atomic_t *p, int v) {*p=v;}
static void k_mutex_lock(int *p,int timeout) {assert(!*p);*p=1;}
static void k_mutex_unlock(int *p) {assert(*p);*p=0;}
static int gpio_color;
static uint8_t levels[3], configured_brightness=100;
static uint8_t cleave_led_brightness_get(void) {return configured_brightness;}
static const void *led_dev;
static const uint8_t rgb_idx[]={0,1,2};
static int led_set_brightness(const void *dev,int index,uint8_t level) {
 levels[index]=level;if(level)gpio_color |= BIT(index);else gpio_color &= ~BIT(index);return 0;
}
static void (*sleep_hook)(void);
static void k_sleep(int ms) {if(sleep_hook){void (*f)(void)=sleep_hook;sleep_hook=NULL;f();}}
static uint8_t battery=90;
static uint8_t zmk_battery_state_of_charge(void) {return battery;}
enum {ZMK_ACTIVITY_ACTIVE,ZMK_ACTIVITY_IDLE,ZMK_ACTIVITY_SLEEP};
struct zmk_activity_state_changed {int state;};
struct zmk_battery_state_changed {int state_of_charge;};
typedef void zmk_event_t;
static const struct zmk_activity_state_changed *as_zmk_activity_state_changed(const void *e) {return e;}
static const struct zmk_battery_state_changed *as_zmk_battery_state_changed(const void *e) {return e;}
#define K_MSGQ_DEFINE(n,size,count,align) static struct {unsigned char items[count][size];int used;} n
#define k_msgq_put(q,p,timeout) mock_put((q)->items,&(q)->used,sizeof(*(p)),p)
static int mock_put(void *items,int *used,int size,const void *p) {
 if(*used==16)return -1;memcpy((char*)items+(*used)++*size,p,size);return 0;
}
"""
state = source[source.index("struct blink_item {"):source.index("static void indicate_connectivity_internal")]
production = state + "\n" + function("get_battery_color(") + "\n" + function("led_battery_listener_cb(") + "\n" + function("resting_color(void) {") + "\n" + function("process_blink(")
test = r"""
static void drain(void) {
 while(led_msgq.used) {
  struct blink_item b;memcpy(&b,led_msgq.items[0],sizeof(b));
  memmove(led_msgq.items[0],led_msgq.items[1],--led_msgq.used*sizeof(b));
  process_blink(b);assert(gpio_color==(led_current_brightness ? led_current_color : 0));
 }
}
static void activity(int state) {struct zmk_activity_state_changed e={state};led_activity_listener_cb(&e);}
static void change_battery(int level) {
 battery=level;struct zmk_battery_state_changed e={level};led_battery_listener_cb(&e);
}
static void check_notification_full_brightness(void) {assert(levels[2]==100);}
static void sleep_during_blink(void) {activity(ZMK_ACTIVITY_SLEEP);assert(gpio_color==0);}
int main(void) {
 /* Startup notifications work; steady illumination waits for initialization. */
 configured_brightness=0;sleep_hook=check_notification_full_brightness;
 assert(resting_color()==0);process_blink((struct blink_item){.color=4,.duration_ms=100});assert(gpio_color==0);
 configured_brightness=100;initialized=true;cleave_led_refresh();drain();assert(gpio_color==2);
 configured_brightness=10;cleave_led_refresh();drain();assert(levels[1]==10);
 configured_brightness=0;cleave_led_refresh();drain();assert(gpio_color==0);
 configured_brightness=100;cleave_led_refresh();drain();assert(levels[1]==100);
 activity(ZMK_ACTIVITY_IDLE);drain();assert(gpio_color==2);
 activity(ZMK_ACTIVITY_ACTIVE);drain();assert(gpio_color==2);
 change_battery(80);drain();assert(gpio_color==2);
 change_battery(79);drain();assert(gpio_color==3);
 change_battery(20);drain();assert(gpio_color==3);
 change_battery(19);drain();assert(gpio_color==1);
 change_battery(5);drain();assert(gpio_color==1);
 change_battery(0);drain();assert(gpio_color==5); /* upstream unknown/zero convention */
 change_battery(90);drain();assert(gpio_color==2);
 configured_brightness=10;cleave_led_refresh();drain();assert(levels[1]==10);
 sleep_hook=check_notification_full_brightness;
 process_blink((struct blink_item){.color=4,.duration_ms=100});assert(gpio_color==2);assert(levels[1]==10);
 sleep_hook=sleep_during_blink;
 process_blink((struct blink_item){.color=3,.duration_ms=100});assert(gpio_color==0);
 change_battery(30);drain();assert(gpio_color==0);
 process_blink((struct blink_item){.color=4,.duration_ms=100});assert(gpio_color==0);
 activity(ZMK_ACTIVITY_ACTIVE);drain();assert(gpio_color==3);
 /* A saturated notification queue cannot lose the new resting state. */
 for(int i=0;i<16;i++){struct blink_item b={.color=4,.duration_ms=100};k_msgq_put(&led_msgq,&b,0);}
 change_battery(90);assert(led_msgq.used==16);drain();assert(gpio_color==2);
 activity(ZMK_ACTIVITY_SLEEP);assert(gpio_color==0);activity(ZMK_ACTIVITY_IDLE);drain();assert(gpio_color==2);
 puts("Awake/idle color, thresholds, battery updates, blink restore, sleep races, wake and full queue: PASS");
}
"""
for central in (0, 1):
    subprocess.run(["wsl", "--", "bash", "-lc", f"gcc -DCONFIG_ZMK_SPLIT_ROLE_CENTRAL={central} -std=c11 -Wall -Wextra -Werror -Wno-unused-parameter -Wno-unused-variable -Wno-misleading-indentation -x c -o /tmp/cleave-awake-led - && /tmp/cleave-awake-led"], input=(stub+production+test).encode(), check=True)
