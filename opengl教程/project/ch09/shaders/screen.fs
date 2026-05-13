#version 330 core
out vec4 FragColor;

in vec2 TexCoords;

uniform sampler2D screenTexture;
uniform int effectType;  // 0=无, 1=反相, 2=灰度, 3=锐化, 4=模糊, 5=边缘检测

void main()
{
    vec3 col = texture(screenTexture, TexCoords).rgb;

    if (effectType == 0)
    {
        FragColor = vec4(col, 1.0);
    }
    else if (effectType == 1)
    {
        // 反相
        FragColor = vec4(1.0 - col, 1.0);
    }
    else if (effectType == 2)
    {
        // 灰度
        float average = 0.2126 * col.r + 0.7152 * col.g + 0.0722 * col.b;
        FragColor = vec4(average, average, average, 1.0);
    }
    else
    {
        // 核效果
        float offset = 1.0 / 300.0;
        vec2 offsets[9] = vec2[](
            vec2(-offset,  offset), vec2(0.0,  offset), vec2(offset,  offset),
            vec2(-offset,  0.0),    vec2(0.0,  0.0),    vec2(offset,  0.0),
            vec2(-offset, -offset), vec2(0.0, -offset), vec2(offset, -offset)
        );

        float kernel[9];

        if (effectType == 3)
        {
            // 锐化
            kernel = float[](
                -1, -1, -1,
                -1,  9, -1,
                -1, -1, -1
            );
        }
        else if (effectType == 4)
        {
            // 模糊
            kernel = float[](
                1.0/16, 2.0/16, 1.0/16,
                2.0/16, 4.0/16, 2.0/16,
                1.0/16, 2.0/16, 1.0/16
            );
        }
        else
        {
            // 边缘检测
            kernel = float[](
                1,  1,  1,
                1, -8,  1,
                1,  1,  1
            );
        }

        vec3 sampleTex[9];
        for (int i = 0; i < 9; i++)
            sampleTex[i] = vec3(texture(screenTexture,
                                        TexCoords + offsets[i]));

        vec3 result = vec3(0.0);
        for (int i = 0; i < 9; i++)
            result += sampleTex[i] * kernel[i];

        FragColor = vec4(result, 1.0);
    }
}
