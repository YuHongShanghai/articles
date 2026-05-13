# OpenGL 实战入门教程 — 环境依赖总览

## 技术栈

| 组件 | 版本要求 | 作用 |
|------|---------|------|
| OpenGL | 3.3+ Core Profile | 图形渲染 API |
| C++ | C++17 | 编程语言 |
| CMake | 3.10+ | 跨平台构建系统 |
| GLFW | 3.3+ | 窗口管理与输入处理 |
| GLAD | OpenGL 3.3 Core | OpenGL 函数加载器 |
| GLM | 0.9.9+ | 数学库（向量、矩阵运算） |
| stb_image | — | 图片加载（header-only） |
| Assimp | 5.0+ | 3D 模型导入（第8篇起） |

## 安装依赖

### macOS (Homebrew)

```bash
brew install cmake glfw glm assimp
```

### Ubuntu / Debian

```bash
sudo apt update
sudo apt install cmake libglfw3-dev libgl1-mesa-dev libglm-dev libassimp-dev
```

### Windows (vcpkg)

```bash
vcpkg install glfw3 glm assimp
```

或使用 MSYS2：
```bash
pacman -S mingw-w64-x86_64-cmake mingw-w64-x86_64-glfw mingw-w64-x86_64-glm mingw-w64-x86_64-assimp
```

## GLAD 配置

GLAD 不通过包管理器安装，需要手动获取：

1. 访问 [GLAD 在线生成器](https://glad.dav1d.de/)
2. 选择：
   - Language: C/C++
   - Specification: OpenGL
   - API gl: Version 3.3
   - Profile: Core
3. 点击 "Generate"，下载压缩包
4. 将生成的文件放置到项目中（参见下方目录结构）

## stb_image 配置

1. 从 [stb GitHub](https://github.com/nothings/stb) 下载 `stb_image.h`
2. 放置到 `third_party/stb/` 目录下

## 推荐项目目录结构

```
opengl教程/
├── third_party/          ← 第三方库（所有章节共用）
│   ├── glad/
│   │   ├── include/
│   │   │   ├── glad/
│   │   │   │   └── glad.h
│   │   │   └── KHR/
│   │   │       └── khrplatform.h
│   │   └── src/
│   │       └── glad.c
│   └── stb/
│       └── stb_image.h
├── 01-环境搭建与第一个窗口/
│   ├── article.md
│   └── src/
├── 02-渲染管线与第一个三角形/
│   ├── article.md
│   └── src/
├── ...
├── 10-综合实战项目/
│   ├── article.md
│   └── src/
└── common/
    ├── README.md          ← 本文件
    └── CMakeLists.txt     ← 顶层 CMake（可选）
```

## 构建单个章节

每个章节的 `src/` 目录都包含独立的 `CMakeLists.txt`，可以单独构建：

```bash
cd 01-环境搭建与第一个窗口/src
mkdir build && cd build
cmake ..
make        # Linux/macOS
# 或
cmake --build .   # 跨平台
./项目名
```

## 构建所有章节

使用顶层 `CMakeLists.txt` 一次性构建：

```bash
cd opengl教程/common
mkdir build && cd build
cmake ..
make
```

## 常见问题

### CMake 找不到 GLFW

确认 GLFW 已安装，或手动指定路径：
```bash
cmake .. -Dglfw3_DIR=/path/to/glfw/lib/cmake/glfw3
```

### CMake 找不到 GLM

GLM 是 header-only 库，可以手动指定包含路径：
```bash
cmake .. -DGLM_INCLUDE_DIR=/path/to/glm
```

### macOS 上出现 OpenGL 废弃警告

macOS 从 10.14 起将 OpenGL 标记为废弃（deprecated）。这只是编译警告，不影响功能。可以添加编译选项忽略：
```cmake
add_compile_definitions(GL_SILENCE_DEPRECATION)
```

### GLAD 链接错误

确保：
1. `glad.c` 被添加到了 CMake 的源文件列表中
2. `glad/include` 目录在 include 路径中
3. 每个可执行文件只编译一次 `glad.c`

### Assimp 运行时找不到模型文件

检查可执行文件的工作目录。CMake 构建后，着色器和资源文件可能需要复制到 build 目录（参见各章节的 CMakeLists.txt 中的文件复制配置）。

## 学习路线建议

按顺序阅读每篇教程。每篇包含完整可运行的代码，建议亲手编写（而非直接复制），在编码过程中加深理解。

| 阶段 | 章节 | 重点 |
|------|------|------|
| 基础 | 第1-3篇 | 理解渲染管线、GLSL、着色器 |
| 进阶 | 第4-6篇 | 纹理、3D变换、摄像机 |
| 光照 | 第7-8篇 | Phong 光照、模型加载 |
| 高级 | 第9-10篇 | FBO、阴影、天空盒、综合项目 |
