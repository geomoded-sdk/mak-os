#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/fs.h>
#include <linux/errno.h>
#include <linux/types.h>

#include "lpnu_mach_o.h"

int lpnu_load_mach_o(struct file *filp, struct dentry *dentry)
{
    void *data;
    loff_t pos = 0;
    int ret;

    data = kzalloc(PAGE_SIZE, GFP_KERNEL);
    if (!data)
        return -ENOMEM;

    ret = kernel_read(filp, data, PAGE_SIZE, &pos);
    if (ret < 0) {
        kfree(data);
        return ret;
    }

    ret = lpnu_parse_mach_o_headers(data, ret);
    kfree(data);

    return ret;
}
EXPORT_SYMBOL(lpnu_load_mach_o);

int lpnu_parse_mach_o_headers(void *data, size_t size)
{
    struct lpnu_mach_header *mh;
    struct lpnu_mach_header_64 *mh64;
    u32 magic;

    if (size < sizeof(u32))
        return -EINVAL;

    magic = *(u32 *)data;

    if (magic == LPNU_MACH_O_MAGIC) {
        mh = (struct lpnu_mach_header *)data;
        printk(KERN_INFO "LPNU: Mach-O 32-bit detected, cputype=%u\n", mh->cputype);
    } else if (magic == LPNU_MACH_O_64_MAGIC) {
        mh64 = (struct lpnu_mach_header_64 *)data;
        printk(KERN_INFO "LPNU: Mach-O 64-bit detected, cputype=%u\n", mh64->cputype);
    } else {
        printk(KERN_WARNING "LPNU: Unknown binary format\n");
        return -ENOEXEC;
    }

    return 0;
}
EXPORT_SYMBOL(lpnu_parse_mach_o_headers);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("LPNU Team");
MODULE_DESCRIPTION("LPNU Mach-O loader");