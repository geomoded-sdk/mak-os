#ifndef LPNU_MACH_O_H
#define LPNU_MACH_O_H

#include <linux/types.h>
#include <linux/fs.h>

#define LPNU_MACH_O_MAGIC 0xfeedface
#define LPNU_MACH_O_64_MAGIC 0xfeedfacf

#define LPNU_CPU_TYPE_X86_64 0x01000007
#define LPNU_CPU_TYPE_ARM64  0x0100000c

#define LPNU_MH_EXECUTE  2
#define LPNU_MH_KEXT    8
#define LPNU_MH_FILESET 12

struct lpnu_mach_header {
    __u32 magic;
    __u32 cputype;
    __u32 cpusubtype;
    __u32 filetype;
    __u32 ncmds;
    __u32 sizeofcmds;
    __u32 flags;
};

struct lpnu_mach_header_64 {
    __u32 magic;
    __u32 cputype;
    __u32 cpusubtype;
    __u32 filetype;
    __u32 ncmds;
    __u32 sizeofcmds;
    __u32 flags;
    __u32 reserved;
};

int lpnu_load_mach_o(struct file *filp, struct dentry *dentry);
int lpnu_parse_mach_o_headers(void *data, size_t size);

#endif