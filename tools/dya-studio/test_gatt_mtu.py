"""Run original/patched GATT sizing and TX callbacks with MTU/refcount mocks."""
from pathlib import Path
import subprocess

stub = r"""
#include <assert.h>
#include <stdint.h>
#include <string.h>
#include <stdio.h>
#define MIN(a,b) ((a)<(b)?(a):(b))
#define LOG_WRN(...)
#define K_NO_WAIT 0
struct k_work {int unused;};
struct bt_conn {uint16_t mtu;};
struct data_len {uint16_t tx_max_len;};
struct bt_conn_info {struct {struct data_len *data_len;} le;};
static struct data_len dle={27};
static struct bt_conn host={23};
static int refs, errors, received, semaphore=1;
static uint8_t output[256], indicate_buffer[27];
struct ring_buf {uint8_t data[256];unsigned pos,len;};
static struct ring_buf tx;
static struct {uint16_t len;} rpc_indicate_params;
#define indicate_sem semaphore
static int k_sem_take(int *s,int timeout) {if(!*s)return -1;*s=0;return 0;}
static void k_sem_give(int *s) {*s=1;}
static struct bt_conn *zmk_ble_active_profile_conn(void) {refs++;return &host;}
static void bt_conn_unref(struct bt_conn *c) {refs--;}
static int bt_conn_get_info(struct bt_conn *c,struct bt_conn_info *i) {i->le.data_len=&dle;return 0;}
static uint16_t bt_gatt_get_mtu(struct bt_conn *c) {return c->mtu;}
static struct ring_buf *zmk_rpc_get_tx_buf(void) {return &tx;}
static unsigned ring_buf_size_get(struct ring_buf *r) {return r->len-r->pos;}
static void ring_buf_reset(struct ring_buf *r) {r->pos=r->len=0;}
static int ring_buf_get_claim(struct ring_buf *r,uint8_t **p,unsigned n) {*p=r->data+r->pos;return MIN(n,r->len-r->pos);}
static void ring_buf_get_finish(struct ring_buf *r,unsigned n) {r->pos+=n;}
static int bt_gatt_indicate(struct bt_conn *c,void *params) {
 if(rpc_indicate_params.len>c->mtu-3){errors++;return -1;}
 memcpy(output+received,indicate_buffer,rpc_indicate_params.len);
 received+=rpc_indicate_params.len;return 0;
}
"""
test = r"""
static void init(unsigned mtu) {
 host.mtu=mtu;refs=errors=received=0;semaphore=1;tx.pos=0;tx.len=80;
 for(unsigned i=0;i<tx.len;i++)tx.data[i]=i;
}
int main(void) {
 init(23);
 while(ring_buf_size_get(&tx)){notif_rpc_tx_cb(NULL);k_sem_give(&indicate_sem);}
#if PATCHED
 assert(errors==0 && received==80 && refs==0);
 for(int i=0;i<80;i++)assert(output[i]==i);
 assert(get_notify_size_for_conn(NULL)==20);
#else
 assert(errors>0 && received<80); /* DLE=27 exceeds ATT payload=20. */
#endif
 init(247);
 while(ring_buf_size_get(&tx)){notif_rpc_tx_cb(NULL);k_sem_give(&indicate_sem);}
 assert(errors==0 && received==80 && refs==0);
 for(int i=0;i<80;i++)assert(output[i]==i);
 init(23);semaphore=0;notif_rpc_tx_cb(NULL);
 assert(refs==(PATCHED?0:1)); /* Busy callback must release acquired connection. */
#if PATCHED
 init(3);notif_rpc_tx_cb(NULL);assert(received==0 && errors==0 && refs==0);
#endif
 puts(PATCHED?"PATCHED MTU23/247 byte order and busy reference cleanup: PASS":
      "UPSTREAM invalid indication size/data loss and busy reference leak: reproduced");
}
"""

for patched, path in [
    (False, Path("output/dya-research/ble-studio/src/studio/gatt_rpc_transport.c")),
    (True, Path("src/studio/gatt_rpc_transport.c")),
]:
    source = path.read_text(encoding="utf-8")
    start = source.index("static uint16_t get_notify_size_for_conn(")
    sizing = source[start:source.index("static void refresh_notify_size", start)]
    start = source.index("static void notif_rpc_tx_cb(")
    callback = source[start:source.index("static K_WORK_DEFINE(notify_tx_work", start)]
    command = (
        "gcc -std=c11 -Wall -Wextra -Werror -Wno-unused-parameter -Wno-unused-function "
        f"-DPATCHED={int(patched)} -x c -o /tmp/cleave-gatt-mtu - && /tmp/cleave-gatt-mtu"
    )
    subprocess.run(["wsl", "--", "bash", "-lc", command],
                   input=(stub + sizing + callback + test).encode(), check=True)
