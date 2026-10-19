#include <zephyr/init.h>
#include "peer_work.h"

K_THREAD_STACK_DEFINE(peer_stack, 2048);
struct k_work_q cleave_peer_work_q;

static int peer_work_init(void) {
    k_work_queue_start(&cleave_peer_work_q, peer_stack,
                       K_THREAD_STACK_SIZEOF(peer_stack), 5, NULL);
    return 0;
}
SYS_INIT(peer_work_init, POST_KERNEL, CONFIG_KERNEL_INIT_PRIORITY_DEFAULT);
