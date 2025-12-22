#include "synthesizer_core.h"
#include <math.h>
#include <string.h>



typedef struct {
    char name[32];      // "a", "i", "u" など
    float* samples;      // WAVの生データ
    uint64_t count;      // サンプル数
} Phoneme;

Phoneme g_library[128];  // 最大128音素まで保持
int g_phoneme_count = 0;

// キャラクター切り替え時に呼ばれる
EXPORT int init_engine(const char* char_id, const char* audio_dir) {
    // 1. 今まで読み込んでいた音源をメモリから消す（メモリリーク防止）
    for (int i = 0; i < g_phoneme_count; i++) {
        if (g_library[i].samples) free(g_library[i].samples);
    }
    g_phoneme_count = 0;

    // 2. audio_dir をスキャンして新しいWAVを読み込む
    // (ここに前述の dr_wav を使ったロード処理を書く)
    printf("C-Engine: キャラクター %s の音源を %s から読み込みます...\n", char_id, audio_dir);
    
    return 0; // 成功
}




// --- ユーティリティ関数 ---
void resample_linear(const float* input, int input_len, float* output, int output_len) {
    for (int i = 0; i < output_len; i++) {
        float t = (float)i * (input_len - 1) / (output_len - 1);
        int t_int = (int)t;
        float t_frac = t - t_int;
        if (t_int + 1 < input_len) {
            output[i] = input[t_int] * (1.0f - t_frac) + input[t_int + 1] * t_frac;
        } else {
            output[i] = input[t_int];
        }
    }
}   
void apply_crossfade(float* dest, int dest_start, const float* src, int src_len, int fade_len) {
    for (int i = 0; i < src_len; i++) {
        if (i < fade_len) {
            float fade_in = (float)i / fade_len;
            float fade_out = 1.0f - fade_in;
            dest[dest_start + i] = dest[dest_start + i] * fade_out + src[i] * fade_in;
        } else if (i >= src_len - fade_len) {
            float fade_out = (float)(src_len - i) / fade_len;
            float fade_in = 1.0f - fade_out;
            dest[dest_start + i] = dest[dest_start + i] * fade_out + src[i] * fade_in;
        } else {
            dest[dest_start + i] += src[i];
        }
    }
}


// --- 音源ライブラリ管理 ---
typedef struct {
    char name[256];   // ← ここを "name" ではなく "name[256]" に修正
    float* samples;
    uint64_t count;   // 先ほどの修正通り count に統一
} Phoneme;



static Phoneme g_lib[128];
static int g_lib_cnt = 0;

EXPORT int init_engine(const char* char_id, const char* audio_dir) {
    g_lib_cnt = 0;
    DIR *dir = opendir(audio_dir);
    if (!dir) return -1;
    struct dirent *ent;
    while ((ent = readdir(dir)) != NULL) {
        if (strstr(ent->d_name, ".wav")) {
            char path[512];
            snprintf(path, sizeof(path), "%s/%s", audio_dir, ent->d_name);
            unsigned int c, sr;
            drwav_uint64 frame_cnt;
            float* data = drwav_open_file_and_read_pcm_frames_f32(path, &c, &sr, &frame_cnt, NULL);
            if (data) {
                strncpy(g_lib[g_lib_cnt].name, ent->d_name, strlen(ent->d_name) - 4);
                g_lib[g_lib_cnt].samples = data;
                g_lib[g_lib_cnt].count = frame_cnt;
                g_lib_cnt++;
            }
        }
    }
    closedir(dir);
    return 0;
}

// --- 合成核心部 ---
float* vse_synthesize_track(CNoteEvent* notes, int note_cnt, CPitchEvent* p_events, int p_cnt, float start, float end, int* out_len) {
    int sr = 44100;
    *out_len = (int)((end - start) * sr);
    float* buffer = (float*)calloc(*out_len, sizeof(float));
    int fade_s = (int)(sr * 0.005); // 5ms

    for (int i = 0; i < note_cnt; i++) {
        int n_start = (int)((notes[i].start_time - start) * sr);
        int n_len = (int)(notes[i].duration * sr);
        if (n_start < 0 || n_start + n_len > *out_len || notes[i].phoneme_count == 0) continue;

        int ph_len = n_len / notes[i].phoneme_count;
        for (int p = 0; p < notes[i].phoneme_count; p++) {
            Phoneme* target = NULL;
            for (int k = 0; k < g_lib_cnt; k++) {
                if (strcmp(g_lib[k].name, notes[i].phonemes[p]) == 0) { target = &g_lib[k]; break; }
            }
            if (!target) continue;

            float* tmp = (float*)malloc(sizeof(float) * ph_len);
            resample_linear(target->samples, (int)target->count, tmp, ph_len);
            
            float amp = notes[i].velocity / 127.0f;
            for (int j = 0; j < ph_len; j++) tmp[j] *= amp;

            int current_p = n_start + (p * ph_len);
            if (p > 0) apply_crossfade(buffer, current_p, tmp, ph_len, fade_s);
            else memcpy(&buffer[current_p], tmp, sizeof(float) * ph_len);
            free(tmp);
        }
    }
    return buffer;
}

// --- Pythonからのメイン窓口 ---
EXPORT float* request_synthesis_full(SynthesisRequest request, int* out_sample_count) {
    float max_time = 0.0f;

    // 終了時間を計算
    for (int i = 0; i < request.note_count; i++) {
        float end = request.notes[i].start_time + request.notes[i].duration;
        if (end > max_time) {
            max_time = end;
        }
    }
    max_time += 1.0f; // バッファに余裕を持たせる

    return vse_synthesize_track(
        request.notes, 
        request.note_count,
        request.pitch_events, 
        request.pitch_event_count,
        0.0f, 
        max_time,
        out_sample_count
    );
}


// --- 合成結果の解放 ---       
EXPORT void free_synthesized_audio(float* audio_data) {
    if (audio_data) {
        free(audio_data);
    }
}
// --- エンジン終了処理 ---
EXPORT void shutdown_engine() {
    for (int i = 0; i < g_lib_cnt; i++) {
        if (g_lib[i].samples) {
            free(g_lib[i].samples);
            g_lib[i].samples = NULL;
        }
    }
    g_lib_cnt = 0;
} 
