# 第10篇：综合实战 — 构建一个完整的 3D 场景

## 前置知识

- 第1篇：开发环境搭建与第一个窗口
- 第2篇：渲染管线与第一个三角形
- 第3篇：深入着色器与 GLSL
- 第4篇：纹理映射
- 第5篇：坐标系统与 3D 变换
- 第6篇：摄像机系统
- 第7篇：基础光照
- 第8篇：模型加载
- 第9篇：进阶渲染技术
- 理解前9篇的所有内容

## 本篇目标

**整合前9篇所有知识，从零构建一个完整的、可交互的 3D 渲染场景，包含模型加载、多光源照明、实时阴影、天空盒和可切换的后处理效果。**

完成本篇后，你将拥有一个"迷你引擎"级别的 3D 渲染 Demo，能够自由漫游、切换光源和后处理效果，并对整个 OpenGL 渲染管线有深入的实践理解。

---

## 一、项目总览

### 1.1 最终效果

我们要构建的场景包含以下要素：

| 要素 | 技术来源 |
|------|---------|
| 地面平面 + 3D 背包模型 × 3 | 第2篇 + 第8篇 |
| 太阳光（平行光）+ 4 个彩色点光源 + 手电筒 | 第7篇 |
| 实时阴影（Shadow Map + PCF） | 第9篇 |
| 天空盒 | 第9篇 |
| 后处理效果（反相/灰度/锐化/模糊/边缘检测） | 第9篇 |
| FPS 风格自由摄像机 | 第6篇 |
| 面剔除优化 | 本篇 |

### 1.2 操作方式

| 按键 | 功能 |
|------|------|
| W/A/S/D | 前后左右移动 |
| 鼠标 | 视角环视 |
| 滚轮 | FOV 缩放 |
| F | 开关手电筒 |
| 0-5 | 切换后处理效果 |
| ESC | 退出 |

---

## 二、项目架构设计

### 2.1 代码组织

```
10-综合实战项目/
├── article.md
├── https://gitee.com/yuhong1234/opengl-tutorial-images/raw/main/ch10/
└── src/
    ├── main.cpp         ← 主程序：初始化、渲染循环、输入处理
    ├── shader.h         ← 着色器工具类（第3篇封装）
    ├── camera.h         ← 摄像机类（第6篇封装）
    ├── mesh.h           ← 网格类（第8篇封装）
    ├── model.h          ← 模型类（第8篇封装）
    ├── CMakeLists.txt
    ├── shaders/
    │   ├── scene.vs/fs  ← 场景着色器（多光源 + 阴影 + 纹理）
    │   ├── depth.vs/fs  ← 深度贴图着色器
    │   ├── skybox.vs/fs ← 天空盒着色器
    │   ├── screen.vs/fs ← 后处理着色器
    │   └── light.vs/fs  ← 光源立方体着色器
    └── resources/
        ├── floor.png
        ├── backpack/
        └── skybox/
```

### 2.2 渲染管线概览

整个渲染循环分为三个 Pass：

```
┌──────────────────────────────────────────────┐
│ Pass 1 — Shadow Map (深度贴图)                │
│ 视角：光源                                     │
│ 目标：depthFBO                                │
│ 着色器：depth.vs + depth.fs                   │
│ 输出：depthMap (阴影深度纹理)                   │
├──────────────────────────────────────────────┤
│ Pass 2 — Scene Rendering (场景渲染)           │
│ 视角：摄像机                                   │
│ 目标：自定义 FBO (后处理用)                     │
│ 着色器：scene.vs + scene.fs                   │
│         skybox.vs + skybox.fs                 │
│         light.vs + light.fs                   │
│ 输入：diffuseTexture, shadowMap               │
│ 输出：colorTexture (颜色附件)                  │
├──────────────────────────────────────────────┤
│ Pass 3 — Post-Processing (后处理)             │
│ 目标：默认帧缓冲（屏幕）                       │
│ 着色器：screen.vs + screen.fs                 │
│ 输入：colorTexture                            │
│ 效果：由 effectType uniform 控制               │
└──────────────────────────────────────────────┘
```

---

## 三、场景搭建

