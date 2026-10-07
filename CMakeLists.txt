if(CONFIG_ZMK_POINTING)
  target_sources(app PRIVATE ${CMAKE_CURRENT_LIST_DIR}/src/mouse_speed.c)
endif()
