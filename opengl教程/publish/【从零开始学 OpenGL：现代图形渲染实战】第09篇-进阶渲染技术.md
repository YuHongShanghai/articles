# 第9篇：进阶渲染技术

## 前置知识

- 第1篇：开发环境搭建与第一个窗口
- 第2篇：渲染管线与第一个三角形
- 第3篇：深入着色器与 GLSL
- 第4篇：纹理映射
- 第5篇：坐标系统与 3D 变换
- 第6篇：摄像机系统
- 第7篇：基础光照
- 第8篇：模型加载
- 理解帧缓冲概念、纹理采样、深度测试

## 本篇目标

**掌握帧缓冲对象（FBO）实现离屏渲染与后处理效果，学会加载天空盒，并实现基础阴影映射。**

完成本篇后，你将拥有一个包含天空盒背景、实时阴影和可切换后处理效果（反相、灰度、锐化、模糊、边缘检测）的渲染场景。

---

## 一、帧缓冲对象（FBO）

### 1.1 什么是帧缓冲

到目前为止，我们所有的绘制操作都直接输出到**默认帧缓冲**（由 GLFW 创建的窗口自带），即屏幕上可见的画面。但 OpenGL 允许我们创建自定义帧缓冲，将渲染结果输出到一张**纹理**上，而非直接显示在屏幕上 —— 这就是**离屏渲染**。

离屏渲染是实现后处理效果的基础：先将场景渲染到纹理上，然后对这张纹理做各种图像处理，最后才输出到屏幕。

### 1.2 帧缓冲的构成

一个完整的帧缓冲需要以下附件：

| 附件类型 | 作用 | 存储格式 |
|---------|------|---------|
| **颜色附件** (Color Attachment) | 存储像素的颜色值 | 纹理 / 渲染缓冲对象 |
| **深度附件** (Depth Attachment) | 存储深度值，用于深度测试 | 纹理 / 渲染缓冲对象 |
| **模板附件** (Stencil Attachment) | 存储模板值 | 纹理 / 渲染缓冲对象 |

> **纹理 vs 渲染缓冲对象（RBO）**：如果后续需要读取附件数据（如采样），使用纹理。如果只需要写入（如深度/模板测试），使用 RBO 更高效。

### 1.3 创建帧缓冲

```cpp
// 1. 创建帧缓冲对象
unsigned int framebuffer;
glGenFramebuffers(1, &framebuffer);
glBindFramebuffer(GL_FRAMEBUFFER, framebuffer);

// 2. 创建颜色附件（纹理）
unsigned int textureColorbuffer;
glGenTextures(1, &textureColorbuffer);
glBindTexture(GL_TEXTURE_2D, textureColorbuffer);
glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB,
             SCR_WIDTH, SCR_HEIGHT, 0,
             GL_RGB, GL_UNSIGNED_BYTE, NULL);  // data 为 NULL
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0,
                       GL_TEXTURE_2D, textureColorbuffer, 0);

// 3. 创建深度+模板附件（RBO）
unsigned int rbo;
glGenRenderbuffers(1, &rbo);
glBindRenderbuffer(GL_RENDERBUFFER, rbo);
glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH24_STENCIL8,
                      SCR_WIDTH, SCR_HEIGHT);
glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_STENCIL_ATTACHMENT,
                          GL_RENDERBUFFER, rbo);

// 4. 检查完整性
if (glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE)
    std::cout << "ERROR: Framebuffer is not complete!" << std::endl;
glBindFramebuffer(GL_FRAMEBUFFER, 0);  // 切回默认帧缓冲
```

注意 `glTexImage2D` 的 `data` 参数为 `NULL` —— 我们只是分配显存空间，纹理内容将在渲染时被填充。

