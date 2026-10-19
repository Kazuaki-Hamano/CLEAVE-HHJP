"""Compile production split-status helper and actual GetSplitInfo handler with mocks."""
from pathlib import Path
import re
import subprocess
helper = Path("modules/ble-management/include/cleave_split_status.h").read_text()
helper = re.sub(r"^#(?:include|pragma).*$", "", helper, flags=re.M)
source = Path("modules/ble-management/src/studio/ble_management_handler.c").read_text()
start = source.index("static int handle_get_split_info_request(", source.index("Handle GetSplitInfoRequest"))
end = source.index("\n/**", start)
handler = source[start:end]
stub = r"""
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#define IS_ENABLED(x) (x)
#define LOG_DBG(...)
#define ZMK_SPLIT_TRANSPORT_CONNECTIONS_STATUS_DISCONNECTED 0
#define ZMK_SPLIT_TRANSPORT_CONNECTIONS_STATUS_SOME_CONNECTED 1
#define ZMK_SPLIT_TRANSPORT_CONNECTIONS_STATUS_ALL_CONNECTED 2
struct zmk_split_transport_status {bool available,enabled;int connections;};
struct api {struct zmk_split_transport_status (*get_status)(void);};
struct zmk_split_transport_central {const struct api *api;};
static struct zmk_split_transport_central transports[2];
#define STRUCT_SECTION_FOREACH(type,it) for(struct type *it=transports;it<transports+2;it++)
static struct zmk_split_transport_status state;
static int queries;
static struct zmk_split_transport_status get_status(void) {queries++;return state;}
static bool bonded;
static bool zmk_split_bt_peripheral_is_bonded(void) {return bonded;}
typedef struct {bool is_split,is_central,peripheral_connected,central_bonded;} zmk_ble_management_SplitInfo;
typedef struct {zmk_ble_management_SplitInfo info;} zmk_ble_management_GetSplitInfoResponse;
#define zmk_ble_management_GetSplitInfoResponse_init_zero {0}
typedef struct {int unused;} zmk_ble_management_GetSplitInfoRequest;
typedef struct {int which_response_type;struct {zmk_ble_management_GetSplitInfoResponse get_split_info;} response_type;} zmk_ble_management_Response;
#define zmk_ble_management_Response_get_split_info_tag 5
static zmk_ble_management_SplitInfo query(void);
"""
test = r"""
static zmk_ble_management_SplitInfo query(void) {
 zmk_ble_management_Response r={0};zmk_ble_management_GetSplitInfoRequest q={0};
 assert(handle_get_split_info_request(&q,&r)==0);
 assert(r.which_response_type==5);return r.response_type.get_split_info.info;
}
int main(void) {
 struct api valid={get_status},missing={0};
 transports[0].api=NULL;transports[1].api=&missing;
 assert(!query().peripheral_connected);assert(queries==0);
 transports[1].api=&valid;
#if CONFIG_ZMK_SPLIT_ROLE_CENTRAL
 state=(struct zmk_split_transport_status){true,true,0};
 assert(query().is_split && query().is_central && !query().peripheral_connected);
 state.connections=2;assert(query().peripheral_connected);
 state.connections=0;assert(!query().peripheral_connected); /* Disconnect after successful query. */
 state.connections=1;assert(query().peripheral_connected); /* Reconnect / some sources. */
 state.available=false;assert(!query().peripheral_connected);
 state.available=true;state.enabled=false;assert(!query().peripheral_connected);
 state.enabled=true;state.connections=99;assert(!query().peripheral_connected);
 assert(!query().central_bonded);
#elif CONFIG_ZMK_SPLIT_ROLE_PERIPHERAL
 bonded=true;assert(query().is_split && !query().is_central && query().central_bonded);
 bonded=false;assert(!query().central_bonded && !query().peripheral_connected);
 assert(queries==0);
#else
 assert(!query().is_split && !query().is_central && !query().central_bonded);
 assert(queries==0);
#endif
 puts("Split RPC role/status transition test: PASS");
}
"""
for role,split,central,peripheral in [("central",1,1,0),("peripheral",1,0,1),("non-split",0,0,0)]:
    flags=f"-DCONFIG_ZMK_SPLIT_BLE={split} -DCONFIG_ZMK_SPLIT_ROLE_CENTRAL={central} -DCONFIG_ZMK_SPLIT_ROLE_PERIPHERAL={peripheral}"
    command=f"gcc -std=c11 -Wall -Wextra -Werror -Wno-unused-function -Wno-unused-parameter {flags} -x c -o /tmp/cleave-split-rpc - && /tmp/cleave-split-rpc"
    subprocess.run(["wsl","--","bash","-lc",command],input=(stub+helper+handler+test).encode(),check=True)
    print(role, "PASS")
