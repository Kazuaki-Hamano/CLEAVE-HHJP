"""Real nanopb round-trip checks for production activity Get/Set handlers."""
from pathlib import Path
import argparse
import os
import subprocess
import sys
import urllib.request
parser=argparse.ArgumentParser();parser.add_argument("--deps",required=True);args=parser.parse_args()
deps=Path(args.deps).resolve();sys.path.insert(0,str(deps))
import importlib.metadata
assert importlib.metadata.version("nanopb")=="0.4.9.1"
r=Path("output/dya-research/activity-wire").resolve();r.mkdir(parents=True,exist_ok=True)
for n in ["pb.h","pb_common.h","pb_common.c","pb_encode.h","pb_encode.c","pb_decode.h","pb_decode.c"]:
 p=r/n
 if not p.exists():p.write_bytes(urllib.request.urlopen("https://raw.githubusercontent.com/nanopb/nanopb/0.4.9.1/"+n).read())
env=dict(os.environ);env["PYTHONPATH"]=str(deps)
subprocess.run([sys.executable,str(deps/"nanopb/generator/nanopb_generator.py"),"-I","modules/settings-rpc/proto","-D",str(r),"modules/settings-rpc/proto/zmk/settings/core.proto"],env=env,check=True)
s=Path("modules/settings-rpc/src/studio/settings_rpc_handler.c").read_text()
functions=[]
for name,marker in [("get","Handle GetActivitySettings request"),("set","Handle SetActivitySettings request")]:
 start=s.index("static int handle_"+name+"_activity_settings(",s.index(marker))
 functions.append(s[start:s.index("\n/**",start)])
stub=r"""
#include <assert.h>
#include <stdint.h>
#include <stdbool.h>
#include <errno.h>
#include <stdio.h>
#include "pb_encode.h"
#include "pb_decode.h"
#include "zmk/settings/core.pb.h"
#define IS_ENABLED(x) (x)
#define LOG_DBG(...)
static uint32_t wanted_idle,wanted_sleep;
static int queue_error;
static int cleave_activity_sync_queue(uint32_t i,uint32_t s) {wanted_idle=i;wanted_sleep=s;return queue_error;}
static uint32_t zmk_activity_get_idle_ms(void) {return 45000;}
static uint32_t zmk_activity_get_sleep_ms(void) {return 900000;}
"""
test=r"""
static zmk_settings_Response wire(zmk_settings_Response *r) {
 uint8_t bytes[128];pb_ostream_t out=pb_ostream_from_buffer(bytes,sizeof(bytes));
 assert(pb_encode(&out,zmk_settings_Response_fields,r));
 zmk_settings_Response decoded=zmk_settings_Response_init_zero;
 pb_istream_t in=pb_istream_from_buffer(bytes,out.bytes_written);
 assert(pb_decode(&in,zmk_settings_Response_fields,&decoded));return decoded;
}
int main(void) {
 zmk_settings_Response response=zmk_settings_Response_init_zero;
 zmk_settings_GetActivitySettingsRequest get={0};assert(handle_get_activity_settings(&get,&response)==0);
 zmk_settings_Response decoded=wire(&response);
 assert(decoded.which_response_type==zmk_settings_Response_get_activity_settings_tag);
 assert(decoded.response_type.get_activity_settings.has_settings);
 assert(decoded.response_type.get_activity_settings.settings.idle_ms==45000);
 assert(decoded.response_type.get_activity_settings.settings.sleep_ms==900000);
 zmk_settings_SetActivitySettingsRequest set=zmk_settings_SetActivitySettingsRequest_init_zero;
 assert(handle_set_activity_settings(&set,&response)==-EINVAL);
 set.has_settings=true;set.settings.idle_ms=70000;set.settings.sleep_ms=1200000;
 assert(handle_set_activity_settings(&set,&response)==0);
 assert(wanted_idle==70000 && wanted_sleep==1200000);
 decoded=wire(&response);assert(decoded.response_type.set_activity_settings.success);
 queue_error=-EIO;assert(handle_set_activity_settings(&set,&response)!=0);
 decoded=wire(&response);assert(!decoded.response_type.set_activity_settings.success);
 puts("Activity RPC: real wire presence, explicit settings, queued result and save failure: PASS");
}
"""
(r/"test.c").write_text(stub+"\n".join(functions)+test)
wslroot=subprocess.check_output(["wsl","--","wslpath","-a",r.as_posix()],text=True).strip()
command=f"cd '{wslroot}' && gcc -std=c11 -I . -DCONFIG_ZMK_SPLIT_ROLE_CENTRAL=1 test.c zmk/settings/core.pb.c pb_common.c pb_encode.c pb_decode.c -o /tmp/cleave-activity-rpc && /tmp/cleave-activity-rpc"
subprocess.run(["wsl","--","bash","-lc",command],check=True)
