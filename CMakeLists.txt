if(CONFIG_ZMK_POINTING)
  target_sources(app PRIVATE ${CMAKE_CURRENT_LIST_DIR}/src/mouse_speed.c)
endif()

if(CONFIG_SHIELD_CLEAVE_HHJP_LEFT OR CONFIG_SHIELD_CLEAVE_HHJP_RIGHT)
  target_sources(app PRIVATE ${CMAKE_CURRENT_LIST_DIR}/src/charge_status.c)
  target_sources(app PRIVATE ${CMAKE_CURRENT_LIST_DIR}/src/app_update.c)
  execute_process(COMMAND git rev-parse --short=8 HEAD
    WORKING_DIRECTORY ${CMAKE_CURRENT_LIST_DIR}
    OUTPUT_VARIABLE CLEAVE_UPDATE_GIT_ID OUTPUT_STRIP_TRAILING_WHITESPACE)
  if(NOT CLEAVE_UPDATE_GIT_ID MATCHES "^[0-9a-f]+$")
    message(FATAL_ERROR "Cannot determine CLEAVE update build identity")
  endif()
  target_compile_definitions(app PRIVATE CLEAVE_UPDATE_BUILD_ID=\"${CLEAVE_UPDATE_GIT_ID}\")
endif()

if(CONFIG_ZMK_SPLIT_BLE_CENTRAL_BATTERY_LEVEL_FETCHING AND CONFIG_USB_HID_DEVICE_COUNT GREATER 1)
  target_sources(app PRIVATE ${CMAKE_CURRENT_LIST_DIR}/src/usb_battery.c)
endif()
