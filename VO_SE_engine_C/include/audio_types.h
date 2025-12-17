#VO_SE_engine_C/include/audio_types.h
#ifndef AUDIO_TYPES_H
#define AUDIO_TYPES_H

// VO-SE_engine_C プロジェクトで使用するデータ構造

#define MAX_LYRIC_LENGTH 256
#define MAX_PHONEMES_COUNT 32

// ピッチベンドイベントの構造体 (PythonのPitchEventに相当)
typedef struct {
    float time;   // イベント発生時刻 (秒)
    int value;    // ピッチベンド値 (-8192 〜 8191)
} CPitchEvent;

// 音符イベントの構造体 (PythonのNoteEventに相当)
typedef struct {
    int note_number;      // MIDIノート番号
    float start_time;     // 開始時刻 (秒)
    float duration;       // 長さ (秒)
    int velocity;         // ベロシティ (音量)

    char lyrics[MAX_LYRIC_LENGTH]; // 歌詞文字列
    
    char** phonemes; // 音素文字列のポインタ配列
    int phoneme_count;

} CNoteEvent;

#endif // AUDIO_TYPES_H
