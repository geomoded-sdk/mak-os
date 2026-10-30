// SPDX-License-Identifier: GPL-2.0-only
/* Formatter for the native PNFS on-disk superblock. */
#define _FILE_OFFSET_BITS 64
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

#define PNFS_MAGIC 0x504E4653U
#define PNFS_VERSION 1U
#define PNFS_BLOCK_SIZE 4096U

struct pnfs_super {
    uint32_t magic;
    uint32_t version;
    uint32_t block_size;
    uint32_t flags;
    uint64_t volume_blocks;
    uint64_t metadata_start;
    uint64_t metadata_blocks;
} __attribute__((packed));

int main(int argc, char **argv)
{
    unsigned char block[PNFS_BLOCK_SIZE] = {0};
    struct pnfs_super *sb = (struct pnfs_super *)block;
    int fd;
    ssize_t written;

    if (argc != 2) {
        fprintf(stderr, "usage: %s BLOCK_DEVICE\n", argv[0]);
        return 2;
    }
    fd = open(argv[1], O_RDWR | O_CLOEXEC);
    if (fd < 0) {
        fprintf(stderr, "open %s: %s\n", argv[1], strerror(errno));
        return 1;
    }
    sb->magic = PNFS_MAGIC;
    sb->version = PNFS_VERSION;
    sb->block_size = PNFS_BLOCK_SIZE;
    sb->metadata_start = 1;
    sb->metadata_blocks = 1;
    written = pwrite(fd, block, sizeof(block), 0);
    if (written != (ssize_t)sizeof(block) || fsync(fd) != 0) {
        fprintf(stderr, "write %s: %s\n", argv[1], strerror(errno));
        close(fd);
        return 1;
    }
    close(fd);
    return 0;
}
