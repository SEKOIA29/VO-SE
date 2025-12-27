#include <stdlib.h>
#include <math.h>
#include <string.h>
#include "../include/synthesizer_core.h"
#include "../include/dr_wav.h"

// 10msのクロスフェード（44100Hzの場合、441サンプル）
#define CROSSFADE_LEN 441

/**
 * 線形クロスフェードを適用する内部関数
 * out: 出力先
 * prev_buf: 前の音素の末尾
 * next_buf: 次の音素の先頭
 * len: フェードさせるサンプル数
 */
static void apply_linear_crossfade(float* out, const float* prev_buf, const float* next_buf, int len) {
    for (int i = 0; i < len; i++) {
        // 0.0から1.0へ変化する比率
        float ratio = (float)i / (float)len;
        // 前の音をフェードアウト(1->0)、次の音をフェードイン(0->1)
        out[i] = (prev_buf[i] * (1.0f - ratio)) + (next_buf[i] * ratio);
    }
}

/**
 * 指定された周波数(Hz)に基づいてリサンプリングを行いながら波形を生成する
 */
void process_note_with_fade(drwav* wav, float target_hz, float duration_sec, const char* lyric, float* overlap_buffer, int* has_overlap) {
    // 1. 音素データの読み込み（実際はaudio_data/からlyricに応じたWAVをロード）
    // ここでは簡易的に、ロード済みのソースバッファがあると仮定
    float source_hz = 440.0f; // 元の音素の基準ピッチ
    float speed_ratio = target_hz / source_hz;
    
    int sample_rate = 44100;
    int total_samples = (int)(duration_sec * sample_rate);
    
    // 出力用一時バッファ
    float* current_note_buf = (float*)malloc(sizeof(float) * total_samples);
    
    // --- [リサンプリング処理] ---
    for (int i = 0; i < total_samples; i++) {
        // speed_ratioに応じて読み取り位置を計算（簡易的な線形補間が望ましい）
        float read_pos = i * speed_ratio;
        // current_note_buf[i] = read_sample(lyric_data, read_pos);
    }

    // --- [クロスフェード適用] ---
    if (*has_overlap) {
        // 前のノートとの重なりがある場合、冒頭部分をフェード
        apply_linear_crossfade(current_note_buf, overlap_buffer, current_note_buf, CROSSFADE_LEN);
    }

    // 2. WAVファイルへの書き出し（フェード後の本体部分）
    // 末尾のCROSSFADE_LEN分は次のノートのために取っておく
    int write_len = total_samples - CROSSFADE_LEN;
    
    // 16bit PCMに変換して書き込み
    for (int i = 0; i < write_len; i++) {
        int16_t pcm = (int16_t)(current_note_buf[i] * 32767.0f);
        drwav_write_pcm_frames(wav, 1, &pcm);
    }

    // 3. 次のノートのために、今回の末尾部分をオーバーラップバッファに保存
    memcpy(overlap_buffer, &current_note_buf[write_len], sizeof(float) * CROSSFADE_LEN);
    *has_overlap = 1;

    free(current_note_buf);
}

/**
 * Pythonから呼ばれるメインのレンダリング関数
 */
void execute_render_to_file(const char* output_path, NoteEvent* notes, int count) {
    drwav_data_format format;
    format.container = drwav_container_riff;
    format.format = DR_WAV_FORMAT_PCM;
    format.channels = 1;
    format.sampleRate = 44100;
    format.bitsPerSample = 16;

    drwav wav;
    if (!drwav_init_file_write(&wav, output_path, &format, NULL)) return;

    float overlap_buffer[CROSSFADE_LEN];
    int has_overlap = 0;

    for (int i = 0; i < count; i++) {
        process_note_with_fade(&wav, notes[i].frequency, notes[i].duration, notes[i].lyric, overlap_buffer, &has_overlap);
    }

    // 最後に残ったバッファを書き出し
    if (has_overlap) {
        for (int i = 0; i < CROSSFADE_LEN; i++) {
            int16_t pcm = (int16_t)(overlap_buffer[i] * 32767.0f);
            drwav_write_pcm_frames(&wav, 1, &pcm);
        }
    }

    drwav_uninit(&wav);
}

