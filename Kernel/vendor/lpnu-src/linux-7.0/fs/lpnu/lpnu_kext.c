#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/init.h>

int lpnu_kext_load(const char *path)
{
    printk(KERN_INFO "LPNU: Loading KEXT: %s\n", path);
    return 0;
}
EXPORT_SYMBOL(lpnu_kext_load);

int lpnu_kext_unload(const char *identifier)
{
    printk(KERN_INFO "LPNU: Unloading KEXT: %s\n", identifier);
    return 0;
}
EXPORT_SYMBOL(lpnu_kext_unload);

int lpnu_io_connect(struct file *filp)
{
    printk(KERN_INFO "LPNU: IO Connect called\n");
    return 0;
}
EXPORT_SYMBOL(lpnu_io_connect);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("LPNU Team");
MODULE_DESCRIPTION("LPNU KEXT compatibility layer");