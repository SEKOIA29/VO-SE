#ifndef SYNTHESIZER_CORE_H
#define SYNTHESIZER_CORE_H

#include "audio_types.h"

// MIDIノートから周波数へ変換
float note_to_hz(int note_number);

// 線形補間リサンプリング
void resample_linear(float* src, int src_len, float* dest, int dest_len);

// クロスフェード適用
void apply_crossfade(float* out_buffer, int current_pos, float* new_sample, int sample_len, int fade_samples);

#endif

