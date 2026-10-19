"""Check actual TP_INT storage names against pinned Zephyr settings name limit."""
from pathlib import Path
import re
import subprocess

source = Path("src/trackpad_settings.c").read_text()
settings = re.findall(r'TP_INT\(\w+, "([^"]+)", "([^"]+)"', source)
assert len(settings) == 5
# Zephyr 63363d92 settings.h: SETTINGS_MAX_DIR_DEPTH=8; MAX_NAME_LEN=8*depth.
limit = 64
for subsystem, key in settings:
    size = len(f"custom_settings/{subsystem}/{key}".encode()) + 1
    assert size <= limit, (key, size, limit)
    print(f"{key}: {size}/{limit} bytes including NUL")
# Exercise the same snprintf truncation check used by setting_storage_name.
c = r"""
#include <assert.h>
#include <stdio.h>
int main(void) {
 char name[64];
 assert(snprintf(name,sizeof(name),"custom_settings/%s/%s","cleave_right_trackpad","right_acceleration_percent") >= sizeof(name));
 assert(snprintf(name,sizeof(name),"custom_settings/%s/%s","cleave_right_trackpad","right_native_scroll_percent") >= sizeof(name));
 assert(snprintf(name,sizeof(name),"custom_settings/%s/%s","cleave_right_trackpad","acceleration_percent") < sizeof(name));
 assert(snprintf(name,sizeof(name),"custom_settings/%s/%s","cleave_right_trackpad","native_scroll_percent") < sizeof(name));
 puts("Old names truncate; replacement names fit: PASS");
}
"""
subprocess.run(["wsl", "--", "bash", "-lc", "gcc -std=c11 -x c -o /tmp/cleave-storage-names - && /tmp/cleave-storage-names"], input=c.encode(), check=True)
# Prove the production build guard rejects the former invalid name.
runner = Path("tools/trackpad-tests/test_registry.py").read_text()
runner = runner.replace('source = re.sub(', 'source = source.replace(\'"acceleration_percent"\', \'"right_acceleration_percent"\')\nsource = re.sub(')
result = subprocess.run(["python", "-c", runner], capture_output=True, text=True)
assert result.returncode != 0 and "Trackpad setting storage name exceeds" in result.stderr, result.stderr
print("Production BUILD_ASSERT rejects oversized name: PASS")
