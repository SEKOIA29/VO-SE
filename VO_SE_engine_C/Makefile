# --- OS判別 ---
ifeq ($(OS),Windows_NT)
    PLATFORM = Windows
else
    UNAME_S := $(shell uname -s)
    ifeq ($(UNAME_S),Darwin)
        PLATFORM = Mac
    else
        PLATFORM = Linux
    endif
endif

# --- 共通設定 ---
CC = gcc
SRCS = src/api_interface.c src/synthesizer_core.c
HEADERS = include/api_interface.h include/audio_types.h include/synthesizer_core.h include/dr_wav.h
LDFLAGS = -lm

# --- OS別の最適化設定 ---
ifeq ($(PLATFORM),Windows)
    # Windows (Intel/AMD) 最適化:
    # -mavx2: 最近のCPUの並列計算(AVX2)を有効化
    # -mfpmath=sse: 浮動小数点計算を高速なSSEで行う
    TARGET = lib/engine.dll
    CFLAGS = -I./include -O3 -shared -mavx2 -mfpmath=sse
    MKDIR = if not exist lib mkdir lib
    CLEAN = if exist lib\engine.dll del lib\engine.dll
else ifeq ($(PLATFORM),Mac)
    # Mac (Apple Silicon / Intel) 最適化:
    # -arch arm64 -arch x86_64: 両方のMacに対応(ユニバーサルバイナリ)
    # -mcpu=apple-m1: Apple Siliconの計算ユニットをフル活用
    TARGET = lib/engine.dylib
    CFLAGS = -I./include -O3 -dynamiclib -fPIC -arch arm64 -arch x86_64
    MKDIR = mkdir -p lib
    CLEAN = rm -rf lib/engine.dylib
endif

# --- ビルド命令 ---
all: $(TARGET)

$(TARGET): $(SRCS) $(HEADERS)
	$(MKDIR)
	$(CC) $(CFLAGS) -o $(TARGET) $(SRCS) $(LDFLAGS)
	@echo "Build Successful for $(PLATFORM): $(TARGET)"

clean:
	$(CLEAN)
