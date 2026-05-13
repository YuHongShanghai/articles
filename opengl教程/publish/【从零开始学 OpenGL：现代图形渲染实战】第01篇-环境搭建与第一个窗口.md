# 第1篇：开发环境搭建与第一个 OpenGL 窗口

## 前置知识

- C/C++ 基础语法
- 基本的命令行操作
- CMake 基本概念（可选，本篇会介绍）

## 本篇目标

**搭建完整的 OpenGL 开发环境，创建一个能响应输入、动态变色的窗口程序。**

---

## 一、OpenGL 是什么

### 1.1 规范而非库

OpenGL（Open Graphics Library）不是一个传统意义上的"库"，它是由 Khronos Group 维护的**图形 API 规范**。规范只定义了函数的名称、参数和行为，具体实现由各 GPU 厂商（NVIDIA、AMD、Intel）在驱动中完成。

这意味着：
- 同一段 OpenGL 代码，在不同 GPU 上可能有细微的行为差异
- OpenGL 函数的地址需要在运行时从驱动中动态获取（这就是 GLAD 的作用）

### 1.2 状态机模型

OpenGL 本质上是一个巨大的**状态机**（通俗地说，就像一个记忆开关面板，你设置的每个状态都会保持，直到你再次修改它）。你通过调用函数来设置各种状态（如当前绑定的纹理、启用的功能、使用的着色器），然后发出绘制命令，OpenGL 会根据当前状态执行渲染。

```cpp
// 设置状态
glBindTexture(GL_TEXTURE_2D, texture);   // 绑定纹理
glUseProgram(shaderProgram);              // 使用着色器
glEnable(GL_DEPTH_TEST);                  // 启用深度测试

// 基于当前状态执行绘制
glDrawArrays(GL_TRIANGLES, 0, 36);
```

### 1.3 与 Vulkan/DirectX 的关系

| 特性 | OpenGL | Vulkan | DirectX 12 |
|------|--------|--------|-----------|
| 抽象层级 | 高（驱动做大量工作） | 低（开发者直接控制） | 低 |
| 学习曲线 | 平缓 | 陡峭 | 陡峭 |
| 跨平台 | 是 | 是 | 仅 Windows |
| 性能上限 | 中 | 高 | 高 |
| 适用场景 | 学习、原型、中小项目 | AAA游戏、高性能渲染 | Windows 游戏 |

> 学习 OpenGL 是理解 GPU 渲染原理的最佳起点，掌握后迁移到 Vulkan 会事半功倍。

---

## 二、软件架构总览

我们的程序涉及以下几层软件栈：