### 3.1 地面

一个大的水平四边形，带有重复纹理映射：

```cpp
float planeVertices[] = {
    // positions          // normals        // texCoords
     25.0f, 0.0f,  25.0f,  0.0f, 1.0f, 0.0f,  25.0f,  0.0f,
    -25.0f, 0.0f,  25.0f,  0.0f, 1.0f, 0.0f,   0.0f,  0.0f,
    -25.0f, 0.0f, -25.0f,  0.0f, 1.0f, 0.0f,   0.0f, 25.0f,
    // ... 第二个三角形 ...
};
```

纹理坐标设为 0~25，配合 `GL_REPEAT` 环绕模式实现地砖重复效果。

### 3.2 3D 模型实例化

加载一个背包模型，通过不同的模型矩阵在场景中放置 3 个实例：

```cpp
Model backpack("resources/backpack/backpack.obj");

glm::vec3 modelPositions[] = {
    glm::vec3( 0.0f, 0.0f,  0.0f),
    glm::vec3( 5.0f, 0.0f, -3.0f),
    glm::vec3(-4.0f, 0.0f,  2.0f),
};
float modelScales[]    = { 1.0f, 0.8f, 1.2f };
float modelRotations[] = { 0.0f, 45.0f, -30.0f };

for (int i = 0; i < 3; i++) {
    glm::mat4 model = glm::mat4(1.0f);
    model = glm::translate(model, modelPositions[i]);
    model = glm::rotate(model, glm::radians(modelRotations[i]),
                        glm::vec3(0, 1, 0));
    model = glm::scale(model, glm::vec3(modelScales[i]));
    sceneShader.setMat4("model", model);
    backpack.Draw(sceneShader);
}
```

同一个 `Model` 对象可以多次绘制，只需每次改变模型矩阵。

### 3.3 天空盒

渲染天空盒的要点（回顾第9篇）：

1. 去掉 View 矩阵的平移分量：`glm::mat4(glm::mat3(view))`
2. 顶点着色器中设置 `gl_Position = pos.xyww`，让深度值恒为 1.0
3. 将深度函数改为 `GL_LEQUAL`，最后绘制天空盒

---

## 四、完整光照系统

### 4.1 光源配置

我们的场景包含三种光源类型：

**1. 太阳光（平行光）**

```cpp
sceneShader.setVec3("dirLight.direction", -0.2f, -1.0f, -0.3f);
sceneShader.setVec3("dirLight.ambient",    0.15f, 0.15f, 0.12f);
sceneShader.setVec3("dirLight.diffuse",    0.8f,  0.75f, 0.6f);
sceneShader.setVec3("dirLight.specular",   1.0f,  0.95f, 0.8f);
```

暖黄色调模拟午后阳光。

**2. 四个点光源**

分布在场景四角，各有不同颜色，且上下轻微浮动增添动感：

```cpp
glm::vec3 pointLightCol[] = {
    glm::vec3(1.0f, 0.8f, 0.6f),  // 暖白
    glm::vec3(0.6f, 0.8f, 1.0f),  // 冷蓝
    glm::vec3(0.8f, 1.0f, 0.6f),  // 浅绿
    glm::vec3(1.0f, 0.6f, 0.8f),  // 粉红
};

// 渲染循环中让点光源上下浮动
pos.y += 0.3f * sin(time * 1.5f + i * 1.57f);
```

每个点光源同时渲染一个小立方体来可视化光源位置。

**3. 手电筒（聚光灯）**

跟随摄像机位置和朝向，按 F 键可开关：

```cpp
if (flashlightOn) {
    sceneShader.setVec3("spotLight.position",  camera.Position);
    sceneShader.setVec3("spotLight.direction", camera.Front);
    sceneShader.setVec3("spotLight.diffuse",   1.0f, 1.0f, 1.0f);
    // ...
} else {
    sceneShader.setVec3("spotLight.diffuse",  0.0f, 0.0f, 0.0f);
    // ...
}
```

### 4.2 着色器中的光照整合

片段着色器中组合所有光源的贡献：

