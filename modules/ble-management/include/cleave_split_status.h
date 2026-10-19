/* SPDX-License-Identifier: MIT */
#pragma once
#include <zephyr/sys/iterable_sections.h>
#include <zmk/split/transport/central.h>

/* Query on demand: no callback replacement, polling, bond/host inference or
 * cached battery data. CLEAVE uses one BLE peripheral and no wired transport. */
static inline bool cleave_split_peripheral_connected(void) {
    STRUCT_SECTION_FOREACH(zmk_split_transport_central, transport) {
        if (!transport->api || !transport->api->get_status) { continue; }
        struct zmk_split_transport_status status = transport->api->get_status();
        if (status.available && status.enabled &&
            (status.connections == ZMK_SPLIT_TRANSPORT_CONNECTIONS_STATUS_SOME_CONNECTED ||
             status.connections == ZMK_SPLIT_TRANSPORT_CONNECTIONS_STATUS_ALL_CONNECTED)) {
            return true;
        }
    }
    return false;
}
