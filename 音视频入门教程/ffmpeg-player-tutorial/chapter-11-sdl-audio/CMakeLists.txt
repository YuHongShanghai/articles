if(SDL2_FOUND)
    add_executable(sdl-audio main.cpp)

    target_include_directories(sdl-audio PRIVATE
        ${AVFORMAT_INCLUDE_DIRS}
        ${AVCODEC_INCLUDE_DIRS}
        ${AVUTIL_INCLUDE_DIRS}
        ${SWRESAMPLE_INCLUDE_DIRS}
        ${SDL2_INCLUDE_DIRS}
    )

    target_link_libraries(sdl-audio PRIVATE
        ${AVFORMAT_LIBRARIES}
        ${AVCODEC_LIBRARIES}
        ${AVUTIL_LIBRARIES}
        ${SWRESAMPLE_LIBRARIES}
        ${SDL2_LIBRARIES}
    )
else()
    message(WARNING "SDL2 not found, skipping chapter-11-sdl-audio")
endif()