![帧缓冲后处理管线](https://gitee.com/yuhong1234/opengl-tutorial-images/raw/main/ch09/fbo_pipeline.png)

### 1.4 使用帧缓冲的渲染流程

```
Pass 1: 渲染场景到自定义帧缓冲
    glBindFramebuffer(GL_FRAMEBUFFER, framebuffer);
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
    绘制场景...
    glBindFramebuffer(GL_FRAMEBUFFER, 0);

Pass 2: 将帧缓冲纹理绘制到屏幕四边形
    glDisable(GL_DEPTH_TEST);
    screenShader.use();
    glBindTexture(GL_TEXTURE_2D, textureColorbuffer);
    绘制全屏四边形...
    glEnable(GL_DEPTH_TEST);
```

---

## 二、后处理效果

有了帧缓冲，我们可以在片段着色器中对整个画面做图像处理。

### 2.1 屏幕四边形

后处理阶段，我们将帧缓冲的颜色纹理渲染到一个覆盖全屏的四边形上：

```cpp
float quadVertices[] = {
    // positions   // texCoords
    -1.0f,  1.0f,  0.0f, 1.0f,
    -1.0f, -1.0f,  0.0f, 0.0f,
     1.0f, -1.0f,  1.0f, 0.0f,
    -1.0f,  1.0f,  0.0f, 1.0f,
     1.0f, -1.0f,  1.0f, 0.0f,
     1.0f,  1.0f,  1.0f, 1.0f,
};
```

顶点着色器直接传递位置和纹理坐标：

```glsl
#version 330 core
layout (location = 0) in vec2 aPos;
layout (location = 1) in vec2 aTexCoords;

out vec2 TexCoords;

void main()
{
    TexCoords   = aTexCoords;
    gl_Position = vec4(aPos.x, aPos.y, 0.0, 1.0);
}
```

### 2.2 效果实现

**反相（Inversion）：**
```glsl
vec3 result = 1.0 - texture(screenTexture, TexCoords).rgb;
```

**灰度（Grayscale）：**

使用加权平均（考虑人眼对绿色更敏感）：
```glsl
float average = 0.2126 * col.r + 0.7152 * col.g + 0.0722 * col.b;
```

![卷积核效果对比](https://gitee.com/yuhong1234/opengl-tutorial-images/raw/main/ch09/kernel_effects.png)

**核效果（Kernel Effects）：**

核效果在每个像素周围采样 3x3 区域，用一个**卷积核**矩阵加权求和。不同的核产生不同效果：

锐化核：
$$
\begin{bmatrix}
-1 & -1 & -1 \\
-1 & 9 & -1 \\
-1 & -1 & -1
\end{bmatrix}
$$

高斯模糊核：
$$
\frac{1}{16}\begin{bmatrix}
1 & 2 & 1 \\
2 & 4 & 2 \\
1 & 2 & 1
\end{bmatrix}
$$

边缘检测核：
$$
\begin{bmatrix}
1 & 1 & 1 \\
1 & -8 & 1 \\
1 & 1 & 1
\end{bmatrix}
$$

片段着色器中的核效果实现：

```glsl
float offset = 1.0 / 300.0;  // 采样偏移

vec2 offsets[9] = vec2[](
    vec2(-offset,  offset), vec2(0.0,  offset), vec2(offset,  offset),
    vec2(-offset,  0.0),    vec2(0.0,  0.0),    vec2(offset,  0.0),
    vec2(-offset, -offset), vec2(0.0, -offset), vec2(offset, -offset)
);

// 以锐化为例
float kernel[9] = float[](
    -1, -1, -1,
    -1,  9, -1,
    -1, -1, -1
);

vec3 sampleTex[9];
for (int i = 0; i < 9; i++)
    sampleTex[i] = vec3(texture(screenTexture, TexCoords + offsets[i]));

vec3 result = vec3(0.0);
for (int i = 0; i < 9; i++)
    result += sampleTex[i] * kernel[i];
```

在我们的实现中，使用 `effectType` uniform 在运行时切换效果（按数字键 0-5）。

---

## 三、立方体贴图与天空盒

### 3.1 什么是立方体贴图

立方体贴图（Cubemap）是一种特殊纹理，由 6 张图片组成，分别对应立方体的 6 个面。采样时使用一个 **3D 方向向量**而非 2D 坐标。

![立方体贴图](https://gitee.com/yuhong1234/opengl-tutorial-images/raw/main/ch09/cubemap.png)

6 个面的对应关系：

| OpenGL 枚举 | 面 |
|------------|-----|
| `GL_TEXTURE_CUBE_MAP_POSITIVE_X` | 右 |
| `GL_TEXTURE_CUBE_MAP_NEGATIVE_X` | 左 |
| `GL_TEXTURE_CUBE_MAP_POSITIVE_Y` | 上 |
| `GL_TEXTURE_CUBE_MAP_NEGATIVE_Y` | 下 |
| `GL_TEXTURE_CUBE_MAP_POSITIVE_Z` | 前 |
| `GL_TEXTURE_CUBE_MAP_NEGATIVE_Z` | 后 |

### 3.2 加载立方体贴图

```cpp
unsigned int loadCubemap(const std::vector<std::string> &faces)
{
    unsigned int textureID;
    glGenTextures(1, &textureID);
    glBindTexture(GL_TEXTURE_CUBE_MAP, textureID);

    int width, height, nrChannels;
    for (unsigned int i = 0; i < faces.size(); i++)
    {
        unsigned char *data = stbi_load(faces[i].c_str(),
                                        &width, &height, &nrChannels, 0);
        if (data)
        {
            glTexImage2D(GL_TEXTURE_CUBE_MAP_POSITIVE_X + i,
                         0, GL_RGB, width, height,
                         0, GL_RGB, GL_UNSIGNED_BYTE, data);
            stbi_image_free(data);
        }
    }

    glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_WRAP_R, GL_CLAMP_TO_EDGE);

    return textureID;
}
```

注意 `GL_TEXTURE_CUBE_MAP_POSITIVE_X + i` 的技巧：OpenGL 保证这 6 个枚举值是连续的，所以可以直接递增。

### 3.3 天空盒渲染

天空盒就是用一个大立方体包围整个场景，内侧贴上天空纹理。

**关键技巧 1：移除平移分量**

天空盒应该跟随摄像机移动（让人感觉天空无限远），因此需要去掉 View 矩阵中的平移部分：

```cpp
glm::mat4 skyboxView = glm::mat4(glm::mat3(view));  // 只保留旋转
```

**关键技巧 2：深度值优化**

让天空盒始终在最远处（深度值 = 1.0），通过在顶点着色器中设置 `z = w`：

```glsl
void main()
{
    TexCoords = aPos;
    vec4 pos = projection * view * vec4(aPos, 1.0);
    gl_Position = pos.xyww;  // z = w，透视除法后 z/w = 1.0
}
```

然后将深度比较函数改为 `GL_LEQUAL`，并**最后**绘制天空盒：

```cpp
glDepthFunc(GL_LEQUAL);
skyboxShader.use();
// ... 设置 uniform、绘制 ...
glDepthFunc(GL_LESS);  // 恢复默认
```

**片段着色器：**

```glsl
#version 330 core
out vec4 FragColor;
in vec3 TexCoords;

uniform samplerCube skybox;

void main()
{
    FragColor = texture(skybox, TexCoords);
}
```

使用 `samplerCube` 类型采样器和 3D 方向向量进行采样。

---

## 四、基础阴影映射（Shadow Mapping）

### 4.1 Shadow Map 原理

阴影映射是目前实时渲染中最常用的阴影技术，分为两个 Pass：

**Pass 1 — 深度贴图生成**
从**光源视角**渲染整个场景，只记录深度值。这张深度纹理就是 Shadow Map。

**Pass 2 — 阴影判定**
从**摄像机视角**渲染场景时，将每个片段变换到光源空间，与 Shadow Map 中的深度比较：
- 如果片段深度 > Shadow Map 中的深度 → 被遮挡 → **在阴影中**
- 如果片段深度 ≤ Shadow Map 中的深度 → 不被遮挡 → **被照亮**

![Shadow Map 原理](https://gitee.com/yuhong1234/opengl-tutorial-images/raw/main/ch09/shadow_mapping.png)

### 4.2 创建深度贴图 FBO

```cpp
const unsigned int SHADOW_WIDTH  = 1024;
const unsigned int SHADOW_HEIGHT = 1024;

unsigned int depthMapFBO;
glGenFramebuffers(1, &depthMapFBO);

unsigned int depthMap;
glGenTextures(1, &depthMap);
glBindTexture(GL_TEXTURE_2D, depthMap);
glTexImage2D(GL_TEXTURE_2D, 0, GL_DEPTH_COMPONENT,
             SHADOW_WIDTH, SHADOW_HEIGHT, 0,
             GL_DEPTH_COMPONENT, GL_FLOAT, NULL);
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_BORDER);
glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_BORDER);
float borderColor[] = { 1.0, 1.0, 1.0, 1.0 };
glTexParameterfv(GL_TEXTURE_2D, GL_TEXTURE_BORDER_COLOR, borderColor);

glBindFramebuffer(GL_FRAMEBUFFER, depthMapFBO);
glFramebufferTexture2D(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT,
                       GL_TEXTURE_2D, depthMap, 0);
glDrawBuffer(GL_NONE);  // 不需要颜色输出
glReadBuffer(GL_NONE);
glBindFramebuffer(GL_FRAMEBUFFER, 0);
```

关键设置：
- 纹理格式为 `GL_DEPTH_COMPONENT`，只存储深度值
- 使用 `GL_NEAREST` 过滤，因为深度值不应被插值
- `GL_CLAMP_TO_BORDER` + 白色边框：光源范围外的区域视为无阴影
- `glDrawBuffer(GL_NONE)`：告诉 OpenGL 这个 FBO 不输出颜色

### 4.3 光源空间矩阵

对于平行光，使用正交投影：

```cpp
glm::mat4 lightProjection = glm::ortho(-10.0f, 10.0f,
                                        -10.0f, 10.0f,
                                        1.0f, 7.5f);
glm::mat4 lightView = glm::lookAt(lightPos,
                                   glm::vec3(0.0f),
                                   glm::vec3(0.0f, 1.0f, 0.0f));
glm::mat4 lightSpaceMatrix = lightProjection * lightView;
```

### 4.4 深度着色器

这是最简单的着色器 —— 只做变换，片段着色器为空（OpenGL 自动写入深度）：

```glsl
// depth.vs
#version 330 core
layout (location = 0) in vec3 aPos;
uniform mat4 lightSpaceMatrix;
uniform mat4 model;
void main()
{
    gl_Position = lightSpaceMatrix * model * vec4(aPos, 1.0);
}

// depth.fs
#version 330 core
void main() { }
```

### 4.5 阴影计算

在场景着色器的片段着色器中：

```glsl
float ShadowCalculation(vec4 fragPosLightSpace,
                         vec3 normal, vec3 lightDir)
{
    // 透视除法
    vec3 projCoords = fragPosLightSpace.xyz / fragPosLightSpace.w;
    projCoords = projCoords * 0.5 + 0.5;  // 映射到 [0,1]

    // 超出光源视锥的片段不产生阴影
    if (projCoords.z > 1.0)
        return 0.0;

    float currentDepth = projCoords.z;

    // 阴影偏移（Shadow Bias）—— 解决阴影痤疮
    float bias = max(0.05 * (1.0 - dot(normal, lightDir)), 0.005);

    // PCF 软阴影：3x3 区域采样取平均
    float shadow = 0.0;
    vec2 texelSize = 1.0 / textureSize(shadowMap, 0);
    for (int x = -1; x <= 1; ++x)
    {
        for (int y = -1; y <= 1; ++y)
        {
            float pcfDepth = texture(shadowMap,
                projCoords.xy + vec2(x, y) * texelSize).r;
            shadow += currentDepth - bias > pcfDepth ? 1.0 : 0.0;
        }
    }
    shadow /= 9.0;

    return shadow;
}
```

#### Shadow Bias（阴影偏移）

由于深度贴图的分辨率有限，多个片段可能映射到同一个 Shadow Map 纹素，导致**自阴影伪影**（Shadow Acne）—— 表面出现条纹状的明暗交替。

解决方法：给深度值加一个小偏移（bias），让比较更加宽容。偏移量根据表面法线与光线的夹角动态调整：

$$
bias = \max(0.05 \times (1 - \vec{n} \cdot \vec{l}),\ 0.005)
$$

角度越大（光线越倾斜），偏移越大。

#### PCF（Percentage-Closer Filtering）

直接比较会产生硬阴影边缘（锯齿明显）。PCF 通过在目标像素周围多次采样并取平均，产生**软阴影**效果：

```glsl
for (int x = -1; x <= 1; ++x)
    for (int y = -1; y <= 1; ++y)
        // 对 3x3 区域逐个比较并求平均
```

### 4.6 最终光照合成

```glsl
float shadow = ShadowCalculation(FragPosLightSpace, normal, lightDir);
vec3 lighting = (ambient + (1.0 - shadow) * (diffuse + specular)) * color;
```

阴影只影响漫反射和镜面反射分量，环境光保持不变（否则阴影区域会完全漆黑）。

---

## 五、核心 API 速查

| 函数 | 作用 |
|------|------|
| `glGenFramebuffers` | 创建帧缓冲对象 |
| `glBindFramebuffer` | 绑定/切换帧缓冲 |
| `glFramebufferTexture2D` | 将纹理附加到帧缓冲 |
| `glFramebufferRenderbuffer` | 将渲染缓冲对象附加到帧缓冲 |
| `glCheckFramebufferStatus` | 检查帧缓冲完整性 |
| `glGenRenderbuffers` | 创建渲染缓冲对象 |
| `glRenderbufferStorage` | 分配 RBO 存储空间 |
| `glDrawBuffer(GL_NONE)` | 禁用颜色写入 |
| `glReadBuffer(GL_NONE)` | 禁用颜色读取 |
| `GL_TEXTURE_CUBE_MAP` | 立方体贴图纹理目标 |
| `samplerCube` (GLSL) | 立方体贴图采样器 |
| `textureSize` (GLSL) | 获取纹理尺寸（用于 PCF） |

---

## 六、完整代码

[教程完整代码链接](https://download.csdn.net/download/qq_29681777/92731423)

### 6.1 项目结构

```
09-进阶渲染技术/
├── article.md
├── https://gitee.com/yuhong1234/opengl-tutorial-images/raw/main/ch09/
└── src/
    ├── main.cpp
    ├── shader.h
    ├── camera.h
    ├── CMakeLists.txt
    ├── shaders/
    │   ├── scene.vs       ← 场景渲染（带阴影）
    │   ├── scene.fs
    │   ├── screen.vs      ← 后处理
    │   ├── screen.fs
    │   ├── skybox.vs      ← 天空盒
    │   ├── skybox.fs
    │   ├── depth.vs       ← 深度贴图生成
    │   └── depth.fs
    └── resources/
        ├── wood.png       ← 立方体纹理
        ├── floor.png      ← 地面纹理
        └── skybox/        ← 天空盒 6 张图
            ├── right.jpg
            ├── left.jpg
            ├── top.jpg
            ├── bottom.jpg
            ├── front.jpg
            └── back.jpg
```

### 6.2 获取资源文件

**纹理素材：**
- 木板纹理和地面纹理：可从 [textures.com](https://www.textures.com/) 下载免费纹理，或使用任意 PNG/JPG 图片
- 天空盒：推荐从 [learnopengl.com/img/textures/skybox/](https://learnopengl.com/img/textures/skybox/) 下载

**操作说明：**
- WASD 移动，鼠标环视
- 数字键 0-5 切换后处理效果：0=无，1=反相，2=灰度，3=锐化，4=模糊，5=边缘检测

### 6.3 渲染流程总览

整个渲染循环分为三个 Pass：

```
┌─────────────────────────────────────┐
│ Pass 1: 深度贴图                      │
│ 从光源视角渲染 → depthMapFBO          │
│ 着色器: depth.vs + depth.fs          │
├─────────────────────────────────────┤
│ Pass 2: 场景渲染                      │
│ 从摄像机视角渲染 → framebuffer        │
│ 着色器: scene.vs + scene.fs          │
│ 输入: diffuseTexture + shadowMap     │
│ + 天空盒                              │
├─────────────────────────────────────┤
│ Pass 3: 后处理                        │
│ 全屏四边形 → 默认帧缓冲（屏幕）        │
│ 着色器: screen.vs + screen.fs         │
│ 输入: textureColorbuffer              │
└─────────────────────────────────────┘
```

> **完整可编译代码**请参阅 `src/` 目录下的源文件。

---

## 七、常见问题

### Q1：帧缓冲不完整（glCheckFramebufferStatus 失败）

**检查清单：**
- 确保至少附加了一个颜色附件或声明了 `glDrawBuffer(GL_NONE)`
- 所有附件的尺寸必须一致
- 附件的格式必须是有效的

### Q2：后处理效果没有生效

- 确认你在 Pass 1 中绑定了自定义帧缓冲而非默认帧缓冲
- 确认 `screenTexture` uniform 指向了正确的纹理单元
- 确认绘制屏幕四边形时禁用了深度测试

### Q3：阴影有条纹/锯齿（Shadow Acne）

增大 shadow bias。如果 bias 太大会导致"Peter Panning"（阴影与物体脱离），需要在两者之间找平衡：
```glsl
float bias = max(0.05 * (1.0 - dot(normal, lightDir)), 0.005);
```

### Q4：天空盒有接缝

确保 6 张天空盒图片无缝衔接，且使用了 `GL_CLAMP_TO_EDGE` 环绕模式（不是 `GL_REPEAT`）。

### Q5：阴影只在一小块区域有效

调整光源空间的正交投影范围。`glm::ortho` 的参数决定了阴影的覆盖范围。对于大场景需要更大的范围，但会降低阴影精度（Shadow Map 分辨率不变的情况下）。

### Q6：窗口大小改变后后处理失效

帧缓冲的纹理和 RBO 尺寸是在创建时固定的。如果窗口大小改变，需要在 `framebuffer_size_callback` 中重新创建它们。

---

## 八、练习题

### 练习 1：自定义后处理效果

实现一种新的后处理效果 —— 晕影（Vignette）：画面边缘变暗，中心正常。

**提示：** 计算当前像素到屏幕中心的距离，用 `smoothstep` 函数根据距离创建一个渐变遮罩，将原始颜色乘以这个遮罩。

### 练习 2：动态天空盒

让天空盒的颜色随时间从白天过渡到黑夜。可以使用两套天空盒纹理（日/夜），通过 `mix` 函数在着色器中混合。

**提示：** 用 `sin(glfwGetTime() * speed)` 生成一个 0~1 的过渡因子，在两个 `samplerCube` 之间插值。

### 练习 3：提升阴影质量

将 Shadow Map 的分辨率从 1024 提高到 4096，观察阴影质量的变化。然后将 PCF 的采样范围从 3x3 扩大到 5x5，比较效果差异。

**提示：** 修改 `SHADOW_WIDTH/HEIGHT` 常量，以及阴影计算函数中的循环范围（从 -1~1 改为 -2~2，除以 25.0 而非 9.0）。

---

## 九、参考资料

1. [LearnOpenGL - Framebuffers](https://learnopengl.com/Advanced-OpenGL/Framebuffers)
2. [LearnOpenGL - Cubemaps](https://learnopengl.com/Advanced-OpenGL/Cubemaps)
3. [LearnOpenGL - Shadow Mapping](https://learnopengl.com/Advanced-Lighting/Shadows/Shadow-Mapping)
4. [OpenGL Wiki - Framebuffer Object](https://www.khronos.org/opengl/wiki/Framebuffer_Object)
5. [GPU Gems - Shadow Map Antialiasing](https://developer.nvidia.com/gpugems/gpugems/part-ii-lighting-and-shadows)
6. Williams, L. (1978). "Casting curved shadows on curved surfaces". *SIGGRAPH*.

---
