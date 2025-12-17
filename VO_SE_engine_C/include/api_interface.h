#ifndef API_INTERFACE_H
#define API_INTERFACE_H

#include "audio_types.h"

// --- マクロ定義 ---
// Windows環境でDLLとして関数を公開するために必要
#ifdef _WIN32
    #define EXPORT __declspec(dllexport)
#else
    #define EXPORT __attribute__((visibility("default")))
#endif

// --- 構造体定義 ---

/**
 * Pythonから一括合成をリクエストする際のデータパッケージ
 */
typedef struct {
    CNoteEvent* notes;         // 音符イベントの配列
    int note_count;            // 音符の数
    CPitchEvent* pitch_events; // ピッチベンドイベントの配列
    int pitch_event_count;     // ピッチベンドの数
    int sample_rate;           // サンプリングレート (例: 44100)
} SynthesisRequest;

// --- 公開関数 (Pythonから呼び出す窓口) ---

#ifdef __cplusplus
extern "C" {
#endif

/**
 * エンジンの基本初期化
 */
EXPORT void vse_initialize();

/**
 * 特定のキャラクター音源をメモリにロードする
 * @param char_id キャラクターの識別子
 * @param audio_dir WAVファイルが格納されているディレクトリパス
 * @return 成功なら0, 失敗なら-1
 */
EXPORT int init_engine(const char* char_id, const char* audio_dir);

/**
 * リアルタイム再生用：特定のノートを解析し、指定されたバッファに直接書き込む
 * Python側のNumPy配列のポインタを直接操作することでゼロコピーを実現する
 */
EXPORT void process_note_to_buffer(
    CNoteEvent note, 
    CPitchEvent* pitch_events, 
    int pitch_event_count, 
    float* out_buffer, 
    int buffer_len,
    int sample_rate
);

/**
 * 一括合成用：リクエストを受け取り、新しいメモリ領域に音声波形を生成して返す
 * @param request ノートやピッチの情報
 * @param out_sample_count 生成されたサンプル数がここに格納される
 * @return 生成されたfloat波形配列のポインタ（使用後にvse_free_bufferで解放が必要）
 */
EXPORT float* request_synthesis_full(SynthesisRequest request, int* out_sample_count);

/**
 * トラック全体の合成実行（内部用または詳細設定用）
 */
EXPORT float* vse_synthesize_track(
    CNoteEvent* notes,
    int note_count,
    CPitchEvent* pitch_events,
    int pitch_event_count,
    float start_time_sec,
    float end_time_sec,
    int* out_audio_length
);

/**
 * メモリ解放：C言語側で確保したfloatバッファをPython側から解放するための必須関数
 */
EXPORT void vse_free_buffer(float* ptr);

/**
 * エンジンの終了処理（メモリの全解放）
 */
EXPORT void vse_shutdown();

#ifdef __cplusplus
}
#endif

#endif // API_INTERFACE_H
