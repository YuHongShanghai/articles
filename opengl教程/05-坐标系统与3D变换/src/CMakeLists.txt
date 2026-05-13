cmake_minimum_required(VERSION 3.10)
project(CoordinateSystems)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 查找所需包
find_package(glfw3 3.3 REQUIRED)
find_package(OpenGL REQUIRED)

# 查找 GLM
find_path(GLM_INCLUDE_DIR glm/glm.hpp
    HINTS
        /usr/local/include
        /opt/homebrew/include
        /usr/include
)

# 查找 GLAD — 如果系统未安装，需手动指定路径
set(GLAD_DIR "${CMAKE_SOURCE_DIR}/../third_party/glad" CACHE PATH "Path to GLAD")
set(STB_DIR   "${CMAKE_SOURCE_DIR}/../third_party"      CACHE PATH "Path to stb_image.h")

add_executable(${PROJECT_NAME}
    main.cpp
    ${GLAD_DIR}/src/glad.c
)

target_include_directories(${PROJECT_NAME} PRIVATE
    ${GLAD_DIR}/include
    ${GLM_INCLUDE_DIR}
    ${STB_DIR}
)

target_link_libraries(${PROJECT_NAME}
    glfw
    OpenGL::GL
)

# macOS 额外框架
if(APPLE)
    target_link_libraries(${PROJECT_NAME}
        "-framework Cocoa"
        "-framework IOKit"
        "-framework CoreVideo"
    )
endif()

# 将着色器文件复制到构建目录
configure_file(${CMAKE_SOURCE_DIR}/cube.vs ${CMAKE_BINARY_DIR}/cube.vs COPYONLY)
configure_file(${CMAKE_SOURCE_DIR}/cube.fs ${CMAKE_BINARY_DIR}/cube.fs COPYONLY)
