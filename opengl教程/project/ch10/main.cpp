#include <glad/glad.h>
#include <GLFW/glfw3.h>

#include <glm/glm.hpp>
#include <glm/gtc/matrix_transform.hpp>
#include <glm/gtc/type_ptr.hpp>

#include "shader.h"
#include "camera.h"
#include "model.h"

#define STB_IMAGE_IMPLEMENTATION
#include "stb_image.h"

#include <iostream>
#include <fstream>
#include <vector>

void framebuffer_size_callback(GLFWwindow* window, int width, int height);
void mouse_callback(GLFWwindow* window, double xpos, double ypos);
void scroll_callback(GLFWwindow* window, double xoffset, double yoffset);
void processInput(GLFWwindow* window);
unsigned int loadTexture(const char *path);
unsigned int loadCubemap(const std::vector<std::string> &faces);

const unsigned int SCR_WIDTH  = 1280;
const unsigned int SCR_HEIGHT = 720;
const unsigned int SHADOW_WIDTH  = 2048;
const unsigned int SHADOW_HEIGHT = 2048;

Camera camera(glm::vec3(0.0f, 2.0f, 8.0f));
float lastX = SCR_WIDTH  / 2.0f;
float lastY = SCR_HEIGHT / 2.0f;
bool firstMouse = true;

float deltaTime = 0.0f;
float lastFrame = 0.0f;

int currentEffect = 0;
bool flashlightOn = true;

int main()
{
    glfwInit();
    glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 3);
    glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 3);
    glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);
#ifdef __APPLE__
    glfwWindowHint(GLFW_OPENGL_FORWARD_COMPAT, GL_TRUE);
