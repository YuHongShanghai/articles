#ifndef SHADER_H
#define SHADER_H

#include <glad/glad.h>
#include <glm/glm.hpp>

#include <string>
#include <fstream>
#include <sstream>
#include <iostream>

class Shader
{
public:
    unsigned int ID;

    Shader(const char* vertexPath, const char* fragmentPath)
    {
        std::string vertexCode, fragmentCode;
        std::ifstream vShaderFile, fShaderFile;
        vShaderFile.exceptions(std::ifstream::failbit | std::ifstream::badbit);
        fShaderFile.exceptions(std::ifstream::failbit | std::ifstream::badbit);

        try {
            vShaderFile.open(vertexPath);
            fShaderFile.open(fragmentPath);
            std::stringstream vStream, fStream;
            vStream << vShaderFile.rdbuf();
            fStream << fShaderFile.rdbuf();
            vShaderFile.close();
            fShaderFile.close();
            vertexCode   = vStream.str();
            fragmentCode = fStream.str();
        } catch (std::ifstream::failure& e) {
            std::cout << "ERROR::SHADER::FILE_NOT_SUCCESSFULLY_READ: "
                      << e.what() << std::endl;
        }

        const char* vCode = vertexCode.c_str();
        const char* fCode = fragmentCode.c_str();
        unsigned int vertex, fragment;
        int success;
        char infoLog[512];

        vertex = glCreateShader(GL_VERTEX_SHADER);
        glShaderSource(vertex, 1, &vCode, NULL);
        glCompileShader(vertex);
        glGetShaderiv(vertex, GL_COMPILE_STATUS, &success);
        if (!success) {
            glGetShaderInfoLog(vertex, 512, NULL, infoLog);
            std::cout << "ERROR::SHADER::VERTEX::COMPILATION_FAILED\n"
                      << infoLog << std::endl;
        }

        fragment = glCreateShader(GL_FRAGMENT_SHADER);
        glShaderSource(fragment, 1, &fCode, NULL);
        glCompileShader(fragment);
        glGetShaderiv(fragment, GL_COMPILE_STATUS, &success);
        if (!success) {
            glGetShaderInfoLog(fragment, 512, NULL, infoLog);
            std::cout << "ERROR::SHADER::FRAGMENT::COMPILATION_FAILED\n"
                      << infoLog << std::endl;
        }

        ID = glCreateProgram();
        glAttachShader(ID, vertex);
        glAttachShader(ID, fragment);
        glLinkProgram(ID);
        glGetProgramiv(ID, GL_LINK_STATUS, &success);
        if (!success) {
            glGetProgramInfoLog(ID, 512, NULL, infoLog);
            std::cout << "ERROR::SHADER::PROGRAM::LINKING_FAILED\n"
                      << infoLog << std::endl;
        }

        glDeleteShader(vertex);
        glDeleteShader(fragment);
    }

    void use()  const { glUseProgram(ID); }
    void setBool (const std::string &n, bool  v) const { glUniform1i(glGetUniformLocation(ID, n.c_str()), (int)v); }
    void setInt  (const std::string &n, int   v) const { glUniform1i(glGetUniformLocation(ID, n.c_str()), v); }
    void setFloat(const std::string &n, float v) const { glUniform1f(glGetUniformLocation(ID, n.c_str()), v); }
    void setVec2 (const std::string &n, const glm::vec2 &v) const { glUniform2fv(glGetUniformLocation(ID, n.c_str()), 1, &v[0]); }
    void setVec3 (const std::string &n, const glm::vec3 &v) const { glUniform3fv(glGetUniformLocation(ID, n.c_str()), 1, &v[0]); }
    void setVec3 (const std::string &n, float x, float y, float z) const { glUniform3f(glGetUniformLocation(ID, n.c_str()), x, y, z); }
    void setVec4 (const std::string &n, const glm::vec4 &v) const { glUniform4fv(glGetUniformLocation(ID, n.c_str()), 1, &v[0]); }
    void setMat2 (const std::string &n, const glm::mat2 &m) const { glUniformMatrix2fv(glGetUniformLocation(ID, n.c_str()), 1, GL_FALSE, &m[0][0]); }
    void setMat3 (const std::string &n, const glm::mat3 &m) const { glUniformMatrix3fv(glGetUniformLocation(ID, n.c_str()), 1, GL_FALSE, &m[0][0]); }
    void setMat4 (const std::string &n, const glm::mat4 &m) const { glUniformMatrix4fv(glGetUniformLocation(ID, n.c_str()), 1, GL_FALSE, &m[0][0]); }
};

#endif
