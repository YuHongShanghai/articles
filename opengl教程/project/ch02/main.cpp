#include <glad/glad.h>
#include <GLFW/glfw3.h>
#include <iostream>

// ---------------------------------------------------------------------------
// 着色器源码
// ---------------------------------------------------------------------------

// 顶点着色器：接收位置和颜色，将颜色传递给片段着色器
const char* vertexShaderSource = R"glsl(
#version 330 core
layout (location = 0) in vec3 aPos;
layout (location = 1) in vec3 aColor;

out vec3 vertexColor;

void main() {
    gl_Position = vec4(aPos, 1.0);
    vertexColor = aColor;
}
)glsl";

// 片段着色器：使用插值后的颜色输出
const char* fragmentShaderSource = R"glsl(
#version 330 core
in vec3 vertexColor;
out vec4 FragColor;

void main() {
    FragColor = vec4(vertexColor, 1.0);
}
)glsl";

// 矩形专用片段着色器：使用纯橙色
const char* rectFragmentShaderSource = R"glsl(
#version 330 core
out vec4 FragColor;

void main() {
    FragColor = vec4(1.0, 0.5, 0.2, 1.0);
}
)glsl";

// ---------------------------------------------------------------------------
// 回调与工具函数
// ---------------------------------------------------------------------------

void framebufferSizeCallback(GLFWwindow* window, int width, int height) {
    glViewport(0, 0, width, height);
}

bool showTriangle = true;
bool wireframeMode = false;

void keyCallback(GLFWwindow* window, int key, int scancode, int action, int mods) {
    if (key == GLFW_KEY_ESCAPE && action == GLFW_PRESS)
        glfwSetWindowShouldClose(window, true);

    if (key == GLFW_KEY_SPACE && action == GLFW_PRESS)
        showTriangle = !showTriangle;

    if (key == GLFW_KEY_W && action == GLFW_PRESS) {
        wireframeMode = !wireframeMode;
        glPolygonMode(GL_FRONT_AND_BACK, wireframeMode ? GL_LINE : GL_FILL);
    }
}

unsigned int compileShader(GLenum type, const char* source) {
    unsigned int shader = glCreateShader(type);
    glShaderSource(shader, 1, &source, nullptr);
    glCompileShader(shader);

    int success;
    char infoLog[512];
    glGetShaderiv(shader, GL_COMPILE_STATUS, &success);
    if (!success) {
        glGetShaderInfoLog(shader, 512, nullptr, infoLog);
        std::cerr << (type == GL_VERTEX_SHADER ? "顶点" : "片段")
                  << "着色器编译失败:\n" << infoLog << std::endl;
    }
    return shader;
}

unsigned int linkProgram(unsigned int vertexShader, unsigned int fragmentShader) {
    unsigned int program = glCreateProgram();
    glAttachShader(program, vertexShader);
    glAttachShader(program, fragmentShader);
    glLinkProgram(program);

    int success;
    char infoLog[512];
    glGetProgramiv(program, GL_LINK_STATUS, &success);
    if (!success) {
        glGetProgramInfoLog(program, 512, nullptr, infoLog);
        std::cerr << "着色器程序链接失败:\n" << infoLog << std::endl;
    }
    return program;
}

// ---------------------------------------------------------------------------
// 主函数
// ---------------------------------------------------------------------------

int main() {
    // -----------------------------------------------------------------------
    // 1. 初始化 GLFW
    // -----------------------------------------------------------------------
    glfwInit();
    glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 3);
    glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 3);
    glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);
#ifdef __APPLE__
    glfwWindowHint(GLFW_OPENGL_FORWARD_COMPAT, GL_TRUE);
