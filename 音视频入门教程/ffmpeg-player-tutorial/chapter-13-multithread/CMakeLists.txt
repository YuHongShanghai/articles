add_executable(multithread-decode main.cpp)

target_include_directories(multithread-decode PRIVATE
    ${AVFORMAT_INCLUDE_DIRS}
    ${AVCODEC_INCLUDE_DIRS}
    ${AVUTIL_INCLUDE_DIRS}
    ${CMAKE_SOURCE_DIR}/chapter-12-queue
)

target_link_libraries(multithread-decode PRIVATE
    ${AVFORMAT_LIBRARIES}
    ${AVCODEC_LIBRARIES}
    ${AVUTIL_LIBRARIES}
    pthread
)
