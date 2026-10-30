// SPDX-License-Identifier: GPL-2.0-only
/* Pineapple OS — FreeBSD-inspired compatibility layer (hybrid kernel).
 *
 * O kernel do macOS real (XNU) é Mach + FreeBSD. O Pineapple OS é Linux +
 * camada BSD: este módulo expõe uma árvore sysctl estilo BSD em
 * /proc/sys/pineapple/ (kern.*) e metadados em /sys/kernel/pineapple/bsd/.
 */

#include <linux/init.h>
#include <linux/kernel.h>
#include <linux/kobject.h>
#include <linux/module.h>
#include <linux/sysctl.h>
#include <linux/utsname.h>

static struct kobject *bsd_kobj;

/* Buffers estáveis apontados pelo sysctl (não usar utsname direto). */
static char pineapple_ostype[64] = "Pineapple";
static char pineapple_osrelease[64];
static char pineapple_osversion[64];

static struct ctl_table pineapple_bsd_table[] = {
	{
		.procname = "ostype",
		.data = pineapple_ostype,
		.maxlen = sizeof(pineapple_ostype),
		.mode = 0444,
		.proc_handler = proc_dostring,
	},
	{
		.procname = "osrelease",
		.data = pineapple_osrelease,
		.maxlen = sizeof(pineapple_osrelease),
		.mode = 0444,
		.proc_handler = proc_dostring,
	},
	{
		.procname = "osversion",
		.data = pineapple_osversion,
		.maxlen = sizeof(pineapple_osversion),
		.mode = 0444,
		.proc_handler = proc_dostring,
	},
	{ }
};

static struct ctl_table pineapple_sysctl_root[] = {
	{
		.procname = "pineapple",
		.mode = 0555,
		.child = pineapple_bsd_table,
	},
	{ }
};

static ssize_t hybrid_show(struct kobject *kobj,
			   struct kobj_attribute *attr, char *buf)
{
	return sysfs_emit(buf,
			  "linux+bsd hybrid (XNU-style: Linux core, BSD layer)\n");
}

static struct kobj_attribute hybrid_attr = __ATTR_RO(hybrid);

static struct attribute *bsd_attrs[] = {
	&hybrid_attr.attr,
	NULL,
};

static const struct attribute_group bsd_attr_group = {
	.attrs = bsd_attrs,
};

static int __init pineapple_bsd_init(void)
{
	int ret;

	strscpy(pineapple_osrelease, utsname()->release,
		sizeof(pineapple_osrelease));
	strscpy(pineapple_osversion, utsname()->version,
		sizeof(pineapple_osversion));

	ret = register_sysctl_table(pineapple_sysctl_root);
	if (ret)
		pr_warn("pineapple-bsd: sysctl register failed (%d)\n", ret);

	bsd_kobj = kobject_create_and_add("bsd", kernel_kobj);
	if (bsd_kobj) {
		ret = sysfs_create_group(bsd_kobj, &bsd_attr_group);
		if (ret)
			kobject_put(bsd_kobj);
	}

	pr_info("pineapple-bsd: BSD compatibility layer initialized\n");
	return 0;
}

static void __exit pineapple_bsd_exit(void)
{
	unregister_sysctl_table(pineapple_sysctl_root);
	if (bsd_kobj)
		kobject_put(bsd_kobj);
}

subsys_initcall(pineapple_bsd_init);
module_exit(pineapple_bsd_exit);

MODULE_DESCRIPTION("Pineapple OS BSD compatibility layer");
MODULE_LICENSE("GPL");
