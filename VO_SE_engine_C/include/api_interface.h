#ifndef API_INTERFACE_H
#define API_INTERFACE_H

#include "audio_types.h"

// WindowsでのDLLエクスポート設定
#ifdef _WIN32
    #define API_EXPORT __declspec(dllexport)
#else
    #define API_EXPORT __attribute__((visibility("default")))
#endif

// --- Pythonから呼び出す関数（公開API） ---

/**
 * エンジンの初期化
 * サンプリングレートなどを設定し、メモリを確保する
 */
API_EXPORT int init_engine(int sample_rate);

/**
 * ターゲット周波数の設定
 * タイムラインのY軸から計算されたHzをここに渡す
 */
API_EXPORT void set_frequency(float hz);

/**
 * 音素の読み込みと再生準備
 * lyric: "a", "i" などの音素名
 */
API_EXPORT void prepare_phoneme(const char* lyric);

/**
 * レンダリング（書き出し）の実行
 * output_path: 保存先のファイルパス
 * notes: ノートデータの配列
 * count: ノートの数
 */
API_EXPORT void execute_render_to_file(const char* output_path, NoteEvent* notes, int count);

/**
 * エンジンの解放
 */
API_EXPORT void terminate_engine();

#endif // API_INTERFACE_H