#endif

    GLFWwindow* window = glfwCreateWindow(SCR_WIDTH, SCR_HEIGHT,
        "OpenGL Demo - Complete 3D Scene", NULL, NULL);
    if (!window) {
        std::cout << "Failed to create GLFW window" << std::endl;
        glfwTerminate();
        return -1;
    }
    glfwMakeContextCurrent(window);
    glfwSetFramebufferSizeCallback(window, framebuffer_size_callback);
    glfwSetCursorPosCallback(window, mouse_callback);
    glfwSetScrollCallback(window, scroll_callback);
    glfwSetInputMode(window, GLFW_CURSOR, GLFW_CURSOR_DISABLED);

    if (!gladLoadGLLoader((GLADloadproc)glfwGetProcAddress)) {
        std::cout << "Failed to initialize GLAD" << std::endl;
        return -1;
    }

    glEnable(GL_DEPTH_TEST);
    glEnable(GL_CULL_FACE);

    // ===== 着色器 =====
    Shader sceneShader("shaders/scene.vs",  "shaders/scene.fs");
    Shader depthShader("shaders/depth.vs",  "shaders/depth.fs");
    Shader skyboxShader("shaders/skybox.vs","shaders/skybox.fs");
    Shader screenShader("shaders/screen.vs","shaders/screen.fs");
    Shader lightShader("shaders/light.vs",  "shaders/light.fs");

    // ===== 地面顶点 =====
    float planeVertices[] = {
         25.0f, 0.0f,  25.0f,  0.0f, 1.0f, 0.0f,  25.0f,  0.0f,
        -25.0f, 0.0f,  25.0f,  0.0f, 1.0f, 0.0f,   0.0f,  0.0f,
        -25.0f, 0.0f, -25.0f,  0.0f, 1.0f, 0.0f,   0.0f, 25.0f,
         25.0f, 0.0f,  25.0f,  0.0f, 1.0f, 0.0f,  25.0f,  0.0f,
        -25.0f, 0.0f, -25.0f,  0.0f, 1.0f, 0.0f,   0.0f, 25.0f,
         25.0f, 0.0f, -25.0f,  0.0f, 1.0f, 0.0f,  25.0f, 25.0f,
    };

    // 光源立方体
    float cubeVertices[] = {
        -0.5f,-0.5f,-0.5f,  0.5f,-0.5f,-0.5f,  0.5f, 0.5f,-0.5f,
         0.5f, 0.5f,-0.5f, -0.5f, 0.5f,-0.5f, -0.5f,-0.5f,-0.5f,
        -0.5f,-0.5f, 0.5f,  0.5f,-0.5f, 0.5f,  0.5f, 0.5f, 0.5f,
         0.5f, 0.5f, 0.5f, -0.5f, 0.5f, 0.5f, -0.5f,-0.5f, 0.5f,
        -0.5f, 0.5f, 0.5f, -0.5f, 0.5f,-0.5f, -0.5f,-0.5f,-0.5f,
        -0.5f,-0.5f,-0.5f, -0.5f,-0.5f, 0.5f, -0.5f, 0.5f, 0.5f,
         0.5f, 0.5f, 0.5f,  0.5f, 0.5f,-0.5f,  0.5f,-0.5f,-0.5f,
         0.5f,-0.5f,-0.5f,  0.5f,-0.5f, 0.5f,  0.5f, 0.5f, 0.5f,
        -0.5f,-0.5f,-0.5f,  0.5f,-0.5f,-0.5f,  0.5f,-0.5f, 0.5f,
         0.5f,-0.5f, 0.5f, -0.5f,-0.5f, 0.5f, -0.5f,-0.5f,-0.5f,
        -0.5f, 0.5f,-0.5f,  0.5f, 0.5f,-0.5f,  0.5f, 0.5f, 0.5f,
         0.5f, 0.5f, 0.5f, -0.5f, 0.5f, 0.5f, -0.5f, 0.5f,-0.5f,
    };

    // 屏幕四边形
    float quadVertices[] = {
        -1.0f,  1.0f,  0.0f, 1.0f,
        -1.0f, -1.0f,  0.0f, 0.0f,
         1.0f, -1.0f,  1.0f, 0.0f,
        -1.0f,  1.0f,  0.0f, 1.0f,
         1.0f, -1.0f,  1.0f, 0.0f,
         1.0f,  1.0f,  1.0f, 1.0f,
    };

    // 天空盒
    float skyboxVertices[] = {
        -1.0f, 1.0f,-1.0f, -1.0f,-1.0f,-1.0f,  1.0f,-1.0f,-1.0f,
         1.0f,-1.0f,-1.0f,  1.0f, 1.0f,-1.0f, -1.0f, 1.0f,-1.0f,
        -1.0f,-1.0f, 1.0f, -1.0f,-1.0f,-1.0f, -1.0f, 1.0f,-1.0f,
        -1.0f, 1.0f,-1.0f, -1.0f, 1.0f, 1.0f, -1.0f,-1.0f, 1.0f,
         1.0f,-1.0f,-1.0f,  1.0f,-1.0f, 1.0f,  1.0f, 1.0f, 1.0f,
         1.0f, 1.0f, 1.0f,  1.0f, 1.0f,-1.0f,  1.0f,-1.0f,-1.0f,
        -1.0f,-1.0f, 1.0f, -1.0f, 1.0f, 1.0f,  1.0f, 1.0f, 1.0f,
         1.0f, 1.0f, 1.0f,  1.0f,-1.0f, 1.0f, -1.0f,-1.0f, 1.0f,
        -1.0f, 1.0f,-1.0f,  1.0f, 1.0f,-1.0f,  1.0f, 1.0f, 1.0f,
         1.0f, 1.0f, 1.0f, -1.0f, 1.0f, 1.0f, -1.0f, 1.0f,-1.0f,
        -1.0f,-1.0f,-1.0f, -1.0f,-1.0f, 1.0f,  1.0f,-1.0f,-1.0f,
         1.0f,-1.0f,-1.0f, -1.0f,-1.0f, 1.0f,  1.0f,-1.0f, 1.0f,
    };

    // ===== VAO 设置 =====
    unsigned int planeVAO, planeVBO;
    glGenVertexArrays(1, &planeVAO);
    glGenBuffers(1, &planeVBO);
    glBindVertexArray(planeVAO);
    glBindBuffer(GL_ARRAY_BUFFER, planeVBO);
    glBufferData(GL_ARRAY_BUFFER, sizeof(planeVertices), planeVertices, GL_STATIC_DRAW);
    glEnableVertexAttribArray(0);
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 8*sizeof(float), (void*)0);
    glEnableVertexAttribArray(1);
    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 8*sizeof(float), (void*)(3*sizeof(float)));
    glEnableVertexAttribArray(2);
    glVertexAttribPointer(2, 2, GL_FLOAT, GL_FALSE, 8*sizeof(float), (void*)(6*sizeof(float)));

    unsigned int lightVAO, lightVBO;
    glGenVertexArrays(1, &lightVAO);
    glGenBuffers(1, &lightVBO);
    glBindVertexArray(lightVAO);
    glBindBuffer(GL_ARRAY_BUFFER, lightVBO);
    glBufferData(GL_ARRAY_BUFFER, sizeof(cubeVertices), cubeVertices, GL_STATIC_DRAW);
    glEnableVertexAttribArray(0);
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3*sizeof(float), (void*)0);

    unsigned int quadVAO, quadVBO;
    glGenVertexArrays(1, &quadVAO);
    glGenBuffers(1, &quadVBO);
    glBindVertexArray(quadVAO);
    glBindBuffer(GL_ARRAY_BUFFER, quadVBO);
    glBufferData(GL_ARRAY_BUFFER, sizeof(quadVertices), quadVertices, GL_STATIC_DRAW);
    glEnableVertexAttribArray(0);
    glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 4*sizeof(float), (void*)0);
    glEnableVertexAttribArray(1);
    glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 4*sizeof(float), (void*)(2*sizeof(float)));

    unsigned int skyboxVAO, skyboxVBO;
    glGenVertexArrays(1, &skyboxVAO);
    glGenBuffers(1, &skyboxVBO);
    glBindVertexArray(skyboxVAO);
    glBindBuffer(GL_ARRAY_BUFFER, skyboxVBO);
    glBufferData(GL_ARRAY_BUFFER, sizeof(skyboxVertices), skyboxVertices, GL_STATIC_DRAW);
    glEnableVertexAttribArray(0);
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3*sizeof(float), (void*)0);

    // ===== 纹理 =====
    unsigned int floorTex = loadTexture("resources/floor.png");

    std::vector<std::string> skyboxFaces = {
        "resources/skybox/right.jpg", "resources/skybox/left.jpg",
        "resources/skybox/top.jpg",   "resources/skybox/bottom.jpg",
        "resources/skybox/front.jpg", "resources/skybox/back.jpg"
    };
    unsigned int cubemapTex = loadCubemap(skyboxFaces);

    // ===== 加载 3D 模型 =====
    // 需要下载 backpack 模型: https://learnopengl.com/data/models/backpack.zip
    // 解压后放到: cmake-build-debug/ch10/resources/backpack/backpack.obj
    {
        std::ifstream checkFile("resources/backpack/backpack.obj");
        if (!checkFile.good()) {
            std::cerr << "\n[错误] 找不到模型文件: resources/backpack/backpack.obj\n\n"
                      << "请按以下步骤获取模型：\n"
                      << "  1. 下载: https://learnopengl.com/data/models/backpack.zip\n"
                      << "  2. 解压，将 backpack/ 文件夹放到: <构建目录>/ch10/resources/backpack/\n\n"
                      << "ch10 还需要 resources/floor.png 和 resources/skybox/*.jpg\n"
                      << "（可使用任意图片临时替代）\n\n";
            glfwTerminate();
            return -1;
        }
    }
    Model backpack("resources/backpack/backpack.obj");

    // ===== 帧缓冲（后处理）=====
    unsigned int fbo;
    glGenFramebuffers(1, &fbo);
    glBindFramebuffer(GL_FRAMEBUFFER, fbo);

    unsigned int colorTex;
    glGenTextures(1, &colorTex);
    glBindTexture(GL_TEXTURE_2D, colorTex);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, SCR_WIDTH, SCR_HEIGHT, 0, GL_RGB, GL_UNSIGNED_BYTE, NULL);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
    glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, colorTex, 0);

    unsigned int rbo;
    glGenRenderbuffers(1, &rbo);
    glBindRenderbuffer(GL_RENDERBUFFER, rbo);
    glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH24_STENCIL8, SCR_WIDTH, SCR_HEIGHT);
    glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_STENCIL_ATTACHMENT, GL_RENDERBUFFER, rbo);

    if (glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE)
        std::cout << "ERROR: Framebuffer not complete!" << std::endl;
    glBindFramebuffer(GL_FRAMEBUFFER, 0);

    // ===== 阴影深度贴图 =====
    unsigned int depthFBO;
    glGenFramebuffers(1, &depthFBO);
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
    float borderCol[] = {1.0f,1.0f,1.0f,1.0f};
    glTexParameterfv(GL_TEXTURE_2D, GL_TEXTURE_BORDER_COLOR, borderCol);
    glBindFramebuffer(GL_FRAMEBUFFER, depthFBO);
    glFramebufferTexture2D(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_TEXTURE_2D, depthMap, 0);
    glDrawBuffer(GL_NONE);
    glReadBuffer(GL_NONE);
    glBindFramebuffer(GL_FRAMEBUFFER, 0);

    // ===== 着色器配置 =====
    sceneShader.use();
    sceneShader.setInt("material.texture_diffuse1", 0);
    sceneShader.setInt("material.texture_specular1", 1);
    sceneShader.setInt("shadowMap", 2);

    screenShader.use();
    screenShader.setInt("screenTexture", 0);

    skyboxShader.use();
    skyboxShader.setInt("skybox", 0);

    // ===== 光源参数 =====
    glm::vec3 sunDir(-0.2f, -1.0f, -0.3f);
    glm::vec3 sunPos(2.0f, 8.0f, 1.0f);

    glm::vec3 pointLightPos[] = {
        glm::vec3( 3.0f, 1.5f,  3.0f),
        glm::vec3(-3.0f, 1.5f,  3.0f),
        glm::vec3( 3.0f, 1.5f, -3.0f),
        glm::vec3(-3.0f, 1.5f, -3.0f),
    };
    glm::vec3 pointLightCol[] = {
        glm::vec3(1.0f, 0.8f, 0.6f),
        glm::vec3(0.6f, 0.8f, 1.0f),
        glm::vec3(0.8f, 1.0f, 0.6f),
        glm::vec3(1.0f, 0.6f, 0.8f),
    };

    // ===== 渲染循环 =====
    while (!glfwWindowShouldClose(window))
    {
        float t = static_cast<float>(glfwGetTime());
        deltaTime = t - lastFrame;
        lastFrame = t;
        processInput(window);

        // ---- Pass 1: Shadow Map ----
        glm::mat4 lightProj = glm::ortho(-15.0f, 15.0f, -15.0f, 15.0f, 0.1f, 20.0f);
        glm::mat4 lightView = glm::lookAt(sunPos, glm::vec3(0.0f), glm::vec3(0.0f,1.0f,0.0f));
        glm::mat4 lightSpace = lightProj * lightView;

        depthShader.use();
        depthShader.setMat4("lightSpaceMatrix", lightSpace);

        glViewport(0, 0, SHADOW_WIDTH, SHADOW_HEIGHT);
        glBindFramebuffer(GL_FRAMEBUFFER, depthFBO);
        glClear(GL_DEPTH_BUFFER_BIT);

        // 地面
        glm::mat4 mdl = glm::mat4(1.0f);
        depthShader.setMat4("model", mdl);
        glBindVertexArray(planeVAO);
        glDrawArrays(GL_TRIANGLES, 0, 6);

        // 模型（3 个实例）
        glm::vec3 modelPositions[] = {
            glm::vec3(0.0f, 0.0f, 0.0f),
            glm::vec3(5.0f, 0.0f, -3.0f),
            glm::vec3(-4.0f, 0.0f, 2.0f),
        };
        float modelScales[] = { 1.0f, 0.8f, 1.2f };
        float modelRotations[] = { 0.0f, 45.0f, -30.0f };

        glDisable(GL_CULL_FACE);
        for (int i = 0; i < 3; i++) {
            mdl = glm::mat4(1.0f);
            mdl = glm::translate(mdl, modelPositions[i]);
            mdl = glm::rotate(mdl, glm::radians(modelRotations[i]), glm::vec3(0,1,0));
            mdl = glm::scale(mdl, glm::vec3(modelScales[i]));
            depthShader.setMat4("model", mdl);
            backpack.DrawDepthOnly();
        }
        glEnable(GL_CULL_FACE);

        glBindFramebuffer(GL_FRAMEBUFFER, 0);

        // ---- Pass 2: Scene → FBO ----
        glViewport(0, 0, SCR_WIDTH, SCR_HEIGHT);
        glBindFramebuffer(GL_FRAMEBUFFER, fbo);
        glClearColor(0.05f, 0.05f, 0.08f, 1.0f);
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

        sceneShader.use();
        glm::mat4 proj = glm::perspective(glm::radians(camera.Zoom),
            (float)SCR_WIDTH/(float)SCR_HEIGHT, 0.1f, 100.0f);
        glm::mat4 view = camera.GetViewMatrix();
        sceneShader.setMat4("projection", proj);
        sceneShader.setMat4("view", view);
        sceneShader.setVec3("viewPos", camera.Position);
        sceneShader.setMat4("lightSpaceMatrix", lightSpace);
        sceneShader.setFloat("material.shininess", 32.0f);

        // 平行光（太阳）
        sceneShader.setVec3("dirLight.direction", sunDir);
        sceneShader.setVec3("dirLight.ambient",   0.15f, 0.15f, 0.12f);
        sceneShader.setVec3("dirLight.diffuse",   0.8f,  0.75f, 0.6f);
        sceneShader.setVec3("dirLight.specular",  1.0f,  0.95f, 0.8f);

        // 4 个点光源
        for (int i = 0; i < 4; i++) {
            std::string b = "pointLights[" + std::to_string(i) + "]";
            glm::vec3 pos = pointLightPos[i];
            pos.y += 0.3f * sin(t * 1.5f + i * 1.57f);
            sceneShader.setVec3(b + ".position",  pos);
            sceneShader.setVec3(b + ".ambient",   pointLightCol[i] * 0.05f);
            sceneShader.setVec3(b + ".diffuse",   pointLightCol[i] * 0.6f);
            sceneShader.setVec3(b + ".specular",  pointLightCol[i]);
            sceneShader.setFloat(b + ".constant",  1.0f);
            sceneShader.setFloat(b + ".linear",    0.14f);
            sceneShader.setFloat(b + ".quadratic", 0.07f);
        }

        // 聚光灯（手电筒）
        if (flashlightOn) {
            sceneShader.setVec3("spotLight.position",  camera.Position);
            sceneShader.setVec3("spotLight.direction",  camera.Front);
            sceneShader.setVec3("spotLight.ambient",    0.0f, 0.0f, 0.0f);
            sceneShader.setVec3("spotLight.diffuse",    1.0f, 1.0f, 1.0f);
            sceneShader.setVec3("spotLight.specular",   1.0f, 1.0f, 1.0f);
        } else {
            sceneShader.setVec3("spotLight.diffuse",  0.0f, 0.0f, 0.0f);
            sceneShader.setVec3("spotLight.specular", 0.0f, 0.0f, 0.0f);
            sceneShader.setVec3("spotLight.ambient",  0.0f, 0.0f, 0.0f);
        }
        sceneShader.setFloat("spotLight.constant",    1.0f);
        sceneShader.setFloat("spotLight.linear",      0.09f);
        sceneShader.setFloat("spotLight.quadratic",   0.032f);
        sceneShader.setFloat("spotLight.cutOff",      glm::cos(glm::radians(12.5f)));
        sceneShader.setFloat("spotLight.outerCutOff", glm::cos(glm::radians(17.5f)));

        // 绑定阴影贴图
        glActiveTexture(GL_TEXTURE2);
        glBindTexture(GL_TEXTURE_2D, depthMap);

        // 绘制地面
        sceneShader.setBool("useTexture", true);
        glActiveTexture(GL_TEXTURE0);
        glBindTexture(GL_TEXTURE_2D, floorTex);
        glActiveTexture(GL_TEXTURE1);
        glBindTexture(GL_TEXTURE_2D, floorTex);
        mdl = glm::mat4(1.0f);
        sceneShader.setMat4("model", mdl);
        glBindVertexArray(planeVAO);
        glDrawArrays(GL_TRIANGLES, 0, 6);

        // 绘制 3D 模型
        sceneShader.setBool("useTexture", true);
        glDisable(GL_CULL_FACE);
        for (int i = 0; i < 3; i++) {
            mdl = glm::mat4(1.0f);
            mdl = glm::translate(mdl, modelPositions[i]);
            mdl = glm::rotate(mdl, glm::radians(modelRotations[i]), glm::vec3(0,1,0));
            mdl = glm::scale(mdl, glm::vec3(modelScales[i]));
            sceneShader.setMat4("model", mdl);
            backpack.Draw(sceneShader);
        }
        glEnable(GL_CULL_FACE);

        // 绘制光源立方体
        lightShader.use();
        lightShader.setMat4("projection", proj);
        lightShader.setMat4("view", view);
        glBindVertexArray(lightVAO);
        for (int i = 0; i < 4; i++) {
            glm::vec3 pos = pointLightPos[i];
            pos.y += 0.3f * sin(t * 1.5f + i * 1.57f);
            mdl = glm::mat4(1.0f);
            mdl = glm::translate(mdl, pos);
            mdl = glm::scale(mdl, glm::vec3(0.15f));
            lightShader.setMat4("model", mdl);
            lightShader.setVec3("lightColor", pointLightCol[i]);
            glDrawArrays(GL_TRIANGLES, 0, 36);
        }

        // 天空盒
        glDepthFunc(GL_LEQUAL);
        skyboxShader.use();
        skyboxShader.setMat4("view", glm::mat4(glm::mat3(view)));
        skyboxShader.setMat4("projection", proj);
        glBindVertexArray(skyboxVAO);
        glActiveTexture(GL_TEXTURE0);
        glBindTexture(GL_TEXTURE_CUBE_MAP, cubemapTex);
        glDrawArrays(GL_TRIANGLES, 0, 36);
        glDepthFunc(GL_LESS);

        glBindFramebuffer(GL_FRAMEBUFFER, 0);

        // ---- Pass 3: 后处理 → 屏幕 ----
        glDisable(GL_DEPTH_TEST);
        glClearColor(1.0f, 1.0f, 1.0f, 1.0f);
        glClear(GL_COLOR_BUFFER_BIT);

        screenShader.use();
        screenShader.setInt("effectType", currentEffect);
        glBindVertexArray(quadVAO);
        glActiveTexture(GL_TEXTURE0);
        glBindTexture(GL_TEXTURE_2D, colorTex);
        glDrawArrays(GL_TRIANGLES, 0, 6);

        glEnable(GL_DEPTH_TEST);

        glfwSwapBuffers(window);
        glfwPollEvents();
    }

    glDeleteVertexArrays(1, &planeVAO);
    glDeleteVertexArrays(1, &lightVAO);
    glDeleteVertexArrays(1, &quadVAO);
    glDeleteVertexArrays(1, &skyboxVAO);
    glDeleteBuffers(1, &planeVBO);
    glDeleteBuffers(1, &lightVBO);
    glDeleteBuffers(1, &quadVBO);
    glDeleteBuffers(1, &skyboxVBO);
    glDeleteFramebuffers(1, &fbo);
    glDeleteFramebuffers(1, &depthFBO);

    glfwTerminate();
    return 0;
}

