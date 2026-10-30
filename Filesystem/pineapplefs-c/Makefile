CC ?= cc
CFLAGS ?= -O2 -Wall -Wextra -Werror

all: pineapplefs-mkfs

pineapplefs-mkfs: pineapplefs-mkfs.c
	$(CC) $(CFLAGS) -o $@ $<

clean:
	rm -f pineapplefs-mkfs

.PHONY: all clean
