// SPDX-License-Identifier: GPL-2.0-only
/* Pineapple OS kernel identity and system metadata. */

#include <linux/init.h>
#include <linux/kernel.h>
#include <linux/kobject.h>
#include <linux/module.h>
#include <linux/sysfs.h>
#include <linux/utsname.h>

static struct kobject *pineapple_kobj;

static ssize_t identity_show(struct kobject *kobj,
                             struct kobj_attribute *attr, char *buf)
{
    return sysfs_emit(buf, "Pineapple Kernel\n");
}

static ssize_t release_show(struct kobject *kobj,
                            struct kobj_attribute *attr, char *buf)
{
    return sysfs_emit(buf, "%s\n", utsname()->release);
}

static struct kobj_attribute identity_attr = __ATTR_RO(identity);
static struct kobj_attribute release_attr = __ATTR_RO(release);

static struct attribute *pineapple_attrs[] = {
    &identity_attr.attr,
    &release_attr.attr,
    NULL,
};

static const struct attribute_group pineapple_attr_group = {
    .attrs = pineapple_attrs,
};

static int __init pineapple_core_init(void)
{
    int ret;

    pineapple_kobj = kobject_create_and_add("pineapple", kernel_kobj);
    if (!pineapple_kobj)
        return -ENOMEM;

    ret = sysfs_create_group(pineapple_kobj, &pineapple_attr_group);
    if (ret) {
        kobject_put(pineapple_kobj);
        pineapple_kobj = NULL;
        return ret;
    }

    pr_info("Pineapple Kernel core initialized (%s)\n", utsname()->release);
    return 0;
}

static void __exit pineapple_core_exit(void)
{
    if (pineapple_kobj) {
        sysfs_remove_group(pineapple_kobj, &pineapple_attr_group);
        kobject_put(pineapple_kobj);
    }
}

subsys_initcall(pineapple_core_init);
module_exit(pineapple_core_exit);

MODULE_DESCRIPTION("Pineapple OS kernel identity and metadata");
MODULE_LICENSE("GPL");
