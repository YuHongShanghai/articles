#include <glad/glad.h>
#include <GLFW/glfw3.h>

#include <glm/glm.hpp>
#include <glm/gtc/matrix_transform.hpp>
#include <glm/gtc/type_ptr.hpp>

// model.h 中只声明使用 stb_image，STB 实现在此处定义
#define STB_IMAGE_IMPLEMENTATION
#include "shader.h"
#include "camera.h"
#include "model.h"

#include <iostream>
#include <fstream>

void framebuffer_size_callback(GLFWwindow* window, int width, int height);
void mouse_callback(GLFWwindow* window, double xpos, double ypos);
void scroll_callback(GLFWwindow* window, double xoffset, double yoffset);
void processInput(GLFWwindow* window);

const unsigned int SCR_WIDTH  = 800;
const unsigned int SCR_HEIGHT = 600;

Camera camera(glm::vec3(0.0f, 0.0f, 5.0f));
float lastX = SCR_WIDTH  / 2.0f;
float lastY = SCR_HEIGHT / 2.0f;
bool firstMouse = true;

float deltaTime = 0.0f;
float lastFrame = 0.0f;

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
                                          "08 - Model Loading", NULL, NULL);
    if (!window)
    {
        std::cout << "Failed to create GLFW window" << std::endl;
        glfwTerminate();
        return -1;
    }
    glfwMakeContextCurrent(window);
    glfwSetFramebufferSizeCallback(window, framebuffer_size_callback);
    glfwSetCursorPosCallback(window, mouse_callback);
    glfwSetScrollCallback(window, scroll_callback);
    glfwSetInputMode(window, GLFW_CURSOR, GLFW_CURSOR_DISABLED);

    if (!gladLoadGLLoader((GLADloadproc)glfwGetProcAddress))
    {
        std::cout << "Failed to initialize GLAD" << std::endl;
        return -1;
    }

    glEnable(GL_DEPTH_TEST);

    Shader modelShader("shaders/model.vs", "shaders/model.fs");

    // 加载模型
    // 模型文件需自行下载，下载地址：
    //   https://learnopengl.com/data/models/backpack.zip
    // 解压后将 backpack/ 文件夹放到可执行文件同级的 resources/ 目录下：
    //   cmake-build-debug/ch08/resources/backpack/backpack.obj
    const std::string modelPath = "resources/backpack/backpack.obj";
    {
        std::ifstream checkFile(modelPath);
        if (!checkFile.good()) {
            std::cerr << "\n[错误] 找不到模型文件: " << modelPath << "\n\n"
                      << "请按以下步骤获取模型：\n"
                      << "  1. 下载: https://learnopengl.com/data/models/backpack.zip\n"
                      << "  2. 解压，将 backpack/ 文件夹放到以下路径：\n"
                      << "     <构建目录>/ch08/resources/backpack/\n"
                      << "  3. 确认路径: cmake-build-debug/ch08/resources/backpack/backpack.obj\n\n";
            glfwTerminate();
            return -1;
        }
    }
    Model ourModel(modelPath);

    while (!glfwWindowShouldClose(window))
    {
        float currentFrame = static_cast<float>(glfwGetTime());
        deltaTime = currentFrame - lastFrame;
        lastFrame = currentFrame;

        processInput(window);

        glClearColor(0.05f, 0.05f, 0.08f, 1.0f);
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

        modelShader.use();
        modelShader.setVec3("viewPos", camera.Position);

        // 平行光（模拟太阳光）
        modelShader.setVec3("dirLight.direction", -0.2f, -1.0f, -0.3f);
        modelShader.setVec3("dirLight.ambient",    0.2f,  0.2f,  0.2f);
        modelShader.setVec3("dirLight.diffuse",    0.5f,  0.5f,  0.5f);
        modelShader.setVec3("dirLight.specular",   1.0f,  1.0f,  1.0f);

        // 点光源
        modelShader.setVec3("pointLight.position", 1.2f, 1.0f, 2.0f);
        modelShader.setVec3("pointLight.ambient",  0.05f, 0.05f, 0.05f);
        modelShader.setVec3("pointLight.diffuse",  0.8f,  0.8f,  0.8f);
        modelShader.setVec3("pointLight.specular", 1.0f,  1.0f,  1.0f);
        modelShader.setFloat("pointLight.constant",  1.0f);
        modelShader.setFloat("pointLight.linear",    0.09f);
        modelShader.setFloat("pointLight.quadratic", 0.032f);

        modelShader.setFloat("material.shininess", 32.0f);

        // 变换矩阵
        glm::mat4 projection = glm::perspective(
            glm::radians(camera.Zoom),
            (float)SCR_WIDTH / (float)SCR_HEIGHT,
            0.1f, 100.0f);
        glm::mat4 view = camera.GetViewMatrix();
        modelShader.setMat4("projection", projection);
        modelShader.setMat4("view", view);

        glm::mat4 model = glm::mat4(1.0f);
        model = glm::translate(model, glm::vec3(0.0f, 0.0f, 0.0f));
        model = glm::scale(model, glm::vec3(1.0f));
        modelShader.setMat4("model", model);

        ourModel.Draw(modelShader);

        glfwSwapBuffers(window);
        glfwPollEvents();
    }

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
}

void framebuffer_size_callback(GLFWwindow* window, int width, int height)
{
    glViewport(0, 0, width, height);
}

void mouse_callback(GLFWwindow* window, double xposIn, double yposIn)
{
    float xpos = static_cast<float>(xposIn);
    float ypos = static_cast<float>(yposIn);

    if (firstMouse)
    {
        lastX = xpos;
        lastY = ypos;
        firstMouse = false;
    }

    float xoffset = xpos - lastX;
    float yoffset = lastY - ypos;

    lastX = xpos;
    lastY = ypos;

    camera.ProcessMouseMovement(xoffset, yoffset);
}

void scroll_callback(GLFWwindow* window, double xoffset, double yoffset)
{
    camera.ProcessMouseScroll(static_cast<float>(yoffset));
}