```glsl
void main()
{
    vec3 norm    = normalize(Normal);
    vec3 viewDir = normalize(viewPos - FragPos);

    // 计算阴影（只影响平行光）
    float shadow = ShadowCalculation(FragPosLightSpace, norm,
                                      normalize(-dirLight.direction));

    // 平行光（带阴影）
    vec3 result = CalcDirLight(dirLight, norm, viewDir, shadow);

    // 4 个点光源
    for (int i = 0; i < NR_POINT_LIGHTS; i++)
        result += CalcPointLight(pointLights[i], norm, FragPos, viewDir);

    // 聚光灯
    result += CalcSpotLight(spotLight, norm, FragPos, viewDir);

    FragColor = vec4(result, 1.0);
}
```

### 4.3 纹理 vs 纯色材质

场景中有两类物体：有纹理贴图的模型和使用纯色的地面。着色器通过 `useTexture` uniform 来区分：

```glsl
vec3 texColor = useTexture
    ? vec3(texture(material.texture_diffuse1, TexCoords))
    : vec3(0.8, 0.8, 0.8);
```

---

## 五、阴影系统

### 5.1 Shadow Map 参数

本项目使用 2048×2048 分辨率的阴影贴图，配合 PCF 3×3 软阴影：

```cpp
const unsigned int SHADOW_WIDTH  = 2048;
const unsigned int SHADOW_HEIGHT = 2048;
```

光源空间矩阵使用正交投影（适合平行光）：

```cpp
glm::mat4 lightProj = glm::ortho(-15.0f, 15.0f,
                                  -15.0f, 15.0f,
                                  0.1f, 20.0f);
glm::mat4 lightView = glm::lookAt(sunPos,
                                   glm::vec3(0.0f),
                                   glm::vec3(0.0f, 1.0f, 0.0f));
```

### 5.2 Shadow Pass

第一个 Pass 从光源视角渲染所有投射阴影的物体，只写深度：

```cpp
depthShader.use();
depthShader.setMat4("lightSpaceMatrix", lightSpace);

glViewport(0, 0, SHADOW_WIDTH, SHADOW_HEIGHT);
glBindFramebuffer(GL_FRAMEBUFFER, depthFBO);
glClear(GL_DEPTH_BUFFER_BIT);

// 渲染地面和模型（只需要顶点位置）
// ...

glBindFramebuffer(GL_FRAMEBUFFER, 0);
```

注意 Shadow Pass 中模型使用 `DrawDepthOnly()` 方法，跳过纹理绑定以提高性能。

---

## 六、渲染优化

### 6.1 面剔除（Face Culling）

启用背面剔除可以跳过不朝向摄像机的三角形，减少约一半的片段处理量：

```cpp
glEnable(GL_CULL_FACE);
```

OpenGL 默认剔除背面（逆时针顶点顺序的面为正面）。注意对于某些模型（如内部可见的物体），可能需要临时禁用剔除：

```cpp
glDisable(GL_CULL_FACE);
backpack.Draw(sceneShader);
glEnable(GL_CULL_FACE);
```

### 6.2 深度贴图 Pass 优化

Shadow Pass 中不需要颜色输出和纹理采样，使用最简着色器即可。对于复杂模型，`DrawDepthOnly()` 方法只绑定 VAO 和执行绘制命令，跳过纹理绑定。

### 6.3 性能分析思路

如果遇到性能瓶颈，可以从以下几个方向排查：

| 瓶颈类型 | 诊断方法 | 优化方向 |
|---------|---------|---------|
| CPU 瓶颈 | 大量 draw call | 合并 Mesh、实例化渲染 |
| 顶点瓶颈 | 高多边形模型 | LOD（细节层次）、遮挡剔除 |
| 片段瓶颈 | 高分辨率、复杂着色器 | 降低分辨率、简化着色器 |
| 带宽瓶颈 | 大量纹理 | 纹理压缩、Mipmap、纹理图集 |

---

## 七、后处理管线

### 7.1 流程

场景先渲染到自定义 FBO 的颜色附件中，然后在 Pass 3 中将这个颜色纹理作为输入，通过后处理着色器处理后输出到屏幕：

