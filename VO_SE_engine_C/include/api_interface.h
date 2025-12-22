#ifndef SYNTHESIZER_CORE_H
#define SYNTHESIZER_CORE_H

void resample_linear(const float* input, int input_len, float* output, int output_len);
void apply_crossfade(float* dest, int dest_start, const float* src, int src_len, int fade_len);

#endif

