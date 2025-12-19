#include "api_interface.h"
#include <stdio.h>
#include <stdlib.h> // malloc, free に必要
#include <string.h> // memset に必要

// このファイルは、Python GUIとC言語コアエンジン間の橋渡し役を担います。

void vse_initialize() {
    // ここにエンジンの初期化処理（例: メモリ確保、設定読み込み）を記述します。
    printf("VO-SE_engine_C: Engine initialized.\n");
}

void vse_shutdown() {
    // ここにエンジンの終了処理（例: メモリ解放、ファイルクローズ）を記述します。
    printf("VO-SE_engine_C: Engine shutdown.\n");
}

float* vse_synthesize_track(
    CNoteEvent* notes,
    int note_count,
    CPitchEvent* pitch_events,
    int pitch_event_count,
    float start_time_sec,
    float end_time_sec,
    int* out_audio_length
) {
    // ダミーの合成処理。実際にはここにアルゴリズムが入ります。

    float duration = end_time_sec - start_time_sec;
    int sample_rate = 44100; // 仮のサンプルレート
    int num_samples = (int)(duration * sample_rate);

    // Pythonに返すためのオーディオデータメモリを確保します。
    // このメモリはPython側で解放される必要があります (メモリ管理規則を明確にすること)
    float* audio_data = (float*)malloc(num_samples * sizeof(float));
    if (audio_data == NULL) {
        // メモリ確保失敗時のエラーハンドリング
        *out_audio_length = 0;
        return NULL;
    }

    // とりあえず無音データで埋めます (ステップ4で置き換えられます)
    memset(audio_data, 0, num_samples * sizeof(float));

    // 生成したサンプル数を呼び出し元に伝える
    *out_audio_length = num_samples;
    
    printf("VO-SE_engine_C: Synthesized dummy track from %f to %f (%d samples).\n", start_time_sec, end_time_sec, num_samples);

    return audio_data;
}
