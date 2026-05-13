cmake_minimum_required(VERSION 3.16)
project(03_Shaders)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(glfw3 3.3 REQUIRED)
find_package(OpenGL REQUIRED)

# GLAD —— 根据实际路径修改
set(GLAD_DIR "${CMAKE_SOURCE_DIR}/../common/third_party/glad"
    CACHE PATH "Path to GLAD directory")

add_library(glad STATIC ${GLAD_DIR}/src/glad.c)
target_include_directories(glad PUBLIC ${GLAD_DIR}/include)

add_executable(${PROJECT_NAME} main.cpp)
target_link_libraries(${PROJECT_NAME} PRIVATE glfw glad OpenGL::GL)

# 将着色器文件复制到构建输出目录
file(GLOB SHADER_FILES "${CMAKE_SOURCE_DIR}/*.glsl")
foreach(SHADER ${SHADER_FILES})
    get_filename_component(SHADER_NAME ${SHADER} NAME)
    configure_file(${SHADER} ${CMAKE_BINARY_DIR}/${SHADER_NAME} COPYONLY)
endforeach()
