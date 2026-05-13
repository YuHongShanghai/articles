cmake_minimum_required(VERSION 3.16)
project(04_Textures)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(glfw3 3.3 REQUIRED)
find_package(OpenGL REQUIRED)

# GLAD
set(GLAD_DIR "${CMAKE_SOURCE_DIR}/../common/third_party/glad"
    CACHE PATH "Path to GLAD directory")

add_library(glad STATIC ${GLAD_DIR}/src/glad.c)
target_include_directories(glad PUBLIC ${GLAD_DIR}/include)

# stb_image
set(STB_DIR "${CMAKE_SOURCE_DIR}/../common/third_party/stb"
    CACHE PATH "Path to stb directory")

add_executable(${PROJECT_NAME} main.cpp)
target_include_directories(${PROJECT_NAME} PRIVATE ${STB_DIR})
target_link_libraries(${PROJECT_NAME} PRIVATE glfw glad OpenGL::GL)

# 复制着色器文件到构建输出目录
file(GLOB SHADER_FILES "${CMAKE_SOURCE_DIR}/*.vs" "${CMAKE_SOURCE_DIR}/*.fs")
foreach(SHADER ${SHADER_FILES})
    get_filename_component(SHADER_NAME ${SHADER} NAME)
    configure_file(${SHADER} ${CMAKE_BINARY_DIR}/${SHADER_NAME} COPYONLY)
endforeach()

# 复制纹理资源到构建输出目录
file(GLOB TEXTURE_FILES "${CMAKE_SOURCE_DIR}/textures/*")
foreach(TEX ${TEXTURE_FILES})
    get_filename_component(TEX_NAME ${TEX} NAME)
    configure_file(${TEX} ${CMAKE_BINARY_DIR}/textures/${TEX_NAME} COPYONLY)
endforeach()
