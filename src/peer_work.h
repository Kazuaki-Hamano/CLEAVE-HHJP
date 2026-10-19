#pragma once
#include <zephyr/kernel.h>

/* GATT request allocation may block. Keep it off the system work queue,
 * which also runs Bluetooth completion and split connection work. */
extern struct k_work_q cleave_peer_work_q;
