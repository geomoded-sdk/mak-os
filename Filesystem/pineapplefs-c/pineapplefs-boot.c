// SPDX-License-Identifier: GPL-2.0-only
/* Minimal BFS metadata runtime for initramfs/preboot and early boot. */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <linux/xattr.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/xattr.h>
#include <unistd.h>

static int make_dir(const char *path)
{
    if (mkdir(path, 0755) == 0 || errno == EEXIST)
        return 0;
    return -1;
}

static void hide_for_supported_filesystems(const char *path)
{
    unsigned char dosattr[4] = {0x02, 0x00, 0x00, 0x00};
    /* exFAT/NTFS userspace drivers commonly understand this DOS hidden bit. */
    (void)setxattr(path, "user.DOSATTRIB", dosattr, sizeof(dosattr), 0);
}

static int create_hidden_file(const char *root, const char *name)
{
    char path[4096];
    int fd;

    if (snprintf(path, sizeof(path), "%s/%s", root, name) >= (int)sizeof(path))
        return -1;
    fd = open(path, O_CREAT | O_WRONLY | O_CLOEXEC, 0600);
    if (fd < 0)
        return -1;
    close(fd);
    hide_for_supported_filesystems(path);
    return 0;
}

static int create_hidden_dir(const char *root, const char *name)
{
    char path[4096];

    if (snprintf(path, sizeof(path), "%s/%s", root, name) >= (int)sizeof(path))
        return -1;
    if (make_dir(path) < 0)
        return -1;
    hide_for_supported_filesystems(path);
    return 0;
}

int main(int argc, char **argv)
{
    char private[4096];
    char path[4096];
    int fd;

    if (argc != 2) {
        fprintf(stderr, "usage: %s MOUNTPOINT\n", argv[0]);
        return 2;
    }
    if (snprintf(private, sizeof(private), "%s/.bfsprivate", argv[1]) >= (int)sizeof(private))
        return 1;
    if (make_dir(private) < 0)
        return 1;
    if (snprintf(path, sizeof(path), "%s/volume.info", private) >= (int)sizeof(path))
        return 1;
    fd = open(path, O_CREAT | O_WRONLY | O_CLOEXEC, 0600);
    if (fd < 0)
        return 1;
    if (lseek(fd, 0, SEEK_END) == 0)
        dprintf(fd, "{\"magic\":\"BFS\",\"format\":\"bfs-overlay\"}\n");
    close(fd);
    hide_for_supported_filesystems(private);
    hide_for_supported_filesystems(path);
    create_hidden_dir(argv[1], ".Spotlight-V100");
    create_hidden_dir(argv[1], ".fseventsd");
    create_hidden_dir(argv[1], ".Trashes");
    create_hidden_file(argv[1], ".DS_Store");
    create_hidden_file(argv[1], ".localized");
    create_hidden_file(argv[1], ".metadata_never_index");
    return 0;
}