#endif

    GLFWwindow* window = glfwCreateWindow(800, 600, "02 - 渲染管线与第一个三角形", nullptr, nullptr);
    if (!window) {
        std::cerr << "创建 GLFW 窗口失败" << std::endl;
        glfwTerminate();
        return -1;
    }
    glfwMakeContextCurrent(window);
    glfwSetFramebufferSizeCallback(window, framebufferSizeCallback);
    glfwSetKeyCallback(window, keyCallback);

    // -----------------------------------------------------------------------
    // 2. 初始化 GLAD
    // -----------------------------------------------------------------------
    if (!gladLoadGLLoader((GLADloadproc)glfwGetProcAddress)) {
        std::cerr << "初始化 GLAD 失败" << std::endl;
        return -1;
    }

    // -----------------------------------------------------------------------
    // 3. 编译链接着色器
    // -----------------------------------------------------------------------
    unsigned int vertShader = compileShader(GL_VERTEX_SHADER, vertexShaderSource);
    unsigned int fragShader = compileShader(GL_FRAGMENT_SHADER, fragmentShaderSource);
    unsigned int triangleProgram = linkProgram(vertShader, fragShader);
    glDeleteShader(fragShader);

    // 矩形使用同一个顶点着色器，但用纯色片段着色器
    unsigned int rectFragShader = compileShader(GL_FRAGMENT_SHADER, rectFragmentShaderSource);
    unsigned int rectProgram = linkProgram(vertShader, rectFragShader);
    glDeleteShader(vertShader);
    glDeleteShader(rectFragShader);

    // -----------------------------------------------------------------------
    // 4. 准备三角形的顶点数据（位置 + 颜色，交错存储）
    // -----------------------------------------------------------------------
    float triangleVertices[] = {
        // 位置                // 颜色
        -0.5f, -0.5f, 0.0f,   1.0f, 0.0f, 0.0f,   // 左下 - 红
         0.5f, -0.5f, 0.0f,   0.0f, 1.0f, 0.0f,   // 右下 - 绿
         0.0f,  0.5f, 0.0f,   0.0f, 0.0f, 1.0f    // 顶部 - 蓝
    };

    unsigned int triangleVAO, triangleVBO;
    glGenVertexArrays(1, &triangleVAO);
    glGenBuffers(1, &triangleVBO);

    glBindVertexArray(triangleVAO);

    glBindBuffer(GL_ARRAY_BUFFER, triangleVBO);
    glBufferData(GL_ARRAY_BUFFER, sizeof(triangleVertices), triangleVertices, GL_STATIC_DRAW);

    // 位置属性 (location = 0): 3 个 float, 步长 6*float, 偏移 0
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 6 * sizeof(float), (void*)0);
    glEnableVertexAttribArray(0);

    // 颜色属性 (location = 1): 3 个 float, 步长 6*float, 偏移 3*float
    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 6 * sizeof(float), (void*)(3 * sizeof(float)));
    glEnableVertexAttribArray(1);

    glBindVertexArray(0);

    // -----------------------------------------------------------------------
    // 5. 准备矩形的顶点数据 + 索引数据（EBO）
    // -----------------------------------------------------------------------
    float rectVertices[] = {
        // 位置                // 颜色（未使用，但保持布局一致）
         0.5f,  0.5f, 0.0f,   1.0f, 0.5f, 0.2f,   // 右上
         0.5f, -0.5f, 0.0f,   1.0f, 0.5f, 0.2f,   // 右下
        -0.5f, -0.5f, 0.0f,   1.0f, 0.5f, 0.2f,   // 左下
        -0.5f,  0.5f, 0.0f,   1.0f, 0.5f, 0.2f    // 左上
    };

    unsigned int rectIndices[] = {
        0, 1, 3,   // 第一个三角形
        1, 2, 3    // 第二个三角形
    };

    unsigned int rectVAO, rectVBO, rectEBO;
    glGenVertexArrays(1, &rectVAO);
    glGenBuffers(1, &rectVBO);
    glGenBuffers(1, &rectEBO);

    glBindVertexArray(rectVAO);

    glBindBuffer(GL_ARRAY_BUFFER, rectVBO);
    glBufferData(GL_ARRAY_BUFFER, sizeof(rectVertices), rectVertices, GL_STATIC_DRAW);

    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, rectEBO);
    glBufferData(GL_ELEMENT_ARRAY_BUFFER, sizeof(rectIndices), rectIndices, GL_STATIC_DRAW);

    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 6 * sizeof(float), (void*)0);
    glEnableVertexAttribArray(0);

    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 6 * sizeof(float), (void*)(3 * sizeof(float)));
    glEnableVertexAttribArray(1);

    glBindVertexArray(0);

    // -----------------------------------------------------------------------
    // 6. 渲染循环
    // -----------------------------------------------------------------------
    std::cout << "按 空格键 切换三角形/矩形" << std::endl;
    std::cout << "按 W 键   切换线框/填充模式" << std::endl;
    std::cout << "按 ESC    退出" << std::endl;

    while (!glfwWindowShouldClose(window)) {
        glClearColor(0.15f, 0.15f, 0.18f, 1.0f);
        glClear(GL_COLOR_BUFFER_BIT);

        if (showTriangle) {
            glUseProgram(triangleProgram);
            glBindVertexArray(triangleVAO);
            glDrawArrays(GL_TRIANGLES, 0, 3);
        } else {
            glUseProgram(rectProgram);
            glBindVertexArray(rectVAO);
            glDrawElements(GL_TRIANGLES, 6, GL_UNSIGNED_INT, 0);
        }

        glfwSwapBuffers(window);
        glfwPollEvents();
    }

    // -----------------------------------------------------------------------
    // 7. 清理资源
    // -----------------------------------------------------------------------
    glDeleteVertexArrays(1, &triangleVAO);
    glDeleteBuffers(1, &triangleVBO);
    glDeleteVertexArrays(1, &rectVAO);
    glDeleteBuffers(1, &rectVBO);
    glDeleteBuffers(1, &rectEBO);
    glDeleteProgram(triangleProgram);
    glDeleteProgram(rectProgram);

    glfwTerminate();
    return 0;
}