void processInput(GLFWwindow* window)
{
    if (glfwGetKey(window, GLFW_KEY_ESCAPE) == GLFW_PRESS)
        glfwSetWindowShouldClose(window, true);
    if (glfwGetKey(window, GLFW_KEY_W) == GLFW_PRESS)
        camera.ProcessKeyboard(FORWARD, deltaTime);
    if (glfwGetKey(window, GLFW_KEY_S) == GLFW_PRESS)
        camera.ProcessKeyboard(BACKWARD, deltaTime);
    if (glfwGetKey(window, GLFW_KEY_A) == GLFW_PRESS)
        camera.ProcessKeyboard(LEFT, deltaTime);
    if (glfwGetKey(window, GLFW_KEY_D) == GLFW_PRESS)
        camera.ProcessKeyboard(RIGHT, deltaTime);

    // 数字键 0-5 切换后处理
    for (int k = 0; k <= 5; k++)
        if (glfwGetKey(window, GLFW_KEY_0 + k) == GLFW_PRESS)
            currentEffect = k;

    // F 键切换手电筒
    static bool fPressed = false;
    if (glfwGetKey(window, GLFW_KEY_F) == GLFW_PRESS && !fPressed) {
        flashlightOn = !flashlightOn;
        fPressed = true;
    }
    if (glfwGetKey(window, GLFW_KEY_F) == GLFW_RELEASE)
        fPressed = false;
}

