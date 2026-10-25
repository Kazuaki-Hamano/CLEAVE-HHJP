"""Exercise brightness settings through pinned production relay macros for both roles."""
from pathlib import Path
import re,subprocess
transport=Path("tools/dya-studio/fixtures/split_bluetooth_service.upstream.c").read_text()
receive_callback=re.search(r"static void split_svc_relay_event_from_central_callback\(struct k_work \*work\) \{.*?^\}", transport, re.S|re.M).group()
upstream=Path("tools/dya-studio/fixtures/event_manager.upstream.h").read_text()
def macro(name, start=0):
    pos=upstream.index("#define " + name + "(", start)
    lines=upstream[pos:].splitlines()
    out=[]
    for line in lines:
        out.append(line)
        if not line.endswith("\\"):break
    return "\n".join(out)+"\n"
relay=macro("__ZMK_RELAY_ASSERT_NAME")+macro("__ZMK_RELAY_ASSERT_SIZE")+macro("ZMK_RELAY_EVENT_HANDLE")
relay+="#if CONFIG_ZMK_SPLIT_ROLE_CENTRAL\n"+macro("ZMK_RELAY_EVENT_CENTRAL_TO_PERIPHERAL")+"\n#define ZMK_RELAY_EVENT_PERIPHERAL_TO_CENTRAL(...)\n#else\n#define ZMK_RELAY_EVENT_CENTRAL_TO_PERIPHERAL(...)\n"+macro("ZMK_RELAY_EVENT_PERIPHERAL_TO_CENTRAL",upstream.index("#else // peripheral"))+"\n#endif\n"
source=re.sub(r"^#include.*$", "", Path("src/status_led/brightness.c").read_text(), flags=re.M)
stub=r"""
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#define IS_ENABLED(x) (x)
#define LOG_MODULE_DECLARE(...)
#define LOG_WRN(...)
#define CONFIG_ZMK_SPLIT_RELAY_EVENT_TYPE_NAME_LEN 4
#define CONFIG_ZMK_SPLIT_RELAY_EVENT_DATA_LEN 240
#define STRINGIFY(x) #x
#define IS_EMPTY(x) 0
#define UNPAREN(...) __VA_ARGS__
#define COND_CODE_1(flag,a,b) UNPAREN b
#define ARG_UNUSED(x) (void)(x)
#define ZMK_EVENT_DECLARE(n) static struct n *as_##n(const void *); static int raise_##n(struct n)
#define ZMK_EVENT_IMPL(...)
struct listener {int (*callback)(const void *);};
struct subscription {const char *type;const struct listener *listener;};
#define ZMK_LISTENER(mod,cb) static const struct listener listener_##mod={cb}
#define ZMK_SUBSCRIPTION(mod,event) static const struct subscription subscription_##mod##_##event={#event,&listener_##mod}
#define ZMK_RPC_CUSTOM_SUBSYSTEM(...)
#define ZMK_RPC_CUSTOM_SUBSYSTEM_UI_URLS() .ui=0
#define ZMK_STUDIO_RPC_HANDLER_UNSECURED 0
#define ZMK_CUSTOM_SETTING_DEFINE(n,...) static const struct zmk_custom_setting n={0}
#define BUILD_ASSERT(c,...) _Static_assert(c,"build assertion")
#define SETTINGS_MAX_NAME_LEN 64
#define SETTINGS_STATIC_HANDLER_DEFINE(...)
#define ZMK_EV_EVENT_BUBBLE 0
#define ZMK_EV_EVENT_HANDLED 1
#define ZMK_RELAY_EVENT_SOURCE_SELF 255
#define K_FOREVER 0
#define K_MSEC(n) (n)
#define K_MUTEX_DEFINE(n) static int n
#define K_WORK_DELAYABLE_DEFINE(n,fn) static int n
struct k_work {int unused;};
static int cleave_peer_work_q,scheduled,canceled,last_delay;
static void k_mutex_lock(int *p,int t) {assert(!*p);*p=1;}
static void k_mutex_unlock(int *p) {assert(*p);*p=0;}
static int k_work_reschedule_for_queue(int *q,int *w,int t){scheduled++;last_delay=t;return 0;}
static int k_work_cancel_delayable(int *w){canceled++;return 0;}
typedef int atomic_t;
static int atomic_get(atomic_t *p){return *p;}
static void atomic_set(atomic_t *p,int v){*p=v;}
static int refreshes,reads,writes,flash_error;static bool connected=true;
static int32_t disk;
static void cleave_led_refresh(void){refreshes++;}
static bool cleave_split_peripheral_connected(void){return connected;}
static bool zmk_split_bt_peripheral_is_connected(void){return connected;}
typedef int (*settings_read_cb)(void *,void *,size_t);
static int settings_save_one(const char *key,const void *p,size_t len){assert(!strcmp(key,"cleave_led/saved"));assert(len==4);writes++;if(flash_error)return -EIO;memcpy(&disk,p,4);return 0;}
struct zmk_split_relay_event_payload {struct {unsigned event_data_size,event_type_size;} header;char event_type[4];uint8_t event_data[240];};
#define ZMK_SPLIT_TRANSPORT_PERIPHERAL_EVENT_TYPE_RELAY_EVENT 1
struct zmk_split_transport_peripheral_event {int type;union {struct zmk_split_relay_event_payload relay_event;} data;};
struct zmk_relay_event_received {uint8_t source;const char *event_name;const uint8_t *event_data;size_t event_data_size;};
static bool incoming_relay;
static struct zmk_relay_event_received *as_zmk_relay_event_received(const void *e){return incoming_relay?(void*)e:NULL;}
static int zmk_split_central_send_relay_event(struct zmk_split_relay_event_payload *p);
static int zmk_split_peripheral_report_event(struct zmk_split_transport_peripheral_event *p);
typedef void zmk_event_t;typedef int zmk_custom_CallRequest;typedef int pb_callback_t;
struct zmk_rpc_custom_subsystem_meta{int ui,security;};
struct zmk_custom_setting{int unused;};
struct zmk_custom_setting_value{int type;int32_t int32_value;};
enum {ZMK_CUSTOM_SETTING_VALUE_TYPE_INT32=2};
enum {ZMK_CUSTOM_SETTING_CHANGED_VALUE_UPDATED,ZMK_CUSTOM_SETTING_CHANGED_SAVED,ZMK_CUSTOM_SETTING_CHANGED_DISCARDED,ZMK_CUSTOM_SETTING_CHANGED_RESET};
struct zmk_custom_setting_changed{const struct zmk_custom_setting *setting;int kind;};
static int event_kind;static int32_t registry_value=100;
static const struct zmk_custom_setting_changed *as_zmk_custom_setting_changed(const void *e){return event_kind==2?e:NULL;}
static const void *as_zmk_custom_settings_initialized(const void *e){return event_kind==1?e:NULL;}
static int zmk_custom_setting_read(const struct zmk_custom_setting *s,struct zmk_custom_setting_value *v){reads++;v->type=2;v->int32_value=registry_value;return 0;}
"""
test=r"""
static struct zmk_led_config sent;static int sends;
static struct zmk_led_config *as_zmk_led_config(const void *e){return incoming_relay?NULL:(void*)e;}
static int record_wire(struct zmk_split_relay_event_payload *p){
 assert(!strcmp(p->event_type,"lc"));assert(p->header.event_data_size==sizeof(sent));
 memcpy(&sent,p->event_data,sizeof(sent));sends++;return 0;
}
static int zmk_split_central_send_relay_event(struct zmk_split_relay_event_payload *p){return record_wire(p);}
static int zmk_split_peripheral_report_event(struct zmk_split_transport_peripheral_event *p){return record_wire(&p->data.relay_event);}
static int raise_zmk_led_config(struct zmk_led_config e){
 bool previous=incoming_relay;incoming_relay=false;
 /* Dispatch through the actual generated sender subscription, not a fake send. */
 assert(!strcmp(subscription_zmk_led_config_relay_zmk_led_config.type,"zmk_led_config"));
 subscription_zmk_led_config_relay_zmk_led_config.listener->callback(&e);
 led_config_event(&e);incoming_relay=previous;return 0;
}
static struct zmk_split_relay_event_payload relay_event_from_central_msgq;
static bool queued;
static int k_msgq_get(struct zmk_split_relay_event_payload *q,void *p,int timeout){
 if(!queued)return -EAGAIN;
 memcpy(p,q,sizeof(*q));queued=false;return 0;
}
#define K_NO_WAIT 0
static int raise_zmk_relay_event_received(struct zmk_relay_event_received wire){
 incoming_relay=true;int before=sends;
 subscription_zmk_led_config_relay_handle_zmk_relay_event_received.listener->callback(&wire);
 incoming_relay=false;assert(sends==before);return 0;
}
__RECEIVE_CALLBACK__
static void receive(int kind,int seq,int live,int saved){
 struct zmk_led_config e={seq,live,saved,kind,255};
#if CONFIG_ZMK_SPLIT_ROLE_CENTRAL
 /* First peripheral slot is raw source 0 in app/src/split/central.c. */
 raise_zmk_relay_event_received((struct zmk_relay_event_received){0,"lc",(const void*)&e,sizeof(e)});
#else
 /* Execute the pinned BLE receiver, including its real raw source value. */
 relay_event_from_central_msgq.header.event_data_size=sizeof(e);
 strcpy(relay_event_from_central_msgq.event_type,"lc");
 memcpy(relay_event_from_central_msgq.event_data,&e,sizeof(e));queued=true;
 split_svc_relay_event_from_central_callback(NULL);assert(!queued);
#endif
}
#if CONFIG_ZMK_SPLIT_ROLE_CENTRAL
static void edit(int value,int kind){event_kind=2;registry_value=value;struct zmk_custom_setting_changed e={&awake_brightness,kind};led_registry_event(&e);}
int main(void){
 registry_value=40;event_kind=1;led_registry_event((void*)1);assert(cleave_led_brightness_get()==40 && state.saved==40);
 led_sync_work(NULL);assert(sent.kind==LED_UPDATE && sent.saved==40 && sent.live==40);
 receive(LED_ACK,sent.sequence,sent.live,sent.saved);assert(!pending);
 edit(10,ZMK_CUSTOM_SETTING_CHANGED_VALUE_UPDATED);assert(state.live==10 && state.saved==40);
 led_sync_work(NULL);assert(sent.live==10 && sent.saved==40 && writes==0);
 unsigned old=sent.sequence;edit(20,ZMK_CUSTOM_SETTING_CHANGED_VALUE_UPDATED);
 receive(LED_ACK,old,10,40);assert(pending); /* stale ACK cannot drop a newer edit */
 edit(20,ZMK_CUSTOM_SETTING_CHANGED_SAVED);assert(state.saved==20);
 connected=false;int count=sends;led_sync_work(NULL);assert(sends==count && pending && last_delay==5000);
 connected=true;led_sync_work(NULL);receive(LED_ACK,sent.sequence,sent.live,sent.saved);assert(!pending);
 receive(LED_REQUEST,0,0,0);assert(pending);led_sync_work(NULL);assert(sent.saved==20);
 edit(100,ZMK_CUSTOM_SETTING_CHANGED_RESET);assert(state.saved==100 && state.live==100);
 edit(0,ZMK_CUSTOM_SETTING_CHANGED_VALUE_UPDATED);assert(cleave_led_brightness_get()==0 && state.saved==100);
 edit(100,ZMK_CUSTOM_SETTING_CHANGED_DISCARDED);assert(cleave_led_brightness_get()==100);
 edit(101,ZMK_CUSTOM_SETTING_CHANGED_VALUE_UPDATED);assert(state.live==100);
 puts("LED central: load, preview/save/discard/reset, stale ACK, disconnect/retry/reconnect and range: PASS");
}
#else
static int load_cb(void *arg,void *p,size_t len){memcpy(p,&disk,len);return len;}
int main(void){
 disk=40;assert(led_load("saved",4,load_cb,NULL)==0);led_peripheral_init(NULL);assert(cleave_led_brightness_get()==40);
 led_sync_work(NULL);assert(sent.kind==LED_REQUEST);
 receive(LED_UPDATE,1,10,40);led_sync_work(NULL);assert(cleave_led_brightness_get()==10 && writes==0 && !pending && sent.kind==LED_ACK);
 receive(LED_UPDATE,2,20,20);flash_error=1;led_sync_work(NULL);assert(pending && cleave_led_brightness_get()==20 && stored_brightness==40);
 flash_error=0;led_sync_work(NULL);assert(!pending && stored_brightness==20 && disk==20 && sent.sequence==2);
 int count=writes;receive(LED_UPDATE,2,20,20);led_sync_work(NULL);assert(writes==count); /* idempotent retry */
 receive(LED_UPDATE,3,101,30);assert(!pending && cleave_led_brightness_get()==20);
 led_connection_event(NULL);led_sync_work(NULL);assert(sent.kind==LED_REQUEST);
 /* Reboot restores saved value, not a live preview. */
 receive(LED_UPDATE,4,0,20);led_sync_work(NULL);assert(cleave_led_brightness_get()==0 && disk==20);
 stored_brightness=100;assert(led_load("saved",4,load_cb,NULL)==0);led_peripheral_init(NULL);assert(cleave_led_brightness_get()==20);
 disk=101;assert(led_load("saved",4,load_cb,NULL)==-EINVAL);
 puts("LED right: saved boot value, preview without flash, save failures/retry, reconnect, zero and validation: PASS");
}
#endif
"""
test=test.replace("__RECEIVE_CALLBACK__",receive_callback)
for role in (0,1):
 subprocess.run(["wsl","--","bash","-lc",f"gcc -DCONFIG_ZMK_SPLIT_ROLE_CENTRAL={role} -std=c11 -Wall -Wextra -Werror -Wno-unused-function -Wno-unused-variable -Wno-unused-parameter -x c -o /tmp/cleave-led-settings - && /tmp/cleave-led-settings"],input=(stub+relay+source+test).encode(),check=True)
