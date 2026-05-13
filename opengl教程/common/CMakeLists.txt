cmake_minimum_required(VERSION 3.10)
project(OpenGLTutorials)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# macOS 上静默 OpenGL 废弃警告
if(APPLE)
    add_compile_definitions(GL_SILENCE_DEPRECATION)
endif()

# 第三方库路径
set(GLAD_DIR "${CMAKE_SOURCE_DIR}/../third_party/glad" CACHE PATH "Path to GLAD")
set(STB_DIR  "${CMAKE_SOURCE_DIR}/../third_party/stb"  CACHE PATH "Path to stb")

# 添加各章节子项目
# 基础章节（无 Assimp 依赖）
add_subdirectory(${CMAKE_SOURCE_DIR}/../01-环境搭建与第一个窗口/src
                 ${CMAKE_BINARY_DIR}/01-window)
add_subdirectory(${CMAKE_SOURCE_DIR}/../02-渲染管线与第一个三角形/src
                 ${CMAKE_BINARY_DIR}/02-triangle)
add_subdirectory(${CMAKE_SOURCE_DIR}/../03-深入着色器与GLSL/src
                 ${CMAKE_BINARY_DIR}/03-shader)
add_subdirectory(${CMAKE_SOURCE_DIR}/../04-纹理映射/src
                 ${CMAKE_BINARY_DIR}/04-texture)
add_subdirectory(${CMAKE_SOURCE_DIR}/../05-坐标系统与3D变换/src
                 ${CMAKE_BINARY_DIR}/05-transform)
add_subdirectory(${CMAKE_SOURCE_DIR}/../06-摄像机系统/src
                 ${CMAKE_BINARY_DIR}/06-camera)
add_subdirectory(${CMAKE_SOURCE_DIR}/../07-基础光照/src
                 ${CMAKE_BINARY_DIR}/07-lighting)

# 进阶章节（需要 Assimp）
add_subdirectory(${CMAKE_SOURCE_DIR}/../08-模型加载/src
                 ${CMAKE_BINARY_DIR}/08-model)
add_subdirectory(${CMAKE_SOURCE_DIR}/../09-进阶渲染技术/src
                 ${CMAKE_BINARY_DIR}/09-advanced)
add_subdirectory(${CMAKE_SOURCE_DIR}/../10-综合实战项目/src
                 ${CMAKE_BINARY_DIR}/10-demo)
