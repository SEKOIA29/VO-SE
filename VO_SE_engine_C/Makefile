CC = gcc
CFLAGS = -I./include -O3 -shared -fPIC
LDFLAGS = -lm
TARGET = lib/engine.dll  # Mac/Linuxなら .so に書き換え

all: $(TARGET)

$(TARGET): src/api_interface.c
	$(CC) $(CFLAGS) -o $(TARGET) src/api_interface.c $(LDFLAGS)

clean:
	rm -f $(TARGET)
