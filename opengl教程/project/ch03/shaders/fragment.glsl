#version 330 core

in vec3 vertexColor;
out vec4 FragColor;

uniform float uTime;
uniform vec3  uTintColor;

void main() {
    float pulse = (sin(uTime * 2.0) + 1.0) * 0.5;
    vec3 finalColor = mix(vertexColor, uTintColor, pulse);
    FragColor = vec4(finalColor, 1.0);
}
