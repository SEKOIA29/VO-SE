#include "synthesizer_core.h"
#include <math.h>
#include <string.h>

// MIDIノート番号を周波数(Hz)に変換
float note_to_hz(int note_number) {
    return 440.0f * powf(2.0f, (note_number - 69) / 12.0f);
}

// ピッチベンド値から周波数倍率を計算 (2025年最新の歌声合成で標準的な±2半音設定)
float get_pitch_multiplier(float time, CPitchEvent* events, int count) {
    if (count == 0 || events == NULL) return 1.0f;
    
    int val = 0;
    for (int i = 0; i < count; i++) {
        if (events[i].time <= time) {
            val = events[i].value;
        } else {
            break;
        }
    }
    // ピッチベンド値を半音単位の倍率に変換
    float semitones = (val / 8192.0f) * 2.0f; 
    return powf(2.0f, semitones / 12.0f);
}

// 線形補間リサンプリングの実装
void resample_linear(float* src, int src_len, float* dest, int dest_len) {
    if (dest_len <= 0) return;
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

// クロスフェード接続の実装
void apply_crossfade(float* out_buffer, int current_pos, float* new_sample, int sample_len, int fade_samples) {
    for (int i = 0; i < fade_samples; i++) {
        float f_in = (float)i / (float)fade_samples;
        float f_out = 1.0f - f_in;
        // 重なり部分を混ぜる
        out_buffer[current_pos + i] = (out_buffer[current_pos + i] * f_out) + (new_sample[i] * f_in);
    }
    // フェード以降の残りをコピー
    if (sample_len > fade_samples) {
        memcpy(&out_buffer[current_pos + fade_samples], &new_sample[fade_samples], sizeof(float) * (sample_len - fade_samples));
    }
}