```cpp
// Pass 3
glDisable(GL_DEPTH_TEST);
screenShader.use();
screenShader.setInt("effectType", currentEffect);
glBindVertexArray(quadVAO);
glBindTexture(GL_TEXTURE_2D, colorTex);
glDrawArrays(GL_TRIANGLES, 0, 6);
glEnable(GL_DEPTH_TEST);
```

### 7.2 可用效果

| 按键 | effectType | 效果 |
|-----|-----------|------|
| 0 | 0 | 无（直接输出） |
| 1 | 1 | 反相 |
| 2 | 2 | 灰度 |
| 3 | 3 | 锐化 |
| 4 | 4 | 高斯模糊 |
| 5 | 5 | 边缘检测 |

---

## 八、核心 API 速查

本篇综合使用了前9篇的所有 API。以下是本篇新增/强调的：

| 函数 / 技术 | 作用 |
|------------|------|
| `glEnable(GL_CULL_FACE)` | 启用面剔除 |
| `glDisable(GL_CULL_FACE)` | 禁用面剔除（特殊物体需要） |
| `glCullFace(GL_BACK)` | 设置剔除背面（默认） |
| `glFrontFace(GL_CCW)` | 设置逆时针为正面（默认） |
| Multi-pass rendering | 多 Pass 渲染管线设计 |
| Uniform Buffer Object | 跨着色器共享矩阵数据（进阶优化） |

---

## 九、完整代码

