#ifndef SYNTHESIZER_CORE_H
#define SYNTHESIZER_CORE_H

#include "audio_types.h"

// --- 定数定義 ---
#define FADE_TIME_SEC 0.005f  // クロスフェード時間 (5ms)
#define PI 3.14159265358979323846f

/**
 * 線形補間によるリサンプリング計算
 * @param src 元の波形データ
 * @param src_len 元のサンプル数
 * @param dest 出力先バッファ
 * @param dest_len 出力したいサンプル数
 */
void resample_linear(float* src, int src_len, float* dest, int dest_len);

/**
 * 指定した時刻におけるピッチベンド補正値の取得
 * @param time 検索する時刻（秒）
 * @param events ピッチイベントの配列
 * @param count イベント数
 * @return 補正後の周波数倍率 (1.0 = 変化なし)
 */
float get_pitch_multiplier(float time, CPitchEvent* events, int count);

/**
 * 2つの波形をクロスフェードで接続する
 * @param out_buffer 合成先のメインバッファ
 * @param current_pos 接続を開始する位置（サンプルインデックス）
 * @param new_sample 接続する新しい波形データ
 * @param sample_len 新しい波形の長さ
 * @param fade_samples フェードにかけるサンプル数
 */
void apply_crossfade(float* out_buffer, int current_pos, float* new_sample, int sample_len, int fade_samples);

/**
 * MIDIノート番号から周波数(Hz)への変換
 */
float note_to_hz(int note_number);

#endif // SYNTHESIZER_CORE_H
