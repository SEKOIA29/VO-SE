#define DR_WAV_IMPLEMENTATION
#include "api_interface.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include "dr_wav.h"
#include "api_interface.h"

// 音素データを保持する内部ハッシュマップの代わりの構造体
typedef struct {
    char phoneme_name[32];
    float* samples;
    int sample_count;
} PhonemeLibrary;

static PhonemeLibrary* g_lib = NULL;
static int g_lib_count = 0;

// エンジンの初期化
int init_engine(const char* char_id, const char* audio_dir) {
    // 実際にはここで audio_dir 内のWAVをスキャンして g_lib にロードします。
    // 今回はスケルトンとして初期化成功を返します。
    vse_initialize();
    printf("Engine initialized for character: %s, dir: %s\n", char_id, audio_dir);
    return 0;
}

void vse_initialize() {
    g_lib = malloc(sizeof(PhonemeLibrary) * 100); // 最大100音素
    g_lib_count = 0;
}

void vse_shutdown() {
    for (int i = 0; i < g_lib_count; i++) {
        free(g_lib[i].samples);
    }
    free(g_lib);
    g_lib = NULL;
}

// ヘルパー：音素名から波形を取得
static PhonemeLibrary* find_phoneme(const char* name) {
    for (int i = 0; i < g_lib_count; i++) {
        if (strcmp(g_lib[i].phoneme_name, name) == 0) return &g_lib[i];
    }
    return NULL;
}

// 2. 合成：単体ノートをバッファに書き込む（Python版の移植）
void process_note_to_buffer(
    CNoteEvent note, 
    CPitchEvent* pitch_events, 
    int pitch_event_count, 
    float* out_buffer, 
    int buffer_len,
    int sample_rate
) {
    if (note.phoneme_count == 0) return;

    int samples_per_phoneme = buffer_len / note.phoneme_count;
    int current_pos = 0;

    for (int p = 0; p < note.phoneme_count; p++) {
        PhonemeLibrary* lib = find_phoneme(note.phonemes[p]);
        if (!lib) {
            current_pos += samples_per_phoneme;
            continue;
        }

        // --- リサンプリング (Pythonのnp.interp相当) ---
        int target_len = samples_per_phoneme;
        float* processed_sample = (float*)malloc(sizeof(float) * target_len);
        
        for (int i = 0; i < target_len; i++) {
            float src_idx = (float)i * lib->sample_count / target_len;
            int idx = (int)src_idx;
            float frac = src_idx - idx;
            if (idx + 1 < lib->sample_count) {
                processed_sample[i] = lib->samples[idx] * (1.0f - frac) + lib->samples[idx+1] * frac;
            } else {
                processed_sample[i] = lib->samples[idx];
            }
        }

        // --- クロスフェード (5ms) ---
        int fade_len = (int)(sample_rate * 0.005);
        if (p > 0 && current_pos >= fade_len) {
            int overlap_pos = current_pos - fade_len;
            for (int i = 0; i < fade_len; i++) {
                float f_in = (float)i / fade_len;
                float f_out = 1.0f - f_in;
                out_buffer[overlap_pos + i] = (out_buffer[overlap_pos + i] * f_out) + (processed_sample[i] * f_in);
            }
            // フェード分を飛ばしてコピー
            int remaining = target_len - fade_len;
            if (current_pos + remaining <= buffer_len) {
                memcpy(&out_buffer[current_pos], &processed_sample[fade_len], sizeof(float) * remaining);
            }
        } else {
            // 最初またはフェードなし
            int copy_len = (current_pos + target_len > buffer_len) ? (buffer_len - current_pos) : target_len;
            memcpy(&out_buffer[current_pos], processed_sample, sizeof(float) * copy_len);
        }

        current_pos += target_len;
        free(processed_sample);
    }

    // ベロシティ適用
    float vol = note.velocity / 127.0f;
    for (int i = 0; i < buffer_len; i++) out_buffer[i] *= vol;
}

// 一括合成実行
float* vse_synthesize_track(
    CNoteEvent* notes, int note_count,
    CPitchEvent* pitch_events, int pitch_event_count,
    float start_time_sec, float end_time_sec,
    int* out_audio_length
) {
    int sr = 44100;
    float duration = end_time_sec - start_time_sec;
    *out_audio_length = (int)(duration * sr);
    float* full_buffer = (float*)calloc(*out_audio_length, sizeof(float));

    for (int n = 0; n < note_count; n++) {
        CNoteEvent note = notes[n];
        int note_start_idx = (int)((note.start_time - start_time_sec) * sr);
        int note_len_idx = (int)(note.duration * sr);

        if (note_start_idx < 0 || note_start_idx >= *out_audio_length) continue;

        // ノート用の一時バッファに合成
        float* note_buf = (float*)calloc(note_len_idx, sizeof(float));
        process_note_to_buffer(note, pitch_events, pitch_event_count, note_buf, note_len_idx, sr);

        // メインバッファへ加算（ミックス）
        for (int i = 0; i < note_len_idx; i++) {
            if (note_start_idx + i < *out_audio_length) {
                full_buffer[note_start_idx + i] += note_buf[i];
            }
        }
        free(note_buf);
    }
    return full_buffer;
}

// Python向けのSynthesisRequest対応関数
EXPORT float* request_synthesis_full(SynthesisRequest request, int* out_sample_count) {
    return vse_synthesize_track(
        request.notes, request.note_count,
        request.pitch_events, request.pitch_event_count,
        0.0f, 10.0f, // TODO: 適切な範囲を指定
        out_sample_count
    );
}

// 音素データを保持する構造体
typedef struct {
    char phoneme_name[32];
    float* samples;
    drwav_uint64 sample_count;
} PhonemeSample;

PhonemeSample g_library[100]; // 最大100音素まで
int g_phoneme_count = 0;

// エンジンの初期化：指定ディレクトリのWAVをすべてロード
int init_engine(const char* char_id, const char* audio_dir) {
    // 実際にはディレクトリ内のファイルをループで回しますが、
    // ここでは代表的な「あ.wav」を読み込む例を示します
    char filepath[512];
    sprintf(filepath, "%s/a.wav", audio_dir); // a.wavを読み込む例

    unsigned int channels;
    unsigned int sampleRate;
    drwav_uint64 totalPCMFrameCount;
    
    float* pSampleData = drwav_open_file_and_read_pcm_frames_f32(
        filepath, &channels, &sampleRate, &totalPCMFrameCount, NULL);

    if (pSampleData != NULL) {
        strcpy(g_library[g_phoneme_count].phoneme_name, "a");
        g_library[g_phoneme_count].samples = pSampleData;
        g_library[g_phoneme_count].sample_count = totalPCMFrameCount;
        g_phoneme_count++;
        return 0;
    }
    return -1;
}
