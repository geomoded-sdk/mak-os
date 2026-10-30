// SPDX-License-Identifier: GPL-2.0-only
/* Pineapple OS — boot-args no kernel (estilo macOS boot-args/NVRAM).
 *
 * Lê /proc/cmdline em initcalls tardios e expõe:
 *   /sys/kernel/pineapple/boot/powerbookid
 *   /sys/kernel/pineapple/boot/pnfsdev
 *   /sys/kernel/pineapple/boot/live
 *
 * Com CONFIG_PINEAPPLE_BOOT_ENFORCE=y (padrão quando PINEAPPLE_BOOT=y),
 * sem -pineapplepowerbookid=<ID> válido (lista empineappleos-ids embutida
 * pelo build) o kernel entra em panic estilo macOS — validação NO KERNEL,
 * não só no initramfs (defesa em profundidade).
 */

#include <linux/init.h>
#include <linux/kernel.h>
#include <linux/kobject.h>
#include <linux/module.h>
#include <linux/string.h>
#include <linux/utsname.h>

#define PBID_MAX 64
#define PNFSD_MAX 64

static char boot_powerbookid[PBID_MAX];
static char boot_pnfsdev[PNFSD_MAX];
static int boot_live;

/* IDs válidos embutidos (gerado pelo build-kernel.sh a partir de ids.txt). */
#ifdef CONFIG_PINEAPPLE_BOOT_ENFORCE
#include "pineapple_ids.h"
#else
static const char *pineapple_valid_ids[] = { };
static const unsigned int pineapple_valid_ids_count;
#endif

static bool id_is_valid(const char *id)
{
	unsigned int i;

	if (!id || !id[0])
		return false;
	for (i = 0; i < pineapple_valid_ids_count; i++) {
		if (strcmp(pineapple_valid_ids[i], id) == 0)
			return true;
	}
	return false;
}

static ssize_t powerbookid_show(struct kobject *kobj,
				struct kobj_attribute *attr, char *buf)
{
	return sysfs_emit(buf, "%s\n", boot_powerbookid[0] ? boot_powerbookid : "(ausente)");
}

static ssize_t pnfsdev_show(struct kobject *kobj,
			    struct kobj_attribute *attr, char *buf)
{
	return sysfs_emit(buf, "%s\n", boot_pnfsdev[0] ? boot_pnfsdev : "(ausente)");
}

static ssize_t live_show(struct kobject *kobj,
			 struct kobj_attribute *attr, char *buf)
{
	return sysfs_emit(buf, "%s\n", boot_live ? "yes" : "no");
}

static struct kobj_attribute powerbookid_attr = __ATTR_RO(powerbookid);
static struct kobj_attribute pnfsdev_attr = __ATTR_RO(pnfsdev);
static struct kobj_attribute live_attr = __ATTR_RO(live);

static struct attribute *boot_attrs[] = {
	&powerbookid_attr.attr,
	&pnfsdev_attr.attr,
	&live_attr.attr,
	NULL,
};

static const struct attribute_group boot_attr_group = {
	.attrs = boot_attrs,
};

static struct kobject *boot_kobj;

static int __init pineapple_boot_init(void)
{
	const char *cmd = saved_command_line;
	const char *p;

	boot_kobj = kobject_create_and_add("boot", kernel_kobj);
	if (boot_kobj)
		sysfs_create_group(boot_kobj, &boot_attr_group);

	if (!cmd)
		return 0;

	p = strstr(cmd, "-pineapplepowerbookid=");
	if (p) {
		p += strlen("-pineapplepowerbookid=");
		strncpy(boot_powerbookid, p, PBID_MAX - 1);
		/* corta no primeiro espaço */
		{
			char *sp = strchr(boot_powerbookid, ' ');
			if (sp)
				*sp = '\0';
		}
	}

	p = strstr(cmd, "-pineapplefs=");
	if (p) {
		p += strlen("-pineapplefs=");
		strncpy(boot_pnfsdev, p, PNFSD_MAX - 1);
		{
			char *sp = strchr(boot_pnfsdev, ' ');
			if (sp)
				*sp = '\0';
		}
	}

	if (strstr(cmd, "boot=live"))
		boot_live = 1;

#ifdef CONFIG_PINEAPPLE_BOOT_ENFORCE
	/* Fora o PowerBook ID no KERNEL (antes do userspace). */
	if (!boot_live && !id_is_valid(boot_powerbookid)) {
		panic("Pineapple OS: PowerBook ID inválido ou ausente.\n\n"
		      "  O kernel exige -pineapplepowerbookid=<ID> válido\n"
		      "  (lista desta build em pineapple_ids.h).\n\n"
		      "  Você precisa reiniciar o computador.\n");
	}
#endif

	pr_info("pineapple-boot: powerbookid=%s pnfs=%s live=%d\n",
		boot_powerbookid[0] ? boot_powerbookid : "-",
		boot_pnfsdev[0] ? boot_pnfsdev : "-",
		boot_live);
	return 0;
}

static void __exit pineapple_boot_exit(void)
{
	if (boot_kobj)
		kobject_put(boot_kobj);
}

late_initcall(pineapple_boot_init);
module_exit(pineapple_boot_exit);

MODULE_DESCRIPTION("Pineapple OS boot-args (PowerBook ID + PNFS)");
MODULE_LICENSE("GPL");
