if(SDL2_FOUND)
    add_executable(sdl-video main.cpp)

    target_include_directories(sdl-video PRIVATE
        ${AVFORMAT_INCLUDE_DIRS}
        ${AVCODEC_INCLUDE_DIRS}
        ${AVUTIL_INCLUDE_DIRS}
        ${SDL2_INCLUDE_DIRS}
    )

    target_link_libraries(sdl-video PRIVATE
        ${AVFORMAT_LIBRARIES}
        ${AVCODEC_LIBRARIES}
        ${AVUTIL_LIBRARIES}
        ${SDL2_LIBRARIES}
    )
else()
    message(WARNING "SDL2 not found, skipping chapter-10-sdl-video")
endif()
