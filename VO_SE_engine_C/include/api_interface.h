#ifndef API_INTERFACE_H
#define API_INTERFACE_H

#include "audio_types.h"

// 合成リクエストをまとめる構造体
typedef struct {
    CNoteEvent* notes;
    int note_count;
    CPitchEvent* pitch_events;
    int pitch_event_count;
    int sample_rate;
} SynthesisRequest;

//  初期化: 音源ディレクトリをスキャンしてメモリにロード（Pythonの _load_all_character_samples に相当）
int init_engine(const char* char_id, const char* audio_dir);

// Pythonから呼び出す関数
EXPORT float* request_synthesis_full(SynthesisRequest request, int* out_sample_count);


// VO-SE_engine_C エンジンの初期化関数
void vse_initialize();

// VO-SE_engine_C エンジンの終了処理関数
void vse_shutdown();

// 2. 合成: ノートとピッチベンドを渡し、波形バッファを受け取る（_generate_note_with_pitch_bend に相当）
// Python側で確保した audio_data（NumPy配列のポインタ）に直接書き込む「ゼロコピー」方式が高速です
void process_note_to_buffer(
    CNoteEvent note, 
    CPitchEvent* pitch_events, 
    int pitch_event_count, 
    float* out_buffer, 
    int buffer_len,
    int sample_rate
);


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
