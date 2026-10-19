"""Encode/decode the production GetSplitInfo handler with real nanopb.

Requires nanopb and grpcio-tools in the supplied --deps directory (pip --target).
The C runtime is fetched from the matching official nanopb release; output is ignored.
"""
from pathlib import Path
import argparse
import os
import re
import subprocess
import sys
import urllib.request
import importlib.metadata

parser=argparse.ArgumentParser()
parser.add_argument("--deps",required=True)
a=parser.parse_args()
deps=Path(a.deps).resolve()
sys.path.insert(0,str(deps))
version=importlib.metadata.version("nanopb")
root=Path("output/dya-research/split-wire").resolve();root.mkdir(parents=True,exist_ok=True)
for name in ["pb.h","pb_common.h","pb_common.c","pb_encode.h","pb_encode.c","pb_decode.h","pb_decode.c"]:
    target=root/name
    if not target.exists():
        target.write_bytes(urllib.request.urlopen(f"https://raw.githubusercontent.com/nanopb/nanopb/{version}/{name}").read())
env=dict(os.environ);env["PYTHONPATH"]=str(deps)
subprocess.run([sys.executable,str(deps/"nanopb/generator/nanopb_generator.py"),"-I","modules/ble-management/proto","-D",str(root),"modules/ble-management/proto/zmk/ble_management/ble_management.proto"],env=env,check=True)
source=Path("modules/ble-management/src/studio/ble_management_handler.c").read_text()
start=source.index("static int handle_get_split_info_request(",source.index("Handle GetSplitInfoRequest"))
handler=source[start:source.index("\n/**",start)]
helper=re.sub(r"^#(?:include|pragma).*$","",Path("modules/ble-management/include/cleave_split_status.h").read_text(),flags=re.M)
# Reuse transport mocks but use the REAL generated protobuf structs below.
harness=Path("tools/dya-studio/test_split_status.py").read_text()
stub=harness.split('stub = r"""',1)[1].split('typedef struct {bool is_split',1)[0]
stub+='#include "zmk/ble_management/ble_management.pb.h"\n#include "pb_encode.h"\n#include "pb_decode.h"\n'
test=r"""
static void round_trip(bool connected) {
 struct api valid={get_status};transports[0].api=&valid;
 state=(struct zmk_split_transport_status){true,true,connected?2:0};
 zmk_ble_management_GetSplitInfoRequest req={0};
 zmk_ble_management_Response resp=zmk_ble_management_Response_init_zero;
 assert(handle_get_split_info_request(&req,&resp)==0);
 uint8_t bytes[128];pb_ostream_t output=pb_ostream_from_buffer(bytes,sizeof(bytes));
 assert(pb_encode(&output,zmk_ble_management_Response_fields,&resp));
 zmk_ble_management_Response decoded=zmk_ble_management_Response_init_zero;
 pb_istream_t input=pb_istream_from_buffer(bytes,output.bytes_written);
 assert(pb_decode(&input,zmk_ble_management_Response_fields,&decoded));
 assert(decoded.which_response_type==zmk_ble_management_Response_get_split_info_tag);
 assert(decoded.response_type.get_split_info.has_info);
#if CONFIG_ZMK_SPLIT_ROLE_CENTRAL
 assert(decoded.response_type.get_split_info.info.is_split);
 assert(decoded.response_type.get_split_info.info.is_central);
 assert(decoded.response_type.get_split_info.info.peripheral_connected==connected);
#endif
 /* Reproduce old bug: populating info without has_info omits the message. */
 resp.response_type.get_split_info.has_info=false;
 output=pb_ostream_from_buffer(bytes,sizeof(bytes));
 assert(pb_encode(&output,zmk_ble_management_Response_fields,&resp));
 decoded=(zmk_ble_management_Response)zmk_ble_management_Response_init_zero;
 input=pb_istream_from_buffer(bytes,output.bytes_written);
 assert(pb_decode(&input,zmk_ble_management_Response_fields,&decoded));
 assert(!decoded.response_type.get_split_info.has_info);
}
int main(void) {round_trip(false);round_trip(true);puts("Real nanopb SplitInfo wire presence and old omission reproduction: PASS");}
"""
(root/"test.c").write_text(stub+helper+handler+test)
# Work through wslpath to avoid assuming a Windows mount layout.
wslroot=subprocess.check_output(["wsl","--","wslpath","-a",root.as_posix()],text=True).strip()
for role,split,central,peripheral in [("central",1,1,0),("peripheral",1,0,1),("non-split",0,0,0)]:
    command=f"cd '{wslroot}' && gcc -std=c11 -I . -DCONFIG_ZMK_SPLIT_BLE={split} -DCONFIG_ZMK_SPLIT_ROLE_CENTRAL={central} -DCONFIG_ZMK_SPLIT_ROLE_PERIPHERAL={peripheral} test.c zmk/ble_management/ble_management.pb.c pb_common.c pb_encode.c pb_decode.c -o /tmp/cleave-split-wire && /tmp/cleave-split-wire"
    subprocess.run(["wsl","--","bash","-lc",command],check=True)
    print(role,"wire PASS", "nanopb",version)
