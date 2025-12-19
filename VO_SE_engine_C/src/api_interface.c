#include "api_interface.h"
#define DR_WAV_IMPLEMENTATION
#include "dr_wav.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#include <stdlib.h>
#include <stddef.h>
#include "api_interface.h" // 構造体定義が含まれるヘッダー

#ifdef _WIN32
  #define EXPORT __declspec(dllexport)
#else
  #define EXPORT __attribute__((visibility("default"))) // macOS/Linuxで確実に公開
#endif


// --- 内部管理用：音源ライブラリ構造体 ---
typedef struct {
    char phoneme_name[32];
    float* samples;
    drwav_uint64 sample_count;
} PhonemeSample;

static PhonemeSample* g_lib = NULL;
static int g_lib_count = 0;
static int g_lib_capacity = 100;

// エンジンの初期化
void vse_initialize() {
    g_lib = (PhonemeSample*)malloc(sizeof(PhonemeSample) * g_lib_capacity);
    g_lib_count = 0;
}

// エンジンの終了処理
void vse_shutdown() {
    if (g_lib) {
        for (int i = 0; i < g_lib_count; i++) {
            if (g_lib[i].samples) drwav_free(g_lib[i].samples, NULL);
        }
        free(g_lib);
        g_lib = NULL;
    }
}

// api_interface.c の init_engine 部分を以下に書き換え
#include <dirent.h> // ディレクトリ走査用

int init_engine(const char* char_id, const char* audio_dir) {
    vse_shutdown(); // 既存の音源があれば解放
    vse_initialize();

    DIR *dir;
    struct dirent *ent;
    if ((dir = opendir(audio_dir)) != NULL) {
        while ((ent = readdir(dir)) != NULL) {
            // .wavファイルのみを対象にする
            if (strstr(ent->d_name, ".wav") != NULL) {
                char filepath[512];
                snprintf(filepath, sizeof(filepath), "%s/%s", audio_dir, ent->d_name);

                unsigned int channels;
                unsigned int sampleRate;
                drwav_uint64 totalPCMFrameCount;
                
                // WAV読み込み
                float* pSampleData = drwav_open_file_and_read_pcm_frames_f32(
                    filepath, &channels, &sampleRate, &totalPCMFrameCount, NULL);

                if (pSampleData) {
                    // 音素名としてファイル名（拡張子なし）を登録
                    char ph_name[64];
                    strncpy(ph_name, ent->d_name, strlen(ent->d_name) - 4);
                    ph_name[strlen(ent->d_name) - 4] = '\0';

                    // ライブラリに登録
                    strcpy(g_lib[g_lib_count].phoneme_name, ph_name);
                    g_lib[g_lib_count].samples = pSampleData;
                    g_lib[g_lib_count].sample_count = totalPCMFrameCount;
                    g_lib_count++;
                    
                    printf("C-Engine: Loaded phoneme [%s] (%llu samples)\n", ph_name, totalPCMFrameCount);
                }
            }
        }
        closedir(dir);
    } else {
        printf("C-Engine Error: Could not open directory %s\n", audio_dir);
        return -1;
    }
    return 0;
}

// ヘルパー：音素名から波形を検索
static PhonemeSample* find_phoneme(const char* name) {
    for (int i = 0; i < g_lib_count; i++) {
        if (strcmp(g_lib[i].phoneme_name, name) == 0) return &g_lib[i];
    }
    return NULL;
}

// メモリ解放：Python側から呼ばれる
void vse_free_buffer(float* ptr) {
    if (ptr) free(ptr);
}

