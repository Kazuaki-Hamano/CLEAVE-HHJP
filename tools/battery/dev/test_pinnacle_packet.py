"""Run the actual driver's packet reporter with mocked I/O (WSL gcc)."""
from pathlib import Path
import subprocess

source = Path('src/pinnacle/input_pinnacle.c').read_text(encoding='utf-8')
reporter = source[source.index('static void pinnacle_report_data('):source.index('static void pinnacle_work_cb(')]
stub = r'''
#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <assert.h>
#include <stdio.h>
#define PINNACLE_STATUS1 2
#define PINNACLE_STATUS1_SW_DR 8
#define PINNACLE_2_2_PACKET0 0x12
#define PINNACLE_PACKET0_BTN_PRIM 1
#define PINNACLE_PACKET0_BTN_SEC 2
#define PINNACLE_PACKET0_BTN_AUX 4
#define PINNACLE_PACKET0_X_SIGN 16
#define PINNACLE_PACKET0_Y_SIGN 32
#define INPUT_BTN_0 0
#define INPUT_REL_X 0
#define INPUT_REL_Y 1
#define INPUT_REL_WHEEL 8
#define K_FOREVER 0
#define BIT(n) (1u << (n))
#define LOG_ERR(...) ((void)0)
#define LOG_DBG(...) ((void)0)
#define LOG_HEXDUMP_DBG(...) ((void)0)
#define WRITE_BIT(v,b,x) ((v)|=(1<<(b)))
struct pinnacle_config {bool no_taps,native_scroll;};
struct pinnacle_data {bool in_int; uint8_t btn_cache;};
struct device {const struct pinnacle_config *config; struct pinnacle_data *data;};
static uint8_t payload[4];
static int reads, wheels, wheel_value, syncs, buttons;
static int pinnacle_seq_read(const struct device *d,int addr,uint8_t *p,int len) {
 if(addr==PINNACLE_STATUS1) {*p=PINNACLE_STATUS1_SW_DR; return 0;}
 assert(len==4); memcpy(p,payload,4); reads++;return 0;
}
static int pinnacle_clear_status(const struct device *d) {return 0;}
static void input_report_key(const struct device *d,int code,int value,bool sync,int wait) {buttons++;}
static void input_report_rel(const struct device *d,int code,int value,bool sync,int wait) {
 if(code==INPUT_REL_WHEEL) {wheels++;wheel_value=value;assert(!sync);}
 if(sync) {syncs++; assert(code==INPUT_REL_Y);}
}
'''
test = r'''
int main(void) {
 struct pinnacle_config cfg={.native_scroll=true}; struct pinnacle_data data={0};
 struct device dev={&cfg,&data};
 for(int value=-128; value<=127; value++) {
  payload[3]=(uint8_t)value; wheels=syncs=0;
  pinnacle_report_data(&dev);
  assert(syncs==1 && wheels==(value!=0));
  if(value) assert(wheel_value==value);
 }
 cfg.native_scroll=false; payload[3]=7; wheels=syncs=0;
 pinnacle_report_data(&dev);assert(wheels==0 && syncs==1);
 payload[0]=1;pinnacle_report_data(&dev);
 payload[0]=0;pinnacle_report_data(&dev);assert(buttons==2);
 puts("Actual Pinnacle reporter: 4-byte read, signed wheel, opt-in, sync, tap release: PASS");
}
'''
subprocess.run(['wsl', '--', 'bash', '-lc',
                'gcc -Wall -Wextra -Werror -Wno-unused-parameter -x c -o /tmp/cleave-pinnacle-packet - && /tmp/cleave-pinnacle-packet'],
               input=(stub + reporter + test).encode(), check=True)
