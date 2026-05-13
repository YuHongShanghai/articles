#ifndef MODEL_H
#define MODEL_H

// 注意：使用此头文件的 main.cpp 需在 #include 之前定义：
//   #define STB_IMAGE_IMPLEMENTATION
// 以确保 stb_image 的实现只被编译一次

#include <glad/glad.h>
#include <glm/glm.hpp>
#include <glm/gtc/matrix_transform.hpp>

#include <assimp/Importer.hpp>
#include <assimp/scene.h>
#include <assimp/postprocess.h>

#include "stb_image.h"

#include <string>
#include <vector>
#include <iostream>
#include <cstring>

#include "shader.h"
#include "mesh.h"

unsigned int TextureFromFile(const char *path, const std::string &directory);

class Model
{
public:
    std::vector<Texture> textures_loaded;
    std::vector<Mesh>    meshes;
    std::string          directory;

    Model(const std::string &path) { loadModel(path); }

    void Draw(const Shader &shader) const
    {
        for (const auto &mesh : meshes)
            mesh.Draw(shader);
    }

    void DrawDepthOnly() const
    {
        for (const auto &mesh : meshes)
            mesh.DrawDepthOnly();
    }

private:
    void loadModel(const std::string &path)
    {
        Assimp::Importer importer;
        const aiScene* scene = importer.ReadFile(path,
            aiProcess_Triangulate      |
            aiProcess_GenSmoothNormals |
            aiProcess_FlipUVs          |
            aiProcess_CalcTangentSpace);

        if (!scene || scene->mFlags & AI_SCENE_FLAGS_INCOMPLETE
            || !scene->mRootNode)
        {
            std::cout << "ERROR::ASSIMP:: "
                      << importer.GetErrorString() << std::endl;
            return;
        }

        directory = path.substr(0, path.find_last_of('/'));
        processNode(scene->mRootNode, scene);
    }

    void processNode(aiNode *node, const aiScene *scene)
    {
        for (unsigned int i = 0; i < node->mNumMeshes; i++)
            meshes.push_back(processMesh(scene->mMeshes[node->mMeshes[i]], scene));
        for (unsigned int i = 0; i < node->mNumChildren; i++)
            processNode(node->mChildren[i], scene);
    }

    Mesh processMesh(aiMesh *mesh, const aiScene *scene)
    {
        std::vector<Vertex>       vertices;
        std::vector<unsigned int> indices;
        std::vector<Texture>      textures;

        for (unsigned int i = 0; i < mesh->mNumVertices; i++)
        {
            Vertex v;
            v.Position = { mesh->mVertices[i].x,
                           mesh->mVertices[i].y,
                           mesh->mVertices[i].z };
            if (mesh->HasNormals())
                v.Normal = { mesh->mNormals[i].x,
                             mesh->mNormals[i].y,
                             mesh->mNormals[i].z };
            if (mesh->mTextureCoords[0])
                v.TexCoords = { mesh->mTextureCoords[0][i].x,
                                mesh->mTextureCoords[0][i].y };
            else
                v.TexCoords = { 0.0f, 0.0f };
            vertices.push_back(v);
        }

        for (unsigned int i = 0; i < mesh->mNumFaces; i++) {
            aiFace face = mesh->mFaces[i];
            for (unsigned int j = 0; j < face.mNumIndices; j++)
                indices.push_back(face.mIndices[j]);
        }

        aiMaterial* mat = scene->mMaterials[mesh->mMaterialIndex];
        auto diffuse  = loadMaterialTextures(mat, aiTextureType_DIFFUSE,  "texture_diffuse");
        textures.insert(textures.end(), diffuse.begin(), diffuse.end());
        auto specular = loadMaterialTextures(mat, aiTextureType_SPECULAR, "texture_specular");
        textures.insert(textures.end(), specular.begin(), specular.end());

        return Mesh(std::move(vertices), std::move(indices), std::move(textures));
    }

    std::vector<Texture> loadMaterialTextures(aiMaterial *mat,
                                               aiTextureType type,
                                               const std::string &typeName)
    {
        std::vector<Texture> textures;
        for (unsigned int i = 0; i < mat->GetTextureCount(type); i++)
        {
            aiString str;
            mat->GetTexture(type, i, &str);

            bool skip = false;
            for (const auto &loaded : textures_loaded) {
                if (std::strcmp(loaded.path.data(), str.C_Str()) == 0) {
                    textures.push_back(loaded);
                    skip = true;
                    break;
                }
            }
            if (!skip) {
                Texture tex;
                tex.id   = TextureFromFile(str.C_Str(), directory);
                tex.type = typeName;
                tex.path = str.C_Str();
                textures.push_back(tex);
                textures_loaded.push_back(tex);
            }
        }
        return textures;
    }
};

inline unsigned int TextureFromFile(const char *path, const std::string &directory)
{
    std::string filename = directory + '/' + std::string(path);

    unsigned int textureID;
    glGenTextures(1, &textureID);

    int width, height, nrComponents;
    unsigned char *data = stbi_load(filename.c_str(),
                                    &width, &height, &nrComponents, 0);
    if (data)
    {
        GLenum format = GL_RGB;
        if      (nrComponents == 1) format = GL_RED;
        else if (nrComponents == 3) format = GL_RGB;
        else if (nrComponents == 4) format = GL_RGBA;

        glBindTexture(GL_TEXTURE_2D, textureID);
        glTexImage2D(GL_TEXTURE_2D, 0, format, width, height,
                     0, format, GL_UNSIGNED_BYTE, data);
        glGenerateMipmap(GL_TEXTURE_2D);

        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR);
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);
    }
    else
    {
        std::cout << "Texture failed to load at path: "
                  << filename << std::endl;
    }
    stbi_image_free(data);
    return textureID;
}

#endif
