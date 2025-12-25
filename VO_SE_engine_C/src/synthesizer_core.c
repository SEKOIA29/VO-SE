#include "synthesizer_core.h"
#include <math.h>
#include <string.h>
#include <stdlib.h>
#include "../include/synthesizer_core.h"

#include "../include/synthesizer_core.h"
#define DR_WAV_IMPLEMENTATION
#include "../include/dr_wav.h" // WAV書き出しライブラリ

// 書き出し用の設定
void execute_render_to_file(const char* filename, NoteEvent* notes, int note_count) {
    drwav_data_format format;
    format.container = drwav_container_riff;
    format.format = DR_WAV_FORMAT_PCM;
    format.channels = 1;
    format.sampleRate = 44100;
    format.bitsPerSample = 16;

    drwav wav;
    if (!drwav_init_file_write(&wav, filename, &format, NULL)) return;

    for (int i = 0; i < note_count; i++) {
        // ノートごとの音程（周波数）からリサンプリング倍率を計算
        float ratio = notes[i].frequency / 440.0f; 
        
        // 元の音素データを読み込み、倍率（ratio）に基づいて
        // 新しいピッチの波形を生成し、wavファイルへ書き込む
        render_and_write_pcm(&wav, notes[i].lyric, ratio, notes[i].duration);
    }

    drwav_uninit(&wav);
    printf("C-Engine: %s へ書き出し完了しました。\n", filename);
}




void update_resampling_ratio(float target_hz) {
    float original_hz = 440.0f; // 元の録音データの基準音程
    float ratio = target_hz / original_hz;
    
    // この ratio (倍率) を使って、
    // 波形データの読み飛ばし間隔（リサンプリング歩進値）を決定する
    set_engine_playback_speed(ratio);
}


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
