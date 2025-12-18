# コンパイラ設定 (macOSはclangが標準)
CC = gcc
# -O3: 最適化, -fPIC: 位置独立コード, -arch: Apple SiliconとIntel両対応
CFLAGS = -I./include -O3 -dynamiclib -fPIC -arch arm64 -arch x86_64
LDFLAGS = -lm

# 出力ファイル名 (macOSは .dylib)
TARGET = lib/engine.dylib

# ソースファイル
SRCS = src/api_interface.c src/synthesizer_core.c
HEADERS = include/api_interface.h include/audio_types.h include/synthesizer_core.h include/dr_wav.h

# ビルド命令
all: $(TARGET)

$(TARGET): $(SRCS) $(HEADERS)
	@mkdir -p lib
	$(CC) $(CFLAGS) -o $(TARGET) $(SRCS) $(LDFLAGS)
	@echo "Build Successful: $(TARGET)"

# 掃除命令
clean:
	rm -rf lib/engine.dylib
