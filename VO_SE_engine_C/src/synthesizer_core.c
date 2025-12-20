#include "synthesizer_core.h"
#include <math.h>
#include <string.h>
#include <stdlib.h>

// 周波数計算
float note_to_hz(int note_number) {
    return 440.0f * powf(2.0f, (note_number - 69) / 12.0f);
}

// リサンプリング（線形補間）
void resample_linear(float* src, int src_len, float* dest, int dest_len) {
    if (dest_len <= 0 || src_len <= 0) return;
    float ratio = (float)src_len / (float)dest_len;
    for (int i = 0; i < dest_len; i++) {
        float pos = i * ratio;
        int idx = (int)pos;
        float frac = pos - idx;
        if (idx + 1 < src_len) {
            dest[i] = src[idx] * (1.0f - frac) + src[idx + 1] * frac;
        } else {
            dest[i] = src[idx];
        }
    }
}

// クロスフェード接続
void apply_crossfade(float* out_buffer, int current_pos, float* new_sample, int sample_len, int fade_samples) {
    for (int i = 0; i < fade_samples; i++) {
        float f_in = (float)i / (float)fade_samples;
        float f_out = 1.0f - f_in;
        out_buffer[current_pos + i] = (out_buffer[current_pos + i] * f_out) + (new_sample[i] * f_in);
    }
    if (sample_len > fade_samples) {
        memcpy(&out_buffer[current_pos + fade_samples], &new_sample[fade_samples], sizeof(float) * (sample_len - fade_samples));
    }
}
