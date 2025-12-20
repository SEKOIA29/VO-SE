#ifndef AUDIO_TYPES_H
#define AUDIO_TYPES_H

#define MAX_LYRIC_LENGTH 256
#define MAX_PHONEMES_COUNT 32

// ピッチベンドイベント
typedef struct {
    float time;   // 秒
    int value;    // -8192 〜 8191
} CPitchEvent;

// 音符（ノート）イベント
typedef struct {
    int note_number;      // MIDIノート番号
    float start_time;     // 開始時刻（秒）
    float duration;       // 長さ（秒）
    int velocity;         // 音量 (0-127)
    char lyrics[MAX_LYRIC_LENGTH]; 
    char** phonemes;      // 音素名の配列
    int phoneme_count;
} CNoteEvent;

#endif
