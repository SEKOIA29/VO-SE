#ifndef API_INTERFACE_H
#define API_INTERFACE_H

#include "audio_types.h"

// VO-SE_engine_C エンジンの初期化関数
void vse_initialize();

// VO-SE_engine_C エンジンの終了処理関数
void vse_shutdown();

// VO-SE_engine_C エンジンによる音声合成実行関数
// 引数として、音符とピッチデータの配列を受け取る
// 戻り値として、生成されたオーディオデータのポインタと長さを返す（メモリ管理に注意）
float* vse_synthesize_track(
    CNoteEvent* notes,
    int note_count,
    CPitchEvent* pitch_events,
    int pitch_event_count,
    float start_time_sec,
    float end_time_sec,
    int* out_audio_length // 生成されたオーディオデータのサンプル数を格納するポインタ
);

#endif // API_INTERFACE_H