void framebuffer_size_callback(GLFWwindow*, int w, int h) { glViewport(0, 0, w, h); }

void mouse_callback(GLFWwindow*, double x, double y)
{
    float xp = (float)x, yp = (float)y;
    if (firstMouse) { lastX = xp; lastY = yp; firstMouse = false; }
    camera.ProcessMouseMovement(xp - lastX, lastY - yp);
    lastX = xp; lastY = yp;
}

void scroll_callback(GLFWwindow*, double, double y)
{ camera.ProcessMouseScroll((float)y); }

unsigned int loadTexture(const char *path)
{
    unsigned int id;
    glGenTextures(1, &id);
    int w, h, ch;
    unsigned char *data = stbi_load(path, &w, &h, &ch, 0);
    if (data) {
        GLenum fmt = ch == 4 ? GL_RGBA : (ch == 3 ? GL_RGB : GL_RED);
        glBindTexture(GL_TEXTURE_2D, id);
        glTexImage2D(GL_TEXTURE_2D, 0, fmt, w, h, 0, fmt, GL_UNSIGNED_BYTE, data);
        glGenerateMipmap(GL_TEXTURE_2D);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
    } else {
        std::cout << "Texture failed: " << path << std::endl;
    }
    stbi_image_free(data);
    return id;
}

unsigned int loadCubemap(const std::vector<std::string> &faces)
{
    unsigned int id;
    glGenTextures(1, &id);
    glBindTexture(GL_TEXTURE_CUBE_MAP, id);
    int w, h, ch;
    for (unsigned int i = 0; i < faces.size(); i++) {
        unsigned char *data = stbi_load(faces[i].c_str(), &w, &h, &ch, 0);
        if (data) {
            glTexImage2D(GL_TEXTURE_CUBE_MAP_POSITIVE_X + i,
                         0, GL_RGB, w, h, 0, GL_RGB, GL_UNSIGNED_BYTE, data);
        } else {
            std::cout << "Cubemap failed: " << faces[i] << std::endl;
        }
        stbi_image_free(data);
    }
    glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_CUBE_MAP, GL_TEXTURE_WRAP_R, GL_CLAMP_TO_EDGE);
    return id;
}
