cmake_minimum_required(VERSION 3.10)
project(06_CameraSystem)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# ── 查找依赖 ──
find_package(OpenGL REQUIRED)
find_package(glfw3 3.3 REQUIRED)
find_package(glm REQUIRED)

# ── GLAD（需要本地 glad 源码） ──
# 如果你通过 Homebrew 安装了 glad，可以改用 find_package(glad)
# 否则请将 glad 源码放到 third_party/glad/ 下
if(EXISTS "${CMAKE_SOURCE_DIR}/third_party/glad/src/glad.c")
    add_library(glad "${CMAKE_SOURCE_DIR}/third_party/glad/src/glad.c")
    target_include_directories(glad PUBLIC "${CMAKE_SOURCE_DIR}/third_party/glad/include")
else()
    # 尝试系统路径
    find_package(glad QUIET)
    if(NOT glad_FOUND)
        message(STATUS "glad not found via find_package, trying pkg-config or manual path...")
        # Homebrew 常见路径
        find_library(GLAD_LIB glad HINTS /usr/local/lib /opt/homebrew/lib)
        find_path(GLAD_INCLUDE glad/glad.h HINTS /usr/local/include /opt/homebrew/include)
        if(GLAD_LIB AND GLAD_INCLUDE)
            add_library(glad INTERFACE)
            target_link_libraries(glad INTERFACE ${GLAD_LIB})
            target_include_directories(glad INTERFACE ${GLAD_INCLUDE})
        else()
            message(FATAL_ERROR
                "Could not find GLAD. Please either:\n"
                "  1) Place glad source in third_party/glad/ (recommended)\n"
                "  2) Install glad via your package manager")
        endif()
    endif()
endif()

# ── 可执行文件 ──
add_executable(camera_demo main.cpp)

target_link_libraries(camera_demo
    OpenGL::GL
    glfw
    glad
    glm::glm
)

target_include_directories(camera_demo PRIVATE ${CMAKE_SOURCE_DIR})

# macOS framework 依赖
if(APPLE)
    target_link_libraries(camera_demo
        "-framework Cocoa"
        "-framework IOKit"
        "-framework CoreVideo"
    )
endif()
