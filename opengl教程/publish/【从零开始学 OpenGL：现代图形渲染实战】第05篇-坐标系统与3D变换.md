# 第5篇：坐标系统与 3D 变换

## 前置知识

- 第1篇：开发环境搭建与第一个窗口
- 第2篇：渲染管线与第一个三角形
- 第3篇：深入着色器与 GLSL
- 第4篇：纹理映射
- 了解基本的线性代数概念（向量、矩阵乘法）

## 本篇目标

**理解从局部空间到屏幕像素的完整坐标变换链，掌握 GLM 数学库进行矩阵运算，实现一个带深度测试的 3D 旋转立方体场景。**

完成本篇后，你将能够：
1. 说出 OpenGL 五大坐标空间及其变换关系
2. 使用 GLM 构建 Model、View、Projection 三大矩阵
3. 理解透视投影与正交投影的区别及适用场景
4. 启用深度测试，正确渲染 3D 场景的遮挡关系

---

## 一、从 2D 到 3D：为什么需要坐标变换

在前四篇中，我们绑定的顶点数据直接就是最终的屏幕坐标（或者说 NDC 坐标，即**标准化设备坐标**——通俗地说，这是一个范围固定在 [-1, 1] 之间的统一坐标系，是 OpenGL 内部使用的标准坐标空间，不管你的显示器多大，这个范围都不变）。这在画三角形和矩形时没问题，但一旦进入 3D 世界，就必须解决三个核心问题：

1. **模型自身的姿态** —— 物体在世界中的位置、朝向、大小
2. **观察者的视角** —— 从哪个角度看这个世界
3. **如何将 3D 投射到 2D 屏幕** —— 透视效果（近大远小）还是等比缩放

OpenGL 用一条 **坐标变换流水线** 来解决这些问题：每个顶点依次经过 5 个坐标空间，最终变成屏幕上的像素。

---

## 二、五大坐标空间

