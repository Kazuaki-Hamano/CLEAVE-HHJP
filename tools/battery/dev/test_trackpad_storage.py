"""Exercise actual firmware storage migration and codec with WSL gcc."""
from pathlib import Path
import subprocess

s = Path('src/trackpad_settings.c').read_text(encoding='utf-8')
validation = s[s.index('int cleave_trackpad_validate('):s.index('void cleave_trackpad_get(')]
storage = s[s.index('static bool equal_config('):s.index('SETTINGS_STATIC_HANDLER_DEFINE(')]
prefix = r'''
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#include <stdio.h>
#include "trackpad_settings.h"
#include "trackpad_math.h"
typedef int k_spinlock_key_t;
typedef int (*settings_read_cb)(void *, void *, size_t);
static int cfg_lock;
static uint32_t generation;
static struct cleave_trackpad_config config,saved;
static int k_spin_lock(int *p) {return 0;}
static void k_spin_unlock(int *p,int key) {}
static uint16_t sys_get_le16(const uint8_t *p) {return p[0]|((uint16_t)p[1]<<8);}
static void sys_put_le16(uint16_t v,uint8_t *p) {p[0]=v;p[1]=v>>8;}
static int reader(void *p,void *out,size_t n) {memcpy(out,p,n);return n;}
'''
test = r'''
int main(void) {
 uint8_t v1[8]={1};
 sys_put_le16(275,v1+1);sys_put_le16(80,v1+3);sys_put_le16(455,v1+5);v1[7]=4;
 assert(settings_set("config",8,reader,v1)==0);
 assert(config.speed==280 && config.maximum==460 && config.acceleration==80);
 assert(config.sensitivity==1 && config.scroll==100 && config.native_scroll==100);
 uint8_t v2[10]={2};
 struct cleave_trackpad_config desired={200,80,450,1,230,170};
 uint8_t encoded[11];encode_config(encoded,&desired);memcpy(v2+1,encoded,9);
 assert(settings_set("config",10,reader,v2)==0);
 assert(config.scroll==230 && config.native_scroll==100);
 uint8_t v3[12]={3};encode_config(v3+1,&desired);
 assert(settings_set("config",12,reader,v3)==0);
 assert(equal_config(&config,&desired) && equal_config(&saved,&desired));
 desired.native_scroll=180;assert(!equal_config(&config,&desired));
 assert(generation==3);
 v3[0]=2;assert(settings_set("config",12,reader,v3)==-EINVAL);
 v3[0]=3;sys_put_le16(0,v3+10);assert(settings_set("config",12,reader,v3)==-EINVAL);
 assert(settings_set("config",11,reader,v3)==-EINVAL);
 assert(config.native_scroll==170);
 puts("Firmware storage: v1/v2 migration, v3 restore, independent fields, invalid rejection: PASS");
}
'''
subprocess.run(['wsl', '--', 'bash', '-lc',
                'gcc -Wall -Wextra -Werror -Wno-unused-parameter -I src -x c -o /tmp/cleave-trackpad-storage - && /tmp/cleave-trackpad-storage'],
               input=(prefix + validation + storage + test).encode(), check=True)
