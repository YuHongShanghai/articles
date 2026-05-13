#ifndef CAMERA_H
#define CAMERA_H

#include <glad/glad.h>
#include <glm/glm.hpp>
#include <glm/gtc/matrix_transform.hpp>

enum Camera_Movement { FORWARD, BACKWARD, LEFT, RIGHT };

const float YAW         = -90.0f;
const float PITCH       =  0.0f;
const float SPEED       =  2.5f;
const float SENSITIVITY =  0.1f;
const float ZOOM        =  45.0f;

class Camera
{
public:
    glm::vec3 Position, Front, Up, Right, WorldUp;
    float Yaw, Pitch, MovementSpeed, MouseSensitivity, Zoom;

    Camera(glm::vec3 position = glm::vec3(0.0f, 0.0f, 3.0f),
           glm::vec3 up = glm::vec3(0.0f, 1.0f, 0.0f),
           float yaw = YAW, float pitch = PITCH)
        : Front(glm::vec3(0.0f, 0.0f, -1.0f)),
          MovementSpeed(SPEED), MouseSensitivity(SENSITIVITY), Zoom(ZOOM)
    {
        Position = position; WorldUp = up;
        Yaw = yaw; Pitch = pitch;
        updateCameraVectors();
    }

    glm::mat4 GetViewMatrix() const
    { return glm::lookAt(Position, Position + Front, Up); }

    void ProcessKeyboard(Camera_Movement dir, float dt)
    {
        float v = MovementSpeed * dt;
        if (dir == FORWARD)  Position += Front * v;
        if (dir == BACKWARD) Position -= Front * v;
        if (dir == LEFT)     Position -= Right * v;
        if (dir == RIGHT)    Position += Right * v;
    }

    void ProcessMouseMovement(float xoff, float yoff, bool constrain = true)
    {
        xoff *= MouseSensitivity; yoff *= MouseSensitivity;
        Yaw += xoff; Pitch += yoff;
        if (constrain) { if (Pitch > 89.0f) Pitch = 89.0f; if (Pitch < -89.0f) Pitch = -89.0f; }
        updateCameraVectors();
    }

    void ProcessMouseScroll(float yoff)
    { Zoom -= yoff; if (Zoom < 1.0f) Zoom = 1.0f; if (Zoom > 45.0f) Zoom = 45.0f; }

private:
    void updateCameraVectors()
    {
        glm::vec3 f;
        f.x = cos(glm::radians(Yaw)) * cos(glm::radians(Pitch));
        f.y = sin(glm::radians(Pitch));
        f.z = sin(glm::radians(Yaw)) * cos(glm::radians(Pitch));
        Front = glm::normalize(f);
        Right = glm::normalize(glm::cross(Front, WorldUp));
        Up    = glm::normalize(glm::cross(Right, Front));
    }
};

#endif
