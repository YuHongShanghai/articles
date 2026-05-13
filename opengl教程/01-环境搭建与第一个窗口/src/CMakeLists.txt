cmake_minimum_required(VERSION 3.16)
project(01_HelloWindow)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# ---- 依赖查找 ----
find_package(glfw3 3.3 REQUIRED)
find_package(OpenGL REQUIRED)

# ---- GLAD (需要手动添加) ----
add_library(glad STATIC
    ${CMAKE_SOURCE_DIR}/third_party/glad/src/glad.c
)
target_include_directories(glad PUBLIC
    ${CMAKE_SOURCE_DIR}/third_party/glad/include
)

# ---- 可执行文件 ----
add_executable(${PROJECT_NAME} main.cpp)

target_link_libraries(${PROJECT_NAME} PRIVATE
    glfw
    glad
    OpenGL::GL
)
