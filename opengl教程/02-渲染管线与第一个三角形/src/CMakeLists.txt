cmake_minimum_required(VERSION 3.10)
project(OpenGL_Triangle LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# --------------------------------------------------------------------------
# 依赖：GLFW 和 OpenGL
# --------------------------------------------------------------------------
find_package(glfw3 3.3 REQUIRED)
find_package(OpenGL REQUIRED)

# --------------------------------------------------------------------------
# GLAD —— 如果通过系统/Homebrew 安装，使用 find_package；
#          否则假定 glad 源码在项目同级 third_party 目录或已安装
# --------------------------------------------------------------------------
# 方式一：glad 以源码形式包含（最通用）
# 如果你把 glad.c 和头文件放在项目 third_party/glad 下，取消下面的注释：
# add_library(glad STATIC third_party/glad/src/glad.c)
# target_include_directories(glad PUBLIC third_party/glad/include)

# 方式二：系统已安装 glad（例如 Homebrew: brew install glad）
find_package(glad QUIET)

if (NOT glad_FOUND)
    # 回退方案：假设 glad 源码在上级 third_party 目录
    if (EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/../third_party/glad/src/glad.c")
        add_library(glad STATIC
            "${CMAKE_CURRENT_SOURCE_DIR}/../third_party/glad/src/glad.c"
        )
        target_include_directories(glad PUBLIC
            "${CMAKE_CURRENT_SOURCE_DIR}/../third_party/glad/include"
        )
    else()
        message(FATAL_ERROR
            "找不到 glad 库。请通过以下方式之一提供 glad：\n"
            "  1. brew install glad\n"
            "  2. 将 glad 源码放入 ../third_party/glad/ 目录\n"
            "     (包含 include/glad/glad.h 和 src/glad.c)")
    endif()
endif()

# --------------------------------------------------------------------------
# 可执行文件
# --------------------------------------------------------------------------
add_executable(${PROJECT_NAME} main.cpp)

target_link_libraries(${PROJECT_NAME} PRIVATE
    glfw
    OpenGL::GL
    glad
)

# macOS 需要额外的框架
if (APPLE)
    target_link_libraries(${PROJECT_NAME} PRIVATE
        "-framework Cocoa"
        "-framework IOKit"
        "-framework CoreVideo"
    )
endif()
