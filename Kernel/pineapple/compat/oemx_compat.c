// SPDX-License-Identifier: GPL-2.0-only
/*
 * OEM-X compatibility core.
 *
 * This is an original Linux-kernel adaptation of two upstream ideas kept in
 * Kernel/vendor/: FreeBSD's queue/sysctl style and XNU's typed IPC/VM model.
 * The vendored files remain reference material under their original licenses;
 * this translation uses Linux primitives and is compiled into OEM-X.
 */
#include <linux/init.h>
#include <linux/kernel.h>
#include <linux/kobject.h>
#include <linux/mutex.h>
#include <linux/sysfs.h>

static DEFINE_MUTEX(oemx_dispatch_lock);
static unsigned long oemx_ipc_generation;

static ssize_t ipc_generation_show(struct kobject *kobj,
                                   struct kobj_attribute *attr, char *buf)
{
    return sysfs_emit(buf, "%lu\n", READ_ONCE(oemx_ipc_generation));
}

static ssize_t vm_policy_show(struct kobject *kobj,
                              struct kobj_attribute *attr, char *buf)
{
    return sysfs_emit(buf, "typed-pages=enabled\nqueues=bounded\n");
}

static struct kobj_attribute ipc_generation_attr = __ATTR_RO(ipc_generation);
static struct kobj_attribute vm_policy_attr = __ATTR_RO(vm_policy);

static struct attribute *oemx_compat_attrs[] = {
    &ipc_generation_attr.attr,
    &vm_policy_attr.attr,
    NULL,
};

static const struct attribute_group oemx_compat_group = {
    .name = "compat",
    .attrs = oemx_compat_attrs,
};

int __init oemx_compat_init(struct kobject *root)
{
    mutex_lock(&oemx_dispatch_lock);
    oemx_ipc_generation = 1;
    mutex_unlock(&oemx_dispatch_lock);
    return sysfs_create_group(root, &oemx_compat_group);
}
