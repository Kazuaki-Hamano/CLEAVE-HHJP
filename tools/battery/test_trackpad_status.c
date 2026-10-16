#include <assert.h>
#include "../../src/trackpad_status.h"

int main(void) {
    uint8_t applied;
    int8_t error;
    for (unsigned sensitivity = 0; sensitivity <= 4; sensitivity++) {
        for (int err = -128; err <= 127; err++) {
            int32_t value = cleave_trackpad_status_encode(sensitivity, err);
            assert(cleave_trackpad_status_decode(value, &applied, &error));
            assert(applied == sensitivity && error == err);
        }
    }
    assert(!cleave_trackpad_status_decode(0, &applied, &error));
    assert(!cleave_trackpad_status_decode(0x54500005, &applied, &error));
    assert(!cleave_trackpad_status_decode(0x55500001, &applied, &error));
    return 0;
}
