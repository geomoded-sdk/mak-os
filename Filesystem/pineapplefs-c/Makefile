CC ?= cc
CFLAGS ?= -O2 -Wall -Wextra -Werror

all: pineapplefs-boot

pineapplefs-boot: pineapplefs-boot.c
	$(CC) $(CFLAGS) -o $@ $<

clean:
	rm -f pineapplefs-boot

.PHONY: all clean
