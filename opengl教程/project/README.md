# OpenGL 实战入门教程 — 统一项目

本目录将 10 篇教程的所有代码整合为一个 CMake 项目，一次配置即可编译所有章节的可执行文件。

## 项目结构

```
project/
├── CMakeLists.txt          ← 顶层构建文件（管理全部章节）
├── README.md
├── common/                 ← 公共工具类（各章节共用）
│   ├── shader.h            ← 文件路径版着色器类（ch03-ch05, ch07-ch10）
│   ├── camera.h            ← 摄像机类（ch06-ch10）
│   ├── mesh.h              ← 网格类，含 DrawDepthOnly()（ch08, ch10）
│   └── model.h             ← 模型加载类，基于 Assimp（ch08, ch10）
├── third_party/            ← 手动放置的第三方库
│   ├── glad/
│   │   ├── include/
│   │   │   ├── glad/glad.h
│   │   │   └── KHR/khrplatform.h
│   │   └── src/glad.c
│   └── stb/
│       └── stb_image.h
├── ch01/  main.cpp                         第1章：窗口
├── ch02/  main.cpp                         第2章：三角形
├── ch03/  main.cpp  shaders/               第3章：着色器
├── ch04/  main.cpp  shaders/               第4章：纹理
├── ch05/  main.cpp  shaders/               第5章：3D变换
├── ch06/  main.cpp  shader.h               第6章：摄像机（内联 GLSL）
├── ch07/  main.cpp  shaders/               第7章：光照
├── ch08/  main.cpp  shaders/               第8章：模型加载（需 Assimp）
├── ch09/  main.cpp  shaders/               第9章：进阶渲染
└── ch10/  main.cpp  shaders/               第10章：综合实战（需 Assimp）
```

> **ch06** 使用内联 GLSL 字符串版 `shader.h`（与其他章节不同），因此该文件保留在 `ch06/` 目录下。

---

## 环境准备

### 1. 安装系统依赖

**macOS (Homebrew)**
```bash
brew install cmake glfw glm assimp
```

**Ubuntu / Debian**
```bash
sudo apt update
sudo apt install cmake libglfw3-dev libgl1-mesa-dev libglm-dev libassimp-dev
```

**Windows (vcpkg)**
```bash
vcpkg install glfw3 glm assimp
```

### 2. GLAD 与 stb_image（自动获取）

CMakeLists.txt 会在 cmake 配置阶段**自动处理** GLAD 和 stb_image：

- 如果 `third_party/glad/src/glad.c` 已存在 → 使用本地文件
- 否则 → 通过 `FetchContent` 从 GitHub 自动下载 glad v2.x

- 如果 `third_party/stb/stb_image.h` 已存在 → 使用本地文件  
- 否则 → 通过 `FetchContent` 从 GitHub 自动下载 stb

**首次 cmake 时需要联网**（仅第一次，之后使用缓存）。

#### 可选：手动放置以离线构建

如需离线构建，可手动提前下载并放置：

| 库 | 下载地址 | 放置位置 |
|----|---------|---------|
| GLAD | [glad.dav1d.de](https://glad.dav1d.de/)（OpenGL 3.3 Core） | `third_party/glad/` |
| stb_image | [github.com/nothings/stb](https://github.com/nothings/stb) | `third_party/stb/stb_image.h` |

---

## 构建

```bash
cd project
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)          # Linux/macOS
# 或
cmake --build . --config Release -j4   # 跨平台
```

构建完成后，每个章节的可执行文件位于各自的子目录中：

```
build/
├── ch01/ch01_window
├── ch02/ch02_triangle
├── ch03/ch03_shader      + shaders/
├── ch04/ch04_texture     + shaders/
├── ch05/ch05_transform   + shaders/
├── ch06/ch06_camera
├── ch07/ch07_lighting    + shaders/
├── ch08/ch08_model       + shaders/   （需要 Assimp）
├── ch09/ch09_advanced    + shaders/
└── ch10/ch10_demo        + shaders/   （需要 Assimp）
```

---

## 运行

每个可执行文件需要在其所在子目录中运行（以保证着色器和资源的相对路径正确）：

```bash
cd build/ch03
./ch03_shader

cd build/ch07
./ch07_lighting

cd build/ch09
./ch09_advanced
```

### 第8、10章的模型资源

ch08 和 ch10 需要额外的模型和纹理文件，运行前请将资源目录放到对应 build 子目录下：

**背包模型**（ch08、ch10 均需要）：
```bash
# 下载：https://learnopengl.com/data/models/backpack.zip
# 解压后放到：
build/ch08/resources/backpack/
build/ch10/resources/backpack/
```

**天空盒纹理**（ch09、ch10 需要）：
```bash
# 从 LearnOpenGL 下载天空盒纹理，放到：
build/ch09/resources/skybox/
build/ch10/resources/skybox/
```

**地面纹理**（ch09、ch10 需要）：
```bash
# 任意地砖 PNG/JPG 图片，命名为 floor.png
build/ch09/resources/floor.png
build/ch10/resources/floor.png
```

---

## 编译单个章节

如果只想构建某一章节：

```bash
cd build
cmake --build . --target ch07_lighting
```

---

## 各章节可执行文件说明

| 目标名 | 章节 | 操作说明 |
|--------|------|---------|
| `ch01_window` | 环境搭建 | 窗口显示，ESC 退出 |
| `ch02_triangle` | 渲染管线 | 彩色三角形 |
| `ch03_shader` | GLSL 着色器 | 随时间变色三角形 |
| `ch04_texture` | 纹理映射 | 双纹理矩形，↑↓调节混合比例 |
| `ch05_transform` | 3D 变换 | 旋转纹理立方体 |
| `ch06_camera` | 摄像机 | WASD移动，鼠标环视，滚轮缩放 |
| `ch07_lighting` | 基础光照 | 多光源 Phong 着色场景 |
| `ch08_model` | 模型加载 | 渲染背包模型 |
| `ch09_advanced` | 进阶渲染 | 天空盒+阴影，0-5键切换后处理 |
| `ch10_demo` | 综合实战 | 完整3D场景，F键手电筒，0-5键后处理 |

---

## 设计说明

### 着色器文件位置规则

各章节在 main.cpp 中引用着色器的路径规则不同，CMake 会自动将着色器复制到对应位置：

| 章节 | 着色器引用方式 | 复制位置 |
|------|-------------|---------|
| ch03 | `"vertex.glsl"` | `build/ch03/` |
| ch04 | `"texture.vs"` | `build/ch04/` |
| ch05 | `"cube.vs"` | `build/ch05/` |
| ch07-ch10 | `"shaders/xxx.vs"` | `build/chXX/shaders/` |

### STB_IMAGE_IMPLEMENTATION 处理

`stb_image.h` 要求在整个程序中只有一个编译单元定义 `STB_IMAGE_IMPLEMENTATION`。本项目在各章节的 `main.cpp` 中定义该宏，`common/model.h` 中只包含 `#include "stb_image.h"`（不定义宏）。

### common/model.h 的 TextureFromFile

该函数声明为 `inline` 以避免多翻译单元链接时的重复定义错误。

### ch06 的 shader.h

第6章使用**内联 GLSL 字符串**作为着色器源码（`Shader(const char* src, const char* src)`），与其他章节的文件路径版本不同。CMake 将 `ch06/` 目录优先放在 include 路径中，使 `ch06/main.cpp` 中的 `#include "shader.h"` 能找到本地版本。
