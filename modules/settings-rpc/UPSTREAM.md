# Settings RPC snapshot

Upstream: https://github.com/cormoran/zmk-module-settings-rpc
Revision: 78f86df9e6c5edaf57bef3ccbd7f360cfdf49291
MIT license retained. Only required event/header/core-proto/build inputs are included;
unused template protocol and web sources are not vendored.

Root CMake/Kconfig includes this snapshot instead of the former west project.
Local changes: durable one-peripheral activity-settings outbox, synchronous
activity/s save before acknowledgement, sequence/value-checked acknowledgements,
GetActivitySettings presence flag, rejection of a missing settings message, and
correction of a void return. Host protobuf contract stays unchanged. Private
split relay changed/report structs add a uint32 transaction ID, requiring both
trial halves to be flashed together. Request/report ID for ordinary reads remains unchanged.
