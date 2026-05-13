cmake_minimum_required(VERSION 3.14)  # 3.14+ for FetchContent_MakeAvailable
project(OpenGLTutorials LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# macOS 静默 OpenGL 废弃 API 警告
if(APPLE)
    add_compile_definitions(GL_SILENCE_DEPRECATION)
endif()

include(FetchContent)

# ============================================================
# GLAD 检测与获取
# 优先使用 third_party/glad/，否则通过 FetchContent 自动下载
# ============================================================
set(GLAD_LOCAL_SRC "${CMAKE_SOURCE_DIR}/third_party/glad/src/glad.c")
set(GLAD_LOCAL_INC "${CMAKE_SOURCE_DIR}/third_party/glad/include")

if(EXISTS "${GLAD_LOCAL_SRC}")
    message(STATUS "GLAD: 使用本地 third_party/glad/")
    add_library(glad STATIC "${GLAD_LOCAL_SRC}")
    target_include_directories(glad PUBLIC "${GLAD_LOCAL_INC}")
    set_target_properties(glad PROPERTIES POSITION_INDEPENDENT_CODE ON)
else()
    message(STATUS "GLAD: 本地文件不存在，通过 FetchContent 下载 glad v2.x ...")
    # glad v2.x（glad2 分支）使用 CMake 原生 C 生成器，无需 Python
    # 根目录 CMakeLists.txt 会暴露 glad_add_library() 函数
    FetchContent_Declare(
        glad_fetch
        GIT_REPOSITORY https://github.com/Dav1dde/glad.git
        GIT_TAG        glad2
        GIT_SHALLOW    TRUE
    )
    FetchContent_MakeAvailable(glad_fetch)
    # glad_add_library 由 glad v2 的 cmake 模块提供
    # REPRODUCIBLE = 相同配置始终生成相同代码（可缓存）
    # LOADER = 包含运行时函数指针加载器
    glad_add_library(glad STATIC REPRODUCIBLE LOADER API gl:core=3.3)
    message(STATUS "GLAD: 下载并生成完成")
endif()

# ============================================================
# stb_image 检测与获取
# ============================================================
set(STB_LOCAL_H "${CMAKE_SOURCE_DIR}/third_party/stb/stb_image.h")

if(EXISTS "${STB_LOCAL_H}")
    message(STATUS "stb_image: 使用本地 third_party/stb/")
    set(STB_INCLUDE "${CMAKE_SOURCE_DIR}/third_party/stb")
else()
    message(STATUS "stb_image: 本地文件不存在，通过 FetchContent 下载 ...")
    FetchContent_Declare(
        stb_fetch
        GIT_REPOSITORY https://github.com/nothings/stb.git
        GIT_TAG        master
        GIT_SHALLOW    TRUE
    )
    FetchContent_MakeAvailable(stb_fetch)
    set(STB_INCLUDE "${stb_fetch_SOURCE_DIR}")
    message(STATUS "stb_image: 下载完成 -> ${STB_INCLUDE}")
endif()

# stb_image 作为 INTERFACE 库
add_library(stb_image INTERFACE)
target_include_directories(stb_image INTERFACE "${STB_INCLUDE}")

# ============================================================
# 公共工具头文件
# ============================================================
set(COMMON_INCLUDE "${CMAKE_SOURCE_DIR}/common")

# ============================================================
# 系统依赖查找
# ============================================================
find_package(glfw3 3.3 REQUIRED)
find_package(OpenGL REQUIRED)

# GLM（header-only）
find_path(GLM_INCLUDE_DIR glm/glm.hpp
    HINTS
        /usr/local/include
        /opt/homebrew/include
        /usr/include
)
if(NOT GLM_INCLUDE_DIR)
    message(FATAL_ERROR
        "\n[GLM NOT FOUND]\n"
        "请安装 GLM：\n"
        "  macOS:  brew install glm\n"
        "  Ubuntu: sudo apt install libglm-dev\n")
endif()

# Assimp（第8、10章需要）
find_package(assimp QUIET)
if(NOT assimp_FOUND)
    message(WARNING
        "\n[ASSIMP NOT FOUND] ch08_model 和 ch10_demo 将被跳过。\n"
        "安装 Assimp：\n"
        "  macOS:  brew install assimp\n"
        "  Ubuntu: sudo apt install libassimp-dev\n")
endif()

# ============================================================
# 辅助宏：链接 OpenGL/GLFW 及平台框架
# ============================================================
macro(link_opengl_libs TARGET)
    target_link_libraries(${TARGET} PRIVATE glad glfw OpenGL::GL)
    if(APPLE)
        target_link_libraries(${TARGET} PRIVATE
            "-framework Cocoa"
            "-framework IOKit"
            "-framework CoreVideo")
    endif()
endmacro()

# 辅助函数：将着色器文件复制到构建目录
function(copy_shaders SHADER_SRC_DIR OUTPUT_SUBDIR)
    file(GLOB SHADER_FILES "${SHADER_SRC_DIR}/*")
    foreach(SHADER_FILE ${SHADER_FILES})
        get_filename_component(SHADER_NAME ${SHADER_FILE} NAME)
        configure_file(${SHADER_FILE}
            "${CMAKE_BINARY_DIR}/${OUTPUT_SUBDIR}/${SHADER_NAME}" COPYONLY)
    endforeach()
endfunction()

# 辅助函数：将源码目录下的 resources/ 递归复制到构建目录
# 用法：copy_resources(TARGET chXX)
#   源：${CMAKE_SOURCE_DIR}/chXX/resources/
#   目标：${CMAKE_BINARY_DIR}/chXX/resources/
function(copy_resources TARGET CHAPTER_SUBDIR)
    set(RES_SRC "${CMAKE_SOURCE_DIR}/${CHAPTER_SUBDIR}/resources")
    set(RES_DST "${CMAKE_BINARY_DIR}/${CHAPTER_SUBDIR}/resources")
    if(EXISTS "${RES_SRC}")
        # 在每次构建时同步 resources/ 目录（增量复制）
        add_custom_command(TARGET ${TARGET} POST_BUILD
            COMMAND ${CMAKE_COMMAND} -E copy_directory
                "${RES_SRC}" "${RES_DST}"
            COMMENT "Copying ${CHAPTER_SUBDIR}/resources/ -> build/${CHAPTER_SUBDIR}/resources/"
        )
        message(STATUS "${TARGET}: 将在构建后同步 resources/ 到输出目录")
    endif()
endfunction()

# 辅助函数：将源码目录下指定子目录复制到构建目录对应位置
# 用法：copy_directory_to_build(TARGET chXX SUBDIR textures)
function(copy_directory_to_build TARGET CHAPTER_SUBDIR SUBDIR)
    set(DIR_SRC "${CMAKE_SOURCE_DIR}/${CHAPTER_SUBDIR}/${SUBDIR}")
    set(DIR_DST "${CMAKE_BINARY_DIR}/${CHAPTER_SUBDIR}/${SUBDIR}")
    if(EXISTS "${DIR_SRC}")
        add_custom_command(TARGET ${TARGET} POST_BUILD
            COMMAND ${CMAKE_COMMAND} -E copy_directory
                "${DIR_SRC}" "${DIR_DST}"
            COMMENT "Copying ${CHAPTER_SUBDIR}/${SUBDIR}/ -> build/${CHAPTER_SUBDIR}/${SUBDIR}/"
        )
    endif()
endfunction()

# 辅助函数：将源码目录下指定文件复制到构建目录对应位置
# 用法：copy_files_to_build(TARGET chXX file1.jpg file2.png ...)
function(copy_files_to_build TARGET CHAPTER_SUBDIR)
    foreach(FNAME ${ARGN})
        set(FILE_SRC "${CMAKE_SOURCE_DIR}/${CHAPTER_SUBDIR}/${FNAME}")
        set(FILE_DST "${CMAKE_BINARY_DIR}/${CHAPTER_SUBDIR}/${FNAME}")
        if(EXISTS "${FILE_SRC}")
            configure_file("${FILE_SRC}" "${FILE_DST}" COPYONLY)
        endif()
    endforeach()
endfunction()

# 辅助宏：将可执行文件输出到独立子目录
macro(set_chapter_output TARGET CHAPTER_SUBDIR)
    set_target_properties(${TARGET} PROPERTIES
        RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/${CHAPTER_SUBDIR}")
endmacro()

# ============================================================
# 第1章：环境搭建与第一个窗口
# ============================================================
add_executable(ch01_window ch01/main.cpp)
target_include_directories(ch01_window PRIVATE ${GLM_INCLUDE_DIR})
link_opengl_libs(ch01_window)
set_chapter_output(ch01_window ch01)

# ============================================================
# 第2章：渲染管线与第一个三角形
# ============================================================
add_executable(ch02_triangle ch02/main.cpp)
link_opengl_libs(ch02_triangle)
set_chapter_output(ch02_triangle ch02)

# ============================================================
# 第3章：深入着色器与 GLSL
# 运行时着色器：vertex.glsl, fragment.glsl（在工作目录下）
# ============================================================
add_executable(ch03_shader ch03/main.cpp)
target_include_directories(ch03_shader PRIVATE ${COMMON_INCLUDE})
link_opengl_libs(ch03_shader)
set_chapter_output(ch03_shader ch03)
copy_shaders("${CMAKE_SOURCE_DIR}/ch03/shaders" ch03)

# ============================================================
# 第4章：纹理映射
# 运行时着色器：texture.vs, texture.fs
# ============================================================
add_executable(ch04_texture ch04/main.cpp)
target_include_directories(ch04_texture PRIVATE
    ${GLM_INCLUDE_DIR}
    ${COMMON_INCLUDE})
target_link_libraries(ch04_texture PRIVATE stb_image)
link_opengl_libs(ch04_texture)
set_chapter_output(ch04_texture ch04)
copy_shaders("${CMAKE_SOURCE_DIR}/ch04/shaders" ch04)
copy_directory_to_build(ch04_texture ch04 textures)

# ============================================================
# 第5章：坐标系统与 3D 变换
# 运行时着色器：cube.vs, cube.fs
# ============================================================
add_executable(ch05_transform ch05/main.cpp)
target_include_directories(ch05_transform PRIVATE
    ${GLM_INCLUDE_DIR}
    ${COMMON_INCLUDE})
target_link_libraries(ch05_transform PRIVATE stb_image)
link_opengl_libs(ch05_transform)
set_chapter_output(ch05_transform ch05)
copy_shaders("${CMAKE_SOURCE_DIR}/ch05/shaders" ch05)
copy_files_to_build(ch05_transform ch05 container.jpg awesomeface.png)

# ============================================================
# 第6章：摄像机系统
# 着色器为内联 GLSL 字符串，使用 ch06/ 本地版 shader.h
# ============================================================
add_executable(ch06_camera ch06/main.cpp)
target_include_directories(ch06_camera PRIVATE
    ${GLM_INCLUDE_DIR}
    "${CMAKE_SOURCE_DIR}/ch06"   # 覆盖 common/shader.h，使用内联字符串版
    ${COMMON_INCLUDE})
link_opengl_libs(ch06_camera)
set_chapter_output(ch06_camera ch06)

# ============================================================
# 第7章：基础光照
# 运行时着色器：shaders/object.vs|fs, shaders/light.vs|fs
# ============================================================
add_executable(ch07_lighting ch07/main.cpp)
target_include_directories(ch07_lighting PRIVATE
    ${GLM_INCLUDE_DIR}
    ${COMMON_INCLUDE})
link_opengl_libs(ch07_lighting)
set_chapter_output(ch07_lighting ch07)
copy_shaders("${CMAKE_SOURCE_DIR}/ch07/shaders" "ch07/shaders")

# ============================================================
# 第8章：模型加载（需要 Assimp）
# 运行时着色器：shaders/model.vs|fs
# ============================================================
if(assimp_FOUND)
    add_executable(ch08_model ch08/main.cpp)
    target_include_directories(ch08_model PRIVATE
        ${GLM_INCLUDE_DIR}
        ${COMMON_INCLUDE}
        ${ASSIMP_INCLUDE_DIRS})
    target_link_libraries(ch08_model PRIVATE stb_image ${ASSIMP_LIBRARIES})
    link_opengl_libs(ch08_model)
    set_chapter_output(ch08_model ch08)
    copy_shaders("${CMAKE_SOURCE_DIR}/ch08/shaders" "ch08/shaders")
    copy_resources(ch08_model ch08)
    message(STATUS "ch08_model: 已启用")
else()
    message(STATUS "ch08_model: 已跳过（未找到 Assimp）")
endif()

# ============================================================
# 第9章：进阶渲染技术（FBO / 天空盒 / Shadow Map）
# 运行时着色器：shaders/scene|screen|skybox|depth .vs|fs
# ============================================================
add_executable(ch09_advanced ch09/main.cpp)
target_include_directories(ch09_advanced PRIVATE
    ${GLM_INCLUDE_DIR}
    ${COMMON_INCLUDE})
target_link_libraries(ch09_advanced PRIVATE stb_image)
link_opengl_libs(ch09_advanced)
set_chapter_output(ch09_advanced ch09)
copy_shaders("${CMAKE_SOURCE_DIR}/ch09/shaders" "ch09/shaders")
copy_resources(ch09_advanced ch09)

# ============================================================
# 第10章：综合实战项目（需要 Assimp）
# 运行时着色器：shaders/scene|screen|skybox|depth|light .vs|fs
# ============================================================
if(assimp_FOUND)
    add_executable(ch10_demo ch10/main.cpp)
    target_include_directories(ch10_demo PRIVATE
        ${GLM_INCLUDE_DIR}
        ${COMMON_INCLUDE}
        ${ASSIMP_INCLUDE_DIRS})
    target_link_libraries(ch10_demo PRIVATE stb_image ${ASSIMP_LIBRARIES})
    link_opengl_libs(ch10_demo)
    set_chapter_output(ch10_demo ch10)
    copy_shaders("${CMAKE_SOURCE_DIR}/ch10/shaders" "ch10/shaders")
    copy_resources(ch10_demo ch10)
    message(STATUS "ch10_demo: 已启用")
else()
    message(STATUS "ch10_demo: 已跳过（未找到 Assimp）")
endif()

# ============================================================
# 构建汇总
# ============================================================
message(STATUS "")
message(STATUS "=== OpenGL 教程构建配置 ===")
message(STATUS "  构建类型    : ${CMAKE_BUILD_TYPE}")
message(STATUS "  GLM 路径    : ${GLM_INCLUDE_DIR}")
message(STATUS "  STB 路径    : ${STB_INCLUDE}")
message(STATUS "  Assimp 可用 : ${assimp_FOUND}")
message(STATUS "===========================")
