if(SDL2_FOUND)
    find_package(PkgConfig REQUIRED)
    pkg_check_modules(SDL2_TTF SDL2_ttf)

    if(SDL2_TTF_FOUND)
        add_executable(subtitle-demo main.cpp)
        target_include_directories(subtitle-demo PRIVATE
            ${AVFORMAT_INCLUDE_DIRS}
            ${AVCODEC_INCLUDE_DIRS}
            ${AVUTIL_INCLUDE_DIRS}
            ${SWRESAMPLE_INCLUDE_DIRS}
            ${SDL2_INCLUDE_DIRS}
            ${SDL2_TTF_INCLUDE_DIRS}
            ${CMAKE_SOURCE_DIR}/chapter-12-queue
        )
        target_link_libraries(subtitle-demo PRIVATE
            ${AVFORMAT_LIBRARIES}
            ${AVCODEC_LIBRARIES}
            ${AVUTIL_LIBRARIES}
            ${SWRESAMPLE_LIBRARIES}
            ${SDL2_LIBRARIES}
            ${SDL2_TTF_LIBRARIES}
            pthread
        )
    else()
        message(WARNING "SDL2_ttf not found, skipping chapter-17-subtitle")
    endif()
else()
    message(WARNING "SDL2 not found, skipping chapter-17-subtitle")
endif()
