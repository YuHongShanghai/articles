if(SDL2_FOUND)
    add_executable(final-player main.cpp)

    target_include_directories(final-player PRIVATE
        ${AVFORMAT_INCLUDE_DIRS}
        ${AVCODEC_INCLUDE_DIRS}
        ${AVUTIL_INCLUDE_DIRS}
        ${SWSCALE_INCLUDE_DIRS}
        ${SWRESAMPLE_INCLUDE_DIRS}
        ${SDL2_INCLUDE_DIRS}
        ${CMAKE_SOURCE_DIR}/chapter-12-queue
    )

    target_link_libraries(final-player PRIVATE
        ${AVFORMAT_LIBRARIES}
        ${AVCODEC_LIBRARIES}
        ${AVUTIL_LIBRARIES}
        ${SWSCALE_LIBRARIES}
        ${SWRESAMPLE_LIBRARIES}
        ${SDL2_LIBRARIES}
        pthread
    )
else()
    message(WARNING "SDL2 not found, skipping chapter-16-final-player")
endif()
