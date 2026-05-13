cmake_minimum_required(VERSION 3.10)
project(ModelLoading)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(glfw3 3.3 REQUIRED)
find_package(OpenGL REQUIRED)
find_package(assimp REQUIRED)

# 查找 GLM
find_path(GLM_INCLUDE_DIR glm/glm.hpp
    HINTS
        /usr/local/include
        /opt/homebrew/include
        /usr/include
)

# GLAD
set(GLAD_DIR "${CMAKE_SOURCE_DIR}/../third_party/glad" CACHE PATH "Path to GLAD")

# stb_image
set(STB_DIR "${CMAKE_SOURCE_DIR}/../third_party/stb" CACHE PATH "Path to stb")

add_executable(${PROJECT_NAME}
    main.cpp
    ${GLAD_DIR}/src/glad.c
)

target_include_directories(${PROJECT_NAME} PRIVATE
    ${GLAD_DIR}/include
    ${GLM_INCLUDE_DIR}
    ${STB_DIR}
    ${ASSIMP_INCLUDE_DIRS}
)

target_link_libraries(${PROJECT_NAME}
    glfw
    OpenGL::GL
    ${ASSIMP_LIBRARIES}
)

if(APPLE)
    target_link_libraries(${PROJECT_NAME}
        "-framework Cocoa"
        "-framework IOKit"
        "-framework CoreVideo"
    )
endif()

# 着色器文件复制到构建目录
file(GLOB SHADER_FILES "${CMAKE_SOURCE_DIR}/shaders/*")
foreach(SHADER ${SHADER_FILES})
    get_filename_component(SHADER_NAME ${SHADER} NAME)
    configure_file(${SHADER} ${CMAKE_BINARY_DIR}/shaders/${SHADER_NAME} COPYONLY)
endforeach()

# 如果有 resources 目录，也复制过去
if(EXISTS "${CMAKE_SOURCE_DIR}/resources")
    file(COPY "${CMAKE_SOURCE_DIR}/resources" DESTINATION "${CMAKE_BINARY_DIR}")
endif()
