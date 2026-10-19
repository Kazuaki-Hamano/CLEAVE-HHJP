"""Run the production DYA event/cache adapter with a fake registry, using WSL gcc.

This tests our event application and per-role generations, not the upstream
registry's range/persistence implementation (those require firmware/UI checks).
"""
from pathlib import Path
import re
import subprocess

source = Path("src/trackpad_settings.c").read_text(encoding="utf-8")
source = re.sub(r'^#include .*$', '', source, flags=re.M)
stub = r"""
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include "trackpad_settings.h"
#define SETTINGS_MAX_NAME_LEN 64
#define BUILD_ASSERT(cond,msg) _Static_assert(cond,msg)
#define ARG_UNUSED(x) ((void)(x))
#define ARRAY_SIZE(x) (sizeof(x)/sizeof((x)[0]))
#define ZMK_EV_EVENT_BUBBLE 0
#define ZMK_LISTENER(...)
#define ZMK_SUBSCRIPTION(...)
#define ZMK_RPC_CUSTOM_SUBSYSTEM(...)
#define ZMK_RPC_CUSTOM_SUBSYSTEM_UI_URLS() .unused=0
#define ZMK_STUDIO_RPC_HANDLER_UNSECURED 0
#define ZMK_CUSTOM_SETTING_VALUE_TYPE_INT32 2
struct zmk_custom_setting_value {int type; int32_t int32_value;};
struct zmk_custom_setting {struct zmk_custom_setting_value value;};
#define ZMK_CUSTOM_SETTING_VALUE_INT32(v) ((struct zmk_custom_setting_value){.type=2,.int32_value=(v)})
#define ZMK_CUSTOM_SETTING_DEFINE(sym,ns,key,type,def,c,r,w,bounds) struct zmk_custom_setting sym={.value=def}
struct zmk_rpc_custom_subsystem_meta {int unused,security;};
typedef struct {int unused;} zmk_custom_CallRequest;
typedef struct {int unused;} pb_callback_t;
#define ZMK_CUSTOM_SETTING_WRITE_MODE_PERSIST 1
typedef int (*settings_read_cb)(void *, void *, size_t);
struct record {const char *path; int32_t value; bool present;};
static struct record records[6];
static bool fail_persist;
static int stored_read(void *arg,void *out,size_t len) {memcpy(out,arg,len);return len;}
static int settings_load_subtree_direct(const char *path,
 int (*cb)(const char *,size_t,settings_read_cb,void *,void *),void *param) {
 for(int i=0;i<6;i++)if(records[i].present && strcmp(records[i].path,path)==0)
  cb("",4,stored_read,&records[i].value,param);
 return 0;
}
static int settings_delete(const char *path) {
 for(int i=0;i<6;i++)if(records[i].path && strcmp(records[i].path,path)==0)records[i].present=false;
 return 0;
}
static int zmk_custom_setting_set_int32(const struct zmk_custom_setting *setting,int32_t v,int mode) {
 if(fail_persist)return -1;
 ((struct zmk_custom_setting *)setting)->value.int32_value=v;
 return 0;
}
struct k_spinlock {int unused;};
typedef int k_spinlock_key_t;
static int k_spin_lock(struct k_spinlock *p) {return 0;}
static void k_spin_unlock(struct k_spinlock *p,int k) {}
struct zmk_custom_setting_changed {const struct zmk_custom_setting *setting;};
typedef struct {int kind; struct zmk_custom_setting_changed changed;} zmk_event_t;
static const void *as_zmk_custom_settings_initialized(const zmk_event_t *e) {return e->kind==1?e:NULL;}
static const struct zmk_custom_setting_changed *as_zmk_custom_setting_changed(const zmk_event_t *e) {return e->kind==2?&e->changed:NULL;}
static const struct zmk_custom_setting *failed_read;
static int zmk_custom_setting_read(const struct zmk_custom_setting *s,struct zmk_custom_setting_value *v) {
 if(s==failed_read)return -1; *v=s->value;return 0;
}
"""
test = r"""
static void notify(struct zmk_custom_setting *s,int value) {
 s->value.int32_value=value;
 zmk_event_t e={.kind=2,.changed={.setting=s}};
 assert(settings_event(&e)==ZMK_EV_EVENT_BUBBLE);
}
int main(void) {
 struct cleave_trackpad_config c;uint32_t rg,lg;
 records[0]=(struct record){"custom_settings/cleave_right_trackpad/right_speed_percent",150,true};
 records[1]=(struct record){"custom_settings/cleave_right_trackpad/speed_percent",250,true};
 right_speed.value.int32_value=250; /* New registry record already loaded. */
 migrate_trackpad_keys();assert(right_speed.value.int32_value==250 && !records[0].present);
 records[0].present=true;records[1].present=false;fail_persist=true;
 migrate_trackpad_keys();assert(records[0].present && right_speed.value.int32_value==250);
 fail_persist=false;migrate_trackpad_keys();assert(!records[0].present && right_speed.value.int32_value==150);
 right_speed.value.int32_value=200;migrate_trackpad_keys();assert(right_speed.value.int32_value==200);
 records[2]=(struct record){"custom_settings/cleave_right_trackpad/right_max_gain_percent",500,true};
 records[3]=(struct record){"custom_settings/cleave_left_scroll/left_scroll_percent",70,true};
 migrate_trackpad_keys();assert(right_maximum.value.int32_value==500 && left_scroll.value.int32_value==70);
 assert(!records[2].present && !records[3].present);
 right_maximum.value.int32_value=300;left_scroll.value.int32_value=100;
 cleave_trackpad_get(&c,&rg);assert(c.speed==200 && c.scroll==100 && rg==1);
 right_speed.value.int32_value=500;left_scroll.value.int32_value=170;
 zmk_event_t init={.kind=1};settings_event(&init);
 cleave_trackpad_get(&c,&rg);cleave_trackpad_get_scroll(&c,&lg);
 assert(c.speed==500 && c.scroll==170 && rg==2 && lg==2);
 notify(&right_acceleration,50);
 cleave_trackpad_get(&c,&rg);cleave_trackpad_get_scroll(&c,&lg);
 assert(c.acceleration==50 && rg==3 && lg==2);
 notify(&left_scroll,180);
 cleave_trackpad_get(&c,&rg);cleave_trackpad_get_scroll(&c,&lg);
 assert(c.scroll==180 && c.speed==500 && rg==3 && lg==3);
 notify(&left_scroll,180); /* Save notification with unchanged effective value. */
 cleave_trackpad_get_scroll(&c,&lg);assert(lg==3);
 failed_read=&right_speed;notify(&right_speed,600);
 cleave_trackpad_get(&c,&rg);assert(c.speed==500 && rg==3);
 failed_read=NULL;notify(&right_speed,200); /* Discard/reset reapplies the effective value. */
 cleave_trackpad_get(&c,&rg);cleave_trackpad_get_scroll(&c,&lg);
 assert(c.speed==200 && c.scroll==180 && rg==4 && lg==3);
 struct zmk_custom_setting unrelated={0};notify(&unrelated,123);
 cleave_trackpad_get(&c,&rg);assert(c.speed==200 && rg==4);
 puts("DYA adapter: key migration, new-value precedence, retry/reset safety, loaded values, updates/discard, failed reads, unrelated events and independent generations: PASS");
}
"""
subprocess.run(["wsl", "--", "bash", "-lc", "gcc -std=c11 -Wall -Wextra -Werror -Wno-unused-parameter -Wno-unused-function -Wno-unused-variable -Wno-misleading-indentation -I src -x c -o /tmp/cleave-trackpad-registry - && /tmp/cleave-trackpad-registry"], input=(stub + source + test).encode(), check=True)
