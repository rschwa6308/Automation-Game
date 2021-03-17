#version 300 es
precision mediump float;
uniform sampler2D Texture;
in vec2 v_text;

out vec4 color;

void main() {
    vec2 center = vec2(0.5, 0.5);
    vec2 off_center = v_text - center;

    off_center *= 1.0 + 0.8 * pow(abs(off_center.yx), vec2(2.5));

    vec2 v_text2 = center + off_center;

    if (v_text2.x > 1.0 || v_text2.x < 0.0 ||
        v_text2.y > 1.0 || v_text2.y < 0.0) {

        color = vec4(0.0, 0.0, 0.0, 1.0);
    } else {

        color=vec4(texture(Texture,v_text2).rgb,1.);
        // float fv = fract(v_text2.y*float(textureSize(Texture, 0).y)/4.0);
        // fv = min(1.0, 0.8 + 0.5 * min(fv, 1.0 - fv));
        // color.rgb*=fv;

        // float c_off=fract(v_text.x*(1.0-v_text.y));
        // color+=vec4(c_off/1.5);
    }
}