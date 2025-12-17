// Pythonの np.interp に相当する線形補間
void resample_wave(float* src, int src_len, float* dest, int dest_len) {
    float ratio = (float)src_len / dest_len;
    for (int i = 0; i < dest_len; i++) {
        float pos = i * ratio;
        int index = (int)pos;
        float frac = pos - index;
        
        if (index + 1 < src_len) {
            // 線形補間
            dest[i] = src[index] * (1.0f - frac) + src[index + 1] * frac;
        } else {
            dest[i] = src[index];
        }
    }
}