[教程完整代码链接](https://download.csdn.net/download/qq_29681777/92731423)

完整可编译代码请参阅 `src/` 目录。代码结构与本文描述一致，所有着色器位于 `src/shaders/` 目录下。

### 9.1 构建步骤

```bash
cd 10-综合实战项目/src
mkdir build && cd build
cmake ..
make
./CompleteDemoScene
```

### 9.2 获取资源文件

| 资源 | 获取方式 |
|------|---------|
| 背包模型 | [learnopengl.com/data/models/backpack.zip](https://learnopengl.com/data/models/backpack.zip) |
| 天空盒纹理 | [learnopengl.com/img/textures/skybox/](https://learnopengl.com/img/textures/skybox/) |
| 地面纹理 | 任意 PNG/JPG 地砖纹理 |

将下载的资源放到 `src/resources/` 目录下，保持如下结构：

```
resources/
├── floor.png
├── backpack/
│   ├── backpack.obj
│   ├── backpack.mtl
│   ├── diffuse.jpg
│   └── specular.jpg
└── skybox/
    ├── right.jpg
    ├── left.jpg
    ├── top.jpg
    ├── bottom.jpg
    ├── front.jpg
    └── back.jpg
```

---

## 十、常见问题

### Q1：编译时 Assimp 找不到

确认已安装 Assimp 并且 CMake 能找到它：
```bash
# macOS
brew install assimp
# Ubuntu
sudo apt install libassimp-dev
```

如果 CMake 仍然找不到，尝试手动指定路径：
```bash
cmake .. -DASSIMP_DIR=/path/to/assimp
```

### Q2：场景中看不到阴影

检查以下几点：
- `lightSpaceMatrix` 是否正确传递
- Shadow Pass 中是否渲染了所有投射阴影的物体
- 场景着色器中 `shadowMap` 的纹理单元是否正确绑定
- 光源投影范围是否覆盖了场景

### Q3：模型穿过地面或浮在空中

调整模型的 Y 轴位移。不同模型的原点位置不同，可能需要手动微调。

### Q4：手电筒开关无反应

确保 F 键的防抖逻辑正确实现（使用 `fPressed` 标志变量），避免按一次触发多次切换。

### Q5：运行时帧率低

- 降低 Shadow Map 分辨率（如 2048 → 1024）
- 减少点光源数量
- 禁用后处理（按 0）
- 使用更简单的模型

---

## 十一、练习题

### 练习 1：添加更多模型

在场景中加入第二种模型（如立方体、球体或其他 .obj 模型），放置在不同位置，使场景更丰富。

**提示：** 创建第二个 `Model` 对象，在渲染循环中使用不同的模型矩阵绘制。

### 练习 2：日夜交替

实现平行光方向随时间缓慢旋转，模拟太阳从东方升起、西方落下的效果。同时调整天空盒颜色从蓝天过渡到橙色夕阳再到深蓝夜空。

**提示：** 用 `sin(time * speed)` 和 `cos(time * speed)` 驱动太阳方向，用时间因子混合光源颜色。

### 练习 3：性能对比实验

在场景中放置 100 个模型实例，分别测量以下优化前后的帧率：
1. 有/无面剔除
2. Shadow Map 分辨率 512 vs 2048 vs 4096
3. PCF 3×3 vs 5×5 vs 无 PCF

记录数据并分析各优化对性能的影响。

---

## 十二、扩展方向

恭喜你完成了整个 OpenGL 入门教程！以下是进阶学习路线：

### PBR（基于物理的渲染）

用更真实的 Cook-Torrance BRDF 替代 Phong 模型，引入金属度（Metallic）和粗糙度（Roughness）参数。

**推荐资源：** [LearnOpenGL - PBR](https://learnopengl.com/PBR/Theory)

### 延迟渲染（Deferred Rendering）

将几何信息（位置、法线、颜色）先存储到 G-Buffer 中，再统一进行光照计算。支持大量光源而不影响性能。

**推荐资源：** [LearnOpenGL - Deferred Shading](https://learnopengl.com/Advanced-Lighting/Deferred-Shading)

### 计算着色器（Compute Shader）

OpenGL 4.3+ 的通用 GPU 计算能力，可用于粒子系统、物理模拟、图像处理等。

**推荐资源：** [OpenGL Wiki - Compute Shader](https://www.khronos.org/opengl/wiki/Compute_Shader)

### Vulkan 迁移

掌握 OpenGL 后，你已经理解了 GPU 渲染的核心概念。迁移到 Vulkan 主要是学习其更底层的 API 设计：
- 显式的命令缓冲区和同步
- 手动管理内存和描述符集
- 渲染通道和管线对象

**推荐资源：** [vulkan-tutorial.com](https://vulkan-tutorial.com/)

### 游戏引擎架构

如果你对游戏引擎开发感兴趣，推荐阅读：
- *Game Engine Architecture* by Jason Gregory
- 研究开源引擎源码（如 Godot、Hazel）

---

## 十三、参考资料

1. [LearnOpenGL](https://learnopengl.com/) — 本教程系列的主要参考
2. [OpenGL Reference Pages](https://docs.gl/)
3. [OpenGL Wiki](https://www.khronos.org/opengl/wiki/)
4. *OpenGL Programming Guide* (Red Book), 9th Edition
5. *OpenGL Shading Language* (Orange Book), 4th Edition
6. [Real-Time Rendering, 4th Edition](https://www.realtimerendering.com/)
7. [GPU Gems Series](https://developer.nvidia.com/gpugems/gpugems/contributors)
8. [Scratchapixel](https://www.scratchapixel.com/) — 计算机图形学理论

---

## 总结

通过这 10 篇教程，我们从零开始走过了 OpenGL 的完整学习路径：

| 篇章 | 知识点 | 代码产出 |
|------|-------|---------|
| 第1篇 | 环境搭建、OpenGL 上下文 | 窗口程序 |
| 第2篇 | 渲染管线、VBO/VAO/EBO | 彩色三角形 |
| 第3篇 | GLSL、Uniform | Shader 工具类 |
| 第4篇 | 纹理映射、多纹理混合 | 纹理矩形 |
| 第5篇 | MVP 矩阵、深度测试 | 3D 旋转立方体 |
| 第6篇 | 摄像机系统 | Camera 工具类 |
| 第7篇 | Phong 光照、多光源 | 光照场景 |
| 第8篇 | Assimp 模型加载 | Mesh/Model 类 |
| 第9篇 | FBO、天空盒、阴影 | 进阶渲染场景 |
| 第10篇 | 综合整合 | 完整 3D Demo |

每一步都建立在前一步的基础上，最终汇聚成一个完整的渲染系统。希望这个教程能帮助你理解现代 GPU 渲染的核心原理，为进一步学习打下坚实的基础。

**Happy Coding!**