![OpenGL 软件架构](https://gitee.com/yuhong1234/opengl-tutorial-images/raw/main/ch01/opengl_architecture.png)

| 组件 | 作用 | 为什么需要 |
|------|------|-----------|
| **GLFW** | 跨平台窗口和输入管理 | OpenGL 本身不负责创建窗口 |
| **GLAD** | OpenGL 函数加载器 | 运行时动态获取 GPU 驱动中的函数指针 |
| **GLM** | 数学库（后续章节） | 提供向量、矩阵运算 |

---

## 三、环境搭建

### 3.1 安装依赖

**macOS (Homebrew):**
```bash
brew install cmake glfw
```

**Ubuntu/Debian:**
```bash
sudo apt install cmake libglfw3-dev libgl1-mesa-dev
```

**Windows (vcpkg):**
```bash
vcpkg install glfw3
```

### 3.2 获取 GLAD

1. 访问 [GLAD 在线生成器](https://glad.dav1d.de/)
2. 选择：
   - Language: **C/C++**
   - Specification: **OpenGL**
   - API gl: **Version 3.3**
   - Profile: **Core**
3. 点击 Generate，下载压缩包
4. 将 `include/` 和 `src/glad.c` 放入项目的 `third_party/glad/` 目录

### 3.3 项目结构

```
01-HelloWindow/
├── CMakeLists.txt
├── main.cpp
└── third_party/
    └── glad/
        ├── include/
        │   ├── glad/
        │   │   └── glad.h
        │   └── KHR/
        │       └── khrplatform.h
        └── src/
            └── glad.c
```

### 3.4 CMakeLists.txt

```cmake
cmake_minimum_required(VERSION 3.16)
project(01_HelloWindow)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(glfw3 3.3 REQUIRED)
find_package(OpenGL REQUIRED)

add_library(glad STATIC
    ${CMAKE_SOURCE_DIR}/third_party/glad/src/glad.c
)
target_include_directories(glad PUBLIC
    ${CMAKE_SOURCE_DIR}/third_party/glad/include
)

add_executable(${PROJECT_NAME} main.cpp)
target_link_libraries(${PROJECT_NAME} PRIVATE glfw glad OpenGL::GL)
```

---

## 四、核心 API 速查

| 函数 | 所属 | 作用 |
|------|------|------|
| `glfwInit()` | GLFW | 初始化 GLFW 库 |
| `glfwWindowHint()` | GLFW | 设置窗口创建参数 |
| `glfwCreateWindow()` | GLFW | 创建窗口和 OpenGL 上下文 |
| `glfwMakeContextCurrent()` | GLFW | 将上下文设为当前线程的活动上下文 |
| `gladLoadGLLoader()` | GLAD | 加载所有 OpenGL 函数指针 |
| `glViewport()` | OpenGL | 设置渲染视口大小 |
| `glClearColor()` | OpenGL | 设置清屏颜色（状态设置） |
| `glClear()` | OpenGL | 执行清屏 |
| `glfwSwapBuffers()` | GLFW | 交换前后缓冲区（显示画面） |
| `glfwPollEvents()` | GLFW | 处理窗口事件 |

> **什么是上下文（Context）？** 你可以理解为 OpenGL 的工作空间，所有的绑定状态和设置都关联到这个上下文。只有当某个线程拥有一个活动的上下文时，才能调用 OpenGL 函数。

---

## 五、代码实战

### 5.1 完整代码

```cpp
#include <glad/glad.h>
#include <GLFW/glfw3.h>
#include <iostream>
#include <cmath>

// 窗口大小改变时的回调
void framebuffer_size_callback(GLFWwindow* window, int width, int height) {
    glViewport(0, 0, width, height);
}

// 处理键盘输入
void processInput(GLFWwindow* window) {
    if (glfwGetKey(window, GLFW_KEY_ESCAPE) == GLFW_PRESS)
        glfwSetWindowShouldClose(window, true);
}

int main() {
    // ===== 第1步：初始化 GLFW =====
    if (!glfwInit()) {
        std::cerr << "Failed to initialize GLFW" << std::endl;
        return -1;
    }

    // 配置 OpenGL 版本：3.3 Core Profile
    glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 3);
    glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 3);
    glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);
#ifdef __APPLE__
    glfwWindowHint(GLFW_OPENGL_FORWARD_COMPAT, GL_TRUE);
#endif

    // ===== 第2步：创建窗口 =====
    GLFWwindow* window = glfwCreateWindow(800, 600, "OpenGL Tutorial 01", nullptr, nullptr);
    if (!window) {
        std::cerr << "Failed to create GLFW window" << std::endl;
        glfwTerminate();
        return -1;
    }
    glfwMakeContextCurrent(window);
    glfwSetFramebufferSizeCallback(window, framebuffer_size_callback);

    // ===== 第3步：加载 OpenGL 函数 =====
    if (!gladLoadGLLoader((GLADloadproc)glfwGetProcAddress)) {
        std::cerr << "Failed to initialize GLAD" << std::endl;
        return -1;
    }

    // 打印 GPU 信息
    std::cout << "OpenGL Version: " << glGetString(GL_VERSION) << std::endl;
    std::cout << "GLSL Version:   " << glGetString(GL_SHADING_LANGUAGE_VERSION) << std::endl;
    std::cout << "GPU Renderer:   " << glGetString(GL_RENDERER) << std::endl;

    // ===== 第4步：渲染循环 =====
    while (!glfwWindowShouldClose(window)) {
        processInput(window);

        // 用时间驱动背景颜色平滑变化
        float time = (float)glfwGetTime();
        float r = (sin(time * 0.7f) + 1.0f) / 2.0f;
        float g = (sin(time * 1.3f) + 1.0f) / 2.0f;
        float b = (sin(time * 2.0f) + 1.0f) / 2.0f;

        glClearColor(r, g, b, 1.0f);
        glClear(GL_COLOR_BUFFER_BIT);

        glfwSwapBuffers(window);
        glfwPollEvents();
    }

    // ===== 第5步：清理 =====
    glfwTerminate();
    return 0;
}
```

### 5.2 代码详解

**初始化流程：**

1. `glfwInit()` — 初始化 GLFW 库，必须最先调用
2. `glfwWindowHint()` — 告诉 GLFW 我们需要 OpenGL 3.3 Core Profile。Core Profile 会移除所有已废弃的功能，确保我们使用现代 OpenGL
3. `glfwCreateWindow()` — 创建一个 800x600 的窗口，同时创建 OpenGL 上下文
4. `glfwMakeContextCurrent()` — 将该上下文绑定到当前线程。OpenGL 是单线程的，所有调用必须在拥有上下文的线程中
5. `gladLoadGLLoader()` — GLAD 去 GPU 驱动中查找并加载所有 OpenGL 3.3 的函数指针

**渲染循环：**

![渲染循环流程](https://gitee.com/yuhong1234/opengl-tutorial-images/raw/main/ch01/render_loop.png)

每一帧的工作：
1. **处理输入** — 检测按键（ESC 退出）
2. **清屏** — `glClearColor` 设置颜色，`glClear` 执行清除
3. **交换缓冲** — 把后缓冲的内容显示到屏幕

**双缓冲机制：**

![双缓冲机制](https://gitee.com/yuhong1234/opengl-tutorial-images/raw/main/ch01/double_buffer.png)

为什么需要双缓冲？如果直接在显示中的缓冲区上绘制，用户会看到逐步绘制的过程（闪烁）。使用双缓冲，我们在后缓冲区完成所有绘制，然后一次性交换到前台，画面就是流畅的。

### 5.3 构建与运行

```bash
mkdir build && cd build
cmake ..
make
./01_HelloWindow
```

运行后你会看到一个窗口，背景颜色随时间平滑变化。按 ESC 键退出。

---

## 六、常见问题

### Q1: 编译时找不到 GLFW
确保已通过包管理器安装 GLFW，或在 CMake 中正确指定路径：
```bash
cmake .. -DGLFW_DIR=/path/to/glfw
```

### Q2: gladLoadGLLoader 返回失败
99% 是因为在调用 GLAD 之前没有 `glfwMakeContextCurrent()`。GLAD 需要一个有效的 OpenGL 上下文才能加载函数。

### Q3: macOS 上窗口显示白屏
macOS 需要添加 `glfwWindowHint(GLFW_OPENGL_FORWARD_COMPAT, GL_TRUE)`，这是 macOS 对 Core Profile 的额外要求。

### Q4: 窗口大小拖动后画面不正确
确保注册了 `framebuffer_size_callback`，在回调中更新 `glViewport`。

---

## 七、练习

1. **修改窗口标题**：让窗口标题实时显示当前 FPS（提示：用 `glfwSetWindowTitle` + 帧计时）
2. **键盘变色**：按 R/G/B 键分别将背景设为纯红/绿/蓝，按空格恢复动态变色
3. **打印 OpenGL 扩展**：用 `glGetIntegerv(GL_NUM_EXTENSIONS, &n)` 和 `glGetStringi(GL_EXTENSIONS, i)` 列出你的 GPU 支持的所有扩展

---

## 八、参考资料

- [OpenGL 官方规范 (Khronos)](https://www.khronos.org/opengl/)
- [GLFW 官方文档](https://www.glfw.org/documentation.html)
- [GLAD 在线生成器](https://glad.dav1d.de/)
- [LearnOpenGL - Getting Started](https://learnopengl.com/Getting-started/Creating-a-window)

---
