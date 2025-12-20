#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <dirent.h>
#define DR_WAV_IMPLEMENTATION
#include "dr_wav.h"
#include "api_interface.h"
#include "synthesizer_core.h"

// --- 音源ライブラリ管理 ---
typedef struct {
    char name[64];
    float* samples;
    drwav_uint64 count;
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

// Pythonとの直接の連絡口
EXPORT float* request_synthesis_full(SynthesisRequest request, int* out_sample_count) {
    // 全体の長さを計算 (最後の音符の終了時間を探す)
    float max_time = 0.0f;
    for (int i = 0; i < request.note_count; i++) {
        float end = request.notes[i].start_time + request.notes[i].duration;
        if (end > max_time) max_time = end;
    }
    max_time += 0.5f; // 余韻

    return vse_synthesize_track(
        request.notes, request.note_count,
        request.pitch_events, request.pitch_event_count,
        0.0f, max_time,
        out_sample_count
    );
    
    return audio_data;
}