![五大坐标空间变换链](https://gitee.com/yuhong1234/opengl-tutorial-images/raw/main/ch05/coordinate_spaces.png)

一个顶点从定义到最终显示在屏幕上，会依次经过以下五个坐标空间：

### 2.1 局部空间（Local Space / Object Space）

也称为模型空间。这是建模软件导出模型时的坐标系，原点通常在模型中心。比如一个立方体的 8 个顶点坐标范围可能是 `[-0.5, 0.5]`。

我们在代码中直接写的顶点数据就处于局部空间：

```cpp
float vertices[] = {
    -0.5f, -0.5f, -0.5f,  // 顶点 0
     0.5f, -0.5f, -0.5f,  // 顶点 1
     0.5f,  0.5f, -0.5f,  // 顶点 2
    // ...
};
```

### 2.2 世界空间（World Space）

通过 **Model 矩阵** 将局部坐标变换到世界坐标。多个不同的模型共享同一个世界坐标系，这样才能确定它们之间的相对位置关系。

比如，同一个立方体模型实例化 10 次，每次用不同的 Model 矩阵放置到世界中的不同位置：

```cpp
glm::vec3 cubePositions[] = {
    glm::vec3( 0.0f,  0.0f,   0.0f),
    glm::vec3( 2.0f,  5.0f, -15.0f),
    glm::vec3(-1.5f, -2.2f,  -2.5f),
    // ... 更多位置
};
```

### 2.3 观察空间（View Space / Eye Space / Camera Space）

通过 **View 矩阵** 将世界坐标变换到以摄像机为原点的坐标系。这一步的本质是：**移动整个世界，使得摄像机处于原点、朝向 -Z 方向。**

OpenGL 本身没有"摄像机"的概念。我们通过反向移动整个场景来模拟摄像机效果。

### 2.4 裁剪空间（Clip Space）

通过 **Projection 矩阵** 将观察空间坐标变换到裁剪坐标。这一步做了两件事：

1. 定义可见范围（视锥体 / 正交盒）
2. 将 3D 坐标投影到齐次坐标 `(x, y, z, w)`（通俗地说，齐次坐标就是在普通的 (x, y, z) 后面加上第四个分量 w，变成 (x, y, z, w)，这样做的好处是可以用一个矩阵同时表达平移、旋转和缩放变换）

之后 OpenGL 自动执行 **透视除法**（Perspective Division）：将 `(x, y, z)` 各分量除以 `w`，得到 **标准化设备坐标（NDC）**，范围为 `[-1, 1]`。

### 2.5 屏幕空间（Screen Space）

OpenGL 通过 `glViewport` 设定的 **视口变换** 将 NDC 坐标映射到屏幕像素坐标。这一步由 OpenGL 自动完成，不需要我们手动处理。

### 总结：完整变换公式

在顶点着色器中，这条变换链浓缩为一行代码：

```glsl
gl_Position = projection * view * model * vec4(aPos, 1.0);
```

注意矩阵乘法的顺序是 **从右往左** 读的：先 Model → 再 View → 最后 Projection。

---

## 三、三大变换矩阵详解

![Model/View/Projection 矩阵说明](https://gitee.com/yuhong1234/opengl-tutorial-images/raw/main/ch05/mvp_matrices.png)

### 3.1 Model 矩阵 —— 模型变换

Model 矩阵决定了物体在世界空间中的位置、旋转角度和缩放比例。它由三种基本变换组合而成：

#### 平移（Translation）

```cpp
glm::mat4 model = glm::mat4(1.0f);  // 单位矩阵
model = glm::translate(model, glm::vec3(1.0f, 2.0f, -3.0f));
```

对应的 4×4 矩阵形式：

$$
T = \begin{bmatrix}
1 & 0 & 0 & t_x \\
0 & 1 & 0 & t_y \\
0 & 0 & 1 & t_z \\
0 & 0 & 0 & 1
\end{bmatrix}
$$

#### 旋转（Rotation）

```cpp
float angle = glm::radians(45.0f);  // 角度转弧度
model = glm::rotate(model, angle, glm::vec3(0.0f, 1.0f, 0.0f));  // 绕 Y 轴旋转
```

绕任意轴旋转的矩阵比较复杂，GLM 内部使用罗德里格斯旋转公式实现，我们只需指定角度和旋转轴即可。

#### 缩放（Scaling）

```cpp
model = glm::scale(model, glm::vec3(2.0f, 2.0f, 2.0f));  // 各方向放大 2 倍
```

对应矩阵：

$$
S = \begin{bmatrix}
s_x & 0 & 0 & 0 \\
0 & s_y & 0 & 0 \\
0 & 0 & s_z & 0 \\
0 & 0 & 0 & 1
\end{bmatrix}
$$

#### 组合顺序

多个变换的组合顺序非常重要！标准做法是 **先缩放、再旋转、最后平移**（代码中的调用顺序恰好相反，因为矩阵从右往左结合）：

```cpp
glm::mat4 model = glm::mat4(1.0f);
model = glm::translate(model, position);   // 3. 最后平移
model = glm::rotate(model, angle, axis);   // 2. 再旋转
model = glm::scale(model, scaleVec);       // 1. 先缩放
```

### 3.2 View 矩阵 —— 观察变换

View 矩阵将整个世界变换到摄像机的视角。最常用的方式是 `glm::lookAt`：

```cpp
glm::mat4 view = glm::lookAt(
    glm::vec3(0.0f, 0.0f, 3.0f),   // eye:    摄像机位置
    glm::vec3(0.0f, 0.0f, 0.0f),   // center: 看向的目标点
    glm::vec3(0.0f, 1.0f, 0.0f)    // up:     世界空间的"上"方向
);
```

三个参数的含义：

| 参数 | 说明 | 示例 |
|------|------|------|
| `eye` | 摄像机在世界空间中的位置 | `(0, 0, 3)` — 站在 Z 轴正方向 |
| `center` | 摄像机看向的目标点 | `(0, 0, 0)` — 看向原点 |
| `up` | 世界空间的上方向向量 | `(0, 1, 0)` — Y 轴朝上 |

在本篇示例代码中，我们用了一种更简单的方式 —— 直接平移：

```cpp
glm::mat4 view = glm::mat4(1.0f);
view = glm::translate(view, glm::vec3(0.0f, 0.0f, -3.0f));
```

这等价于把整个场景往 -Z 方向移动 3 个单位，效果和摄像机在 `(0, 0, 3)` 处看向原点相同。在下一篇（摄像机系统）中，我们会全面使用 `glm::lookAt`。

### 3.3 Projection 矩阵 —— 投影变换

投影矩阵定义了我们能"看到"的空间范围，并将 3D 坐标投影到 2D。OpenGL 提供两种投影方式：

![透视投影 vs 正交投影](https://gitee.com/yuhong1234/opengl-tutorial-images/raw/main/ch05/perspective_vs_ortho.png)

#### 透视投影（Perspective Projection）

模拟人眼的真实效果 —— **近大远小**。适用于大多数 3D 场景。

```cpp
glm::mat4 projection = glm::perspective(
    glm::radians(45.0f),                    // FOV:  垂直视野角度
    (float)SCR_WIDTH / (float)SCR_HEIGHT,   // 宽高比
    0.1f,                                    // 近平面距离
    100.0f                                   // 远平面距离
);
```

参数说明：

| 参数 | 说明 | 推荐值 |
|------|------|--------|
| `fov` | 垂直方向的视野角度（弧度） | 45° 接近人眼自然视角 |
| `aspect` | 宽高比 = 窗口宽 / 窗口高 | `800.0f / 600.0f` |
| `near` | 近裁剪面距离（> 0） | `0.1f` |
| `far` | 远裁剪面距离 | `100.0f` |

> **注意**：`near` 值不要设置得太小（如 `0.001f`），否则会导致 Z-fighting（深度精度不足，远处物体闪烁）。

#### 正交投影（Orthographic Projection）

没有透视效果，物体不会因距离改变大小。常用于 2D 游戏、UI 渲染、CAD 软件。

```cpp
glm::mat4 projection = glm::ortho(
    -5.0f, 5.0f,    // left, right
    -4.0f, 4.0f,    // bottom, top
     0.1f, 100.0f   // near, far
);
```

#### 透视 vs 正交对比

| 特性 | 透视投影 | 正交投影 |
|------|----------|----------|
| 近大远小 | ✅ 有 | ❌ 无 |
| 可视范围形状 | 截锥体（Frustum） | 长方体（Box） |
| 适用场景 | 3D 游戏、VR | 2D 游戏、UI、工程制图 |
| GLM 函数 | `glm::perspective` | `glm::ortho` |

---

## 四、GLM 数学库速查

GLM（OpenGL Mathematics）是一个 header-only 的 C++ 数学库，API 设计与 GLSL 高度一致。

### 4.1 引入头文件

```cpp
#include <glm/glm.hpp>                // 基础类型：vec2/3/4, mat2/3/4
#include <glm/gtc/matrix_transform.hpp> // 变换函数：translate, rotate, scale, perspective, lookAt
#include <glm/gtc/type_ptr.hpp>        // glm::value_ptr —— 将矩阵转为 float* 传给 OpenGL
```

### 4.2 核心 API 速查表

| 函数 | 签名 | 说明 |
|------|------|------|
| `glm::translate` | `mat4 translate(mat4 m, vec3 v)` | 在矩阵 `m` 基础上附加平移 `v` |
| `glm::rotate` | `mat4 rotate(mat4 m, float angle, vec3 axis)` | 附加绕 `axis` 轴旋转 `angle` 弧度 |
| `glm::scale` | `mat4 scale(mat4 m, vec3 v)` | 附加缩放 `v` |
| `glm::perspective` | `mat4 perspective(float fovy, float aspect, float near, float far)` | 透视投影矩阵 |
| `glm::ortho` | `mat4 ortho(float left, float right, float bottom, float top, float near, float far)` | 正交投影矩阵 |
| `glm::lookAt` | `mat4 lookAt(vec3 eye, vec3 center, vec3 up)` | 观察矩阵 |
| `glm::radians` | `float radians(float degrees)` | 角度 → 弧度 |
| `glm::value_ptr` | `const float* value_ptr(mat4 m)` | 获取矩阵首地址指针 |

### 4.3 将矩阵传递给着色器

```cpp
// 方式 1：使用 Shader 封装类
ourShader.setMat4("model", model);

// 方式 2：直接调用 OpenGL API
unsigned int loc = glGetUniformLocation(shaderID, "model");
glUniformMatrix4fv(loc, 1, GL_FALSE, glm::value_ptr(model));
```

`glUniformMatrix4fv` 的第三个参数 `GL_FALSE` 表示**不需要转置** —— GLM 的矩阵存储方式与 OpenGL 一致（列主序）。

---

## 五、深度测试

当场景中存在多个 3D 物体时，它们在屏幕上会相互遮挡。OpenGL 使用 **深度缓冲（Depth Buffer / Z-Buffer）** 来判断哪些片段应该被绘制、哪些应该被遮挡。

![深度测试原理示意](https://gitee.com/yuhong1234/opengl-tutorial-images/raw/main/ch05/depth_buffer.png)

### 5.1 工作原理

1. 每个像素除了颜色值，还维护一个 **深度值**（范围 `[0.0, 1.0]`，0 最近、1 最远）
2. 初始时所有深度值设为 `1.0`（最远）
3. 每个片段到达时，将其深度与缓冲区中已有的深度比较
4. 如果新片段更近（深度值更小），就更新颜色缓冲和深度缓冲
5. 如果新片段更远，则丢弃该片段

### 5.2 启用深度测试

只需两步：

```cpp
// 第一步：启用深度测试（在渲染循环之前）
glEnable(GL_DEPTH_TEST);

// 第二步：每帧清除深度缓冲（在渲染循环中）
glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
```

> **重要**：如果忘记 `glEnable(GL_DEPTH_TEST)`，后绘制的物体会始终覆盖先绘制的物体，无论远近。如果忘记清除深度缓冲，上一帧的深度信息会残留，导致渲染异常。

### 5.3 深度测试函数

默认的比较函数是 `GL_LESS`（新片段深度 < 缓冲区深度时通过），你也可以修改：

```cpp
glDepthFunc(GL_LESS);     // 默认值：更近的通过
glDepthFunc(GL_LEQUAL);   // 小于等于时通过（天空盒常用）
glDepthFunc(GL_ALWAYS);   // 总是通过（禁用深度测试的效果）
```

---

## 六、顶点着色器

在顶点着色器中完成 MVP 变换：

```glsl
#version 330 core
layout (location = 0) in vec3 aPos;
layout (location = 1) in vec2 aTexCoord;

out vec2 TexCoord;

uniform mat4 model;
uniform mat4 view;
uniform mat4 projection;

void main()
{
    gl_Position = projection * view * model * vec4(aPos, 1.0);
    TexCoord = aTexCoord;
}
```

关键点：
- 三个 `uniform mat4` 分别接收从 CPU 端传入的 Model、View、Projection 矩阵
- `vec4(aPos, 1.0)` 将 3D 坐标扩展为齐次坐标（`w=1.0` 表示这是一个点，而非方向）
- 矩阵乘法顺序：`projection * view * model * vertex`，从右往左依次变换

片段着色器和前一篇一样，做纹理混合：

```glsl
#version 330 core
out vec4 FragColor;

in vec2 TexCoord;

uniform sampler2D texture1;
uniform sampler2D texture2;

void main()
{
    FragColor = mix(texture(texture1, TexCoord), texture(texture2, TexCoord), 0.3);
}
```

---

## 七、完整代码解析

[教程完整代码链接](https://download.csdn.net/download/qq_29681777/92731423)

以下对 `src/main.cpp` 中的核心逻辑进行逐段解析。

### 7.1 头文件与 GLM 引入

```cpp
#include <glad/glad.h>
#include <GLFW/glfw3.h>

#include <glm/glm.hpp>
#include <glm/gtc/matrix_transform.hpp>
#include <glm/gtc/type_ptr.hpp>

#define STB_IMAGE_IMPLEMENTATION
#include "stb_image.h"
#include "shader.h"
```

相比前几篇，新增了三个 GLM 头文件。`matrix_transform.hpp` 提供所有变换函数，`type_ptr.hpp` 用于矩阵指针转换（在 `Shader::setMat4` 中使用）。

### 7.2 立方体顶点数据

```cpp
float vertices[] = {
    // positions          // tex coords
    -0.5f, -0.5f, -0.5f,  0.0f, 0.0f,
     0.5f, -0.5f, -0.5f,  1.0f, 0.0f,
     0.5f,  0.5f, -0.5f,  1.0f, 1.0f,
    // ... 共 36 个顶点（6 个面 × 每面 2 个三角形 × 3 个顶点）
};
```

立方体有 6 个面，每个面由 2 个三角形组成，所以需要 36 个顶点。每个顶点包含 5 个浮点数：3 个位置分量 + 2 个纹理坐标。这些坐标都处于 **局部空间**。

### 7.3 10 个立方体的世界位置

```cpp
glm::vec3 cubePositions[] = {
    glm::vec3( 0.0f,  0.0f,   0.0f),
    glm::vec3( 2.0f,  5.0f, -15.0f),
    glm::vec3(-1.5f, -2.2f,  -2.5f),
    glm::vec3(-3.8f, -2.0f, -12.3f),
    glm::vec3( 2.4f, -0.4f,  -3.5f),
    glm::vec3(-1.7f,  3.0f,  -7.5f),
    glm::vec3( 1.3f, -2.0f,  -2.5f),
    glm::vec3( 1.5f,  2.0f,  -2.5f),
    glm::vec3( 1.5f,  0.2f,  -1.5f),
    glm::vec3(-1.3f,  1.0f,  -1.5f)
};
```

同一份顶点数据被复用 10 次，每个立方体通过不同的 Model 矩阵放置到世界空间的不同位置。

### 7.4 启用深度测试

```cpp
glEnable(GL_DEPTH_TEST);
```

在创建窗口、加载 GLAD 之后，渲染循环之前启用。

### 7.5 渲染循环中的 MVP 矩阵设置

```cpp
// 每帧清除颜色缓冲和深度缓冲
glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

// ===== View 矩阵 =====
glm::mat4 view = glm::mat4(1.0f);
view = glm::translate(view, glm::vec3(0.0f, 0.0f, -3.0f));

// ===== Projection 矩阵 =====
glm::mat4 projection = glm::perspective(
    glm::radians(45.0f),                       // 45° FOV
    (float)SCR_WIDTH / (float)SCR_HEIGHT,       // 宽高比
    0.1f,                                        // 近平面
    100.0f                                       // 远平面
);

ourShader.setMat4("view", view);
ourShader.setMat4("projection", projection);
```

View 和 Projection 矩阵每帧只需设置一次（它们不随物体变化）。

### 7.6 绘制 10 个立方体

```cpp
for (unsigned int i = 0; i < 10; i++)
{
    glm::mat4 model = glm::mat4(1.0f);
    model = glm::translate(model, cubePositions[i]);

    float angle = 20.0f * i;
    if (i % 3 == 0)
        angle = (float)glfwGetTime() * 25.0f * (i + 1);

    model = glm::rotate(model, glm::radians(angle),
                        glm::vec3(1.0f, 0.3f, 0.5f));

    ourShader.setMat4("model", model);

    glDrawArrays(GL_TRIANGLES, 0, 36);
}
```

逻辑拆解：
1. 为每个立方体创建独立的 Model 矩阵（从单位矩阵开始）
2. 先平移到对应的世界位置
3. 计算旋转角度 —— 索引是 3 的倍数的立方体会随时间旋转（产生动画效果）
4. 绕 `(1.0, 0.3, 0.5)` 轴旋转（一个任意的非轴对齐方向，让旋转看起来更自然）
5. 将 Model 矩阵传入着色器，绘制 36 个顶点

### 7.7 Shader 类的 setMat4

```cpp
void setMat4(const std::string &name, const glm::mat4 &mat) const
{
    glUniformMatrix4fv(glGetUniformLocation(ID, name.c_str()),
                       1, GL_FALSE, &mat[0][0]);
}
```

`&mat[0][0]` 获取矩阵第一个元素的地址，效果与 `glm::value_ptr(mat)` 相同。

---

## 八、CMake 配置要点

```cmake
# 查找 GLM 头文件路径
find_path(GLM_INCLUDE_DIR glm/glm.hpp
    HINTS
        /usr/local/include
        /opt/homebrew/include   # macOS Homebrew (Apple Silicon)
        /usr/include
)

target_include_directories(${PROJECT_NAME} PRIVATE
    ${GLAD_DIR}/include
    ${GLM_INCLUDE_DIR}         # GLM 是 header-only，只需 include 路径
    ${STB_DIR}
)
```

GLM 是纯头文件库，不需要链接任何 `.lib` / `.a` 文件，只需将其 include 目录加入搜索路径。

---

## 九、核心 API 速查表

| API | 说明 |
|-----|------|
| `glEnable(GL_DEPTH_TEST)` | 启用深度测试 |
| `glDepthFunc(func)` | 设置深度比较函数（默认 `GL_LESS`） |
| `glClear(GL_DEPTH_BUFFER_BIT)` | 清除深度缓冲 |
| `glDepthMask(GL_FALSE)` | 禁止写入深度缓冲（只读） |
| `glViewport(x, y, w, h)` | 设置视口（NDC → 屏幕的映射） |
| `glUniformMatrix4fv(loc, 1, GL_FALSE, ptr)` | 传递 4×4 矩阵给着色器 |
| `glm::mat4(1.0f)` | 创建 4×4 单位矩阵 |
| `glm::translate(m, vec3)` | 平移变换 |
| `glm::rotate(m, radians, axis)` | 旋转变换 |
| `glm::scale(m, vec3)` | 缩放变换 |
| `glm::perspective(fov, aspect, near, far)` | 透视投影 |
| `glm::ortho(l, r, b, t, n, f)` | 正交投影 |
| `glm::lookAt(eye, center, up)` | 观察矩阵 |

---

## 十、常见问题

### Q1：为什么我的立方体看起来是"穿模"的，面的前后关系不对？

**A**：忘记启用深度测试。请确保调用了 `glEnable(GL_DEPTH_TEST)`，并且每帧渲染前用 `glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)` 同时清除颜色和深度缓冲。

### Q2：矩阵变换的顺序为什么如此重要？

**A**：矩阵乘法不满足交换律。`glm::translate(model, pos)` 本质上是 `model = model * T`，后调用的变换会先作用于顶点。所以代码中的 `translate → rotate → scale` 调用顺序，实际上对顶点的作用顺序是 `scale → rotate → translate`，即先缩放、再旋转、最后平移。如果先平移再旋转，物体会绕世界原点旋转而非自身中心。

### Q3：`near` 平面设为 0 行不行？

**A**：绝对不行。透视投影矩阵中 `near` 出现在分母中，设为 0 会导致除零错误。即使设为极小值（如 `0.0001f`），也会严重损害深度缓冲的精度，导致远处物体出现 Z-fighting（深度冲突闪烁）。推荐 `near = 0.1f`。

### Q4：`glm::radians` 是做什么的？为什么不直接写角度值？

**A**：GLM 的所有三角函数和旋转函数都使用 **弧度** 而非角度。`glm::radians(45.0f)` 将 45 度转换为约 `0.785` 弧度。直接传入 `45.0f` 会被当作 45 弧度（约 2578 度），结果完全错误。

### Q5：为什么用 `vec4(aPos, 1.0)` 而不是 `vec4(aPos, 0.0)`？

**A**：齐次坐标的第四个分量 `w` 用于区分**点**和**方向**：
- `w = 1.0`：表示一个**位置点**，平移操作会生效
- `w = 0.0`：表示一个**方向向量**，平移操作被忽略（只有旋转和缩放生效）

顶点坐标是位置，所以必须用 `w = 1.0`。

---

## 十一、练习题

### 练习 1：使用 glm::lookAt

将当前的 View 矩阵替换为 `glm::lookAt`，让摄像机位于 `(3.0, 2.0, 5.0)`，看向原点 `(0, 0, 0)`，上方向为 `(0, 1, 0)`。观察画面变化。

```cpp
glm::mat4 view = glm::lookAt(
    glm::vec3(3.0f, 2.0f, 5.0f),
    glm::vec3(0.0f, 0.0f, 0.0f),
    glm::vec3(0.0f, 1.0f, 0.0f)
);
```

### 练习 2：正交投影

将透视投影替换为正交投影，比较两种投影的视觉差异：

```cpp
glm::mat4 projection = glm::ortho(-5.0f, 5.0f, -4.0f, 4.0f, 0.1f, 100.0f);
```

注意观察：在正交投影下，立方体的远近面大小完全相同，没有"近大远小"的效果。

### 练习 3：让所有立方体都旋转起来

修改渲染循环中的旋转逻辑，让所有 10 个立方体都随时间旋转，每个立方体绕不同的轴、以不同的速度旋转：

```cpp
for (unsigned int i = 0; i < 10; i++)
{
    glm::mat4 model = glm::mat4(1.0f);
    model = glm::translate(model, cubePositions[i]);

    float angle = (float)glfwGetTime() * glm::radians(20.0f * (i + 1));
    model = glm::rotate(model, angle,
                        glm::vec3(sin(i * 1.0f), cos(i * 0.7f), sin(i * 1.3f)));

    ourShader.setMat4("model", model);
    glDrawArrays(GL_TRIANGLES, 0, 36);
}
```

---

## 十二、参考资料

1. [Learn OpenGL - Coordinate Systems](https://learnopengl.com/Getting-started/Coordinate-Systems)
2. [GLM 官方文档](https://github.com/g-truc/glm)
3. [OpenGL Wiki - Depth Buffer](https://www.khronos.org/opengl/wiki/Depth_Buffer)
4. [Songho - OpenGL Projection Matrix](http://www.songho.ca/opengl/gl_projectionmatrix.html)
5. [3Blue1Brown - 线性代数的本质](https://www.bilibili.com/video/BV1ys411472E) — 直观理解矩阵变换的绝佳视频

---
