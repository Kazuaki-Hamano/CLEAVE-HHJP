"""Exercise the actual sensitivity poll with and without deep sleep enabled."""
from pathlib import Path
import subprocess

source = Path("src/trackpad_settings.c").read_text(encoding="utf-8")
start = source.index("static void poll(struct k_work *work) {")
end = source.index("static int trackpad_init(void)", start)
poll = source[start:end]
stub = r"""
#include <assert.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include "charge_status.h"
#define IS_ENABLED(x) (x)
#define ARG_UNUSED(x) ((void)(x))
#define DEVICE_DT_NAME(x) "tp_sens"
#define DT_NODELABEL(x) 0
#define K_SECONDS(x) (x)
struct k_work {int unused;};
struct cleave_trackpad_config {int sensitivity;};
struct zmk_behavior_binding {const char *behavior_dev; int param1;};
struct zmk_behavior_binding_event {int source,position; int64_t timestamp;};
static struct k_work poll_work;
static int power_state,sends,reschedules;
static int cfg_lock,transport_attempts,transport_submit_error,transport_stage;
static int64_t peer_updated;
uint8_t cleave_local_power_state(void) {return power_state;}
static void cleave_trackpad_get(struct cleave_trackpad_config *c,void *g) {c->sensitivity=1;}
static int64_t k_uptime_get(void) {return 10000;}
static int zmk_split_central_invoke_behavior(int side,struct zmk_behavior_binding *b,struct zmk_behavior_binding_event e,bool pressed) {
 assert(side==0 && b->param1==1 && pressed); sends++; return 0;
}
static void atomic_inc(int *p) {++*p;}
static void atomic_set(int *p,int v) {*p=v;}
typedef int k_spinlock_key_t;
static int k_spin_lock(int *p) {return 0;}
static void k_spin_unlock(int *p,int key) {}
static void k_work_reschedule(struct k_work *p,int seconds) {assert(p==&poll_work && seconds==1);reschedules++;}
"""
test = r"""
int main(void) {
 for(int i=0;i<4;i++) {
  power_state=i;sends=reschedules=0;transport_attempts=0;
  poll(&poll_work);
  int expected=!CONFIG_ZMK_SLEEP || i==CLEAVE_POWER_USB_IDLE || i==CLEAVE_POWER_CHARGING;
  assert(sends==expected && transport_attempts==expected && reschedules==1);
 }
 puts("Actual trackpad poll: battery/unknown suppression, USB/charging requests, reschedule: PASS");
}
"""
for enabled in (0, 1):
    code = "#define CONFIG_ZMK_SLEEP " + str(enabled) + "\n" + stub + poll + test
    subprocess.run(["wsl", "--", "bash", "-lc", "gcc -Wall -Wextra -Werror -Wno-unused-parameter -I src -x c -o /tmp/cleave-sleep-poll - && /tmp/cleave-sleep-poll"], input=code.encode(), check=True)