// 線形補間リサンプリングとクロスフェードを伴うノート合成
void process_note_to_buffer(
    CNoteEvent note, 
    CPitchEvent* pitch_events, 
    int pitch_event_count, 
    float* out_buffer, 
    int buffer_len,
    int sample_rate
) {
    if (note.phoneme_count <= 0) return;

    int samples_per_phoneme = buffer_len / note.phoneme_count;
    int current_pos = 0;
    int fade_len = (int)(sample_rate * 0.005); // 5msクロスフェード

    for (int p = 0; p < note.phoneme_count; p++) {
        PhonemeSample* ph = find_phoneme(note.phonemes[p]);
        if (!ph) {
            current_pos += samples_per_phoneme;
            continue;
        }

        // --- リサンプリング (np.interp 相当) ---
        float* resampled = (float*)malloc(sizeof(float) * samples_per_phoneme);
        float ratio = (float)ph->sample_count / samples_per_phoneme;
        
        for (int i = 0; i < samples_per_phoneme; i++) {
            float src_idx = i * ratio;
            int idx = (int)src_idx;
            float frac = src_idx - idx;
            if (idx + 1 < ph->sample_count) {
                resampled[i] = ph->samples[idx] * (1.0f - frac) + ph->samples[idx + 1] * frac;
            } else {
                resampled[i] = ph->samples[idx];
            }
        }

        // --- 波形接続（クロスフェード処理） ---
        if (p > 0 && current_pos >= fade_len) {
            int overlap_start = current_pos - fade_len;
            for (int i = 0; i < fade_len; i++) {
                float f_in = (float)i / fade_len;
                float f_out = 1.0f - f_in;
                out_buffer[overlap_start + i] = (out_buffer[overlap_start + i] * f_out) + (resampled[i] * f_in);
            }
            // 残りのコピー
            int remain = samples_per_phoneme - fade_len;
            if (current_pos + remain <= buffer_len) {
                memcpy(&out_buffer[current_pos], &resampled[fade_len], sizeof(float) * remain);
            }
        } else {
            // 初回の音素はそのままコピー
            int copy_len = (current_pos + samples_per_phoneme > buffer_len) ? (buffer_len - current_pos) : samples_per_phoneme;
            memcpy(&out_buffer[current_pos], resampled, sizeof(float) * copy_len);
        }

        current_pos += samples_per_phoneme;
        free(resampled);
    }

    // ベロシティ(音量)適用
    float amp = note.velocity / 127.0f;
    for (int i = 0; i < buffer_len; i++) out_buffer[i] *= amp;
}

// 一括合成 (request_synthesis_full から呼ばれる)
float* vse_synthesize_track(
    CNoteEvent* notes, int note_count,
    CPitchEvent* pitch_events, int pitch_event_count,
    float start_time_sec, float end_time_sec,
    int* out_audio_length
) {
    int sr = 44100;
    *out_audio_length = (int)((end_time_sec - start_time_sec) * sr);
    if (*out_audio_length <= 0) return NULL;

    float* full_buffer = (float*)calloc(*out_audio_length, sizeof(float));

    for (int n = 0; n < note_count; n++) {
        int n_start = (int)((notes[n].start_time - start_time_sec) * sr);
        int n_len = (int)(notes[n].duration * sr);

        if (n_start < 0 || n_start >= *out_audio_length) continue;

        float* note_buf = (float*)calloc(n_len, sizeof(float));
        process_note_to_buffer(notes[n], pitch_events, pitch_event_count, note_buf, n_len, sr);

        // トラックへのミックス（加算）
        for (int i = 0; i < n_len; i++) {
            if (n_start + i < *out_audio_length) {
                full_buffer[n_start + i] += note_buf[i];
            }
        }
        free(note_buf);
    }
    return full_buffer;
}


// --- 修正された窓口関数 ---
EXPORT float* request_synthesis_full(SynthesisRequest request, int* out_sample_count) {
    float max_time = 0.0f;
    for (int i = 0; i < request.note_count; i++) {
        float end = request.notes[i].start_time + request.notes[i].duration;
        if (end > max_time) {
            max_time = end;
        }
    }
    max_time += 0.5f;

    // 変数宣言はここ1回だけなので、先ほどのエラーは出ません
    float* audio_data = vse_synthesize_track(
        request.notes, 
        request.note_count, 
        request.pitch_events, 
        request.pitch_event_count, 
        0.0f, 
        max_time, 
        out_sample_count
    );

    return audio_data;
}

EXPORT void free_audio_buffer(float* ptr) {
    if (ptr != NULL) {
        free(ptr);
    }
}
