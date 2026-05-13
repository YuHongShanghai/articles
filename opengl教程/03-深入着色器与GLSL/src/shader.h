#ifndef SHADER_H
#define SHADER_H

#include <glad/glad.h>
#include <string>
#include <fstream>
#include <sstream>
#include <iostream>

class Shader {
public:
    unsigned int ID;

    Shader(const char* vertexPath, const char* fragmentPath) {
        std::string vertexCode   = readFile(vertexPath);
        std::string fragmentCode = readFile(fragmentPath);

        unsigned int vertex   = compileShader(GL_VERTEX_SHADER, vertexCode.c_str(), vertexPath);
        unsigned int fragment = compileShader(GL_FRAGMENT_SHADER, fragmentCode.c_str(), fragmentPath);

        ID = glCreateProgram();
        glAttachShader(ID, vertex);
        glAttachShader(ID, fragment);
        glLinkProgram(ID);
        checkLinkErrors(ID);

        glDeleteShader(vertex);
        glDeleteShader(fragment);
    }

    ~Shader() {
        glDeleteProgram(ID);
    }

    void use() const {
        glUseProgram(ID);
    }

    // --- uniform 设置函数 ---

    void setBool(const std::string& name, bool value) const {
        glUniform1i(getLocation(name), static_cast<int>(value));
    }

    void setInt(const std::string& name, int value) const {
        glUniform1i(getLocation(name), value);
    }

    void setFloat(const std::string& name, float value) const {
        glUniform1f(getLocation(name), value);
    }

    void setVec2(const std::string& name, float x, float y) const {
        glUniform2f(getLocation(name), x, y);
    }

    void setVec3(const std::string& name, float x, float y, float z) const {
        glUniform3f(getLocation(name), x, y, z);
    }

    void setVec4(const std::string& name, float x, float y, float z, float w) const {
        glUniform4f(getLocation(name), x, y, z, w);
    }

    void setMat4(const std::string& name, const float* value) const {
        glUniformMatrix4fv(getLocation(name), 1, GL_FALSE, value);
    }

private:
    GLint getLocation(const std::string& name) const {
        GLint loc = glGetUniformLocation(ID, name.c_str());
        if (loc == -1) {
            std::cerr << "[Shader] Warning: uniform '" << name
                      << "' not found (may be optimized out)." << std::endl;
        }
        return loc;
    }

    static std::string readFile(const char* path) {
        std::ifstream file(path);
        if (!file.is_open()) {
            std::cerr << "[Shader] ERROR: cannot open file: " << path << std::endl;
            return "";
        }
        std::stringstream ss;
        ss << file.rdbuf();
        return ss.str();
    }

    static unsigned int compileShader(GLenum type, const char* source, const char* path) {
        unsigned int shader = glCreateShader(type);
        glShaderSource(shader, 1, &source, nullptr);
        glCompileShader(shader);

        int success;
        glGetShaderiv(shader, GL_COMPILE_STATUS, &success);
        if (!success) {
            char infoLog[1024];
            glGetShaderInfoLog(shader, sizeof(infoLog), nullptr, infoLog);
            const char* typeName = (type == GL_VERTEX_SHADER) ? "VERTEX" : "FRAGMENT";
            std::cerr << "[Shader] " << typeName << " compilation failed (" << path << "):\n"
                      << infoLog << std::endl;
        }
        return shader;
    }

    static void checkLinkErrors(unsigned int program) {
        int success;
        glGetProgramiv(program, GL_LINK_STATUS, &success);
        if (!success) {
            char infoLog[1024];
            glGetProgramInfoLog(program, sizeof(infoLog), nullptr, infoLog);
            std::cerr << "[Shader] PROGRAM linking failed:\n" << infoLog << std::endl;
        }
    }
};

#endif
