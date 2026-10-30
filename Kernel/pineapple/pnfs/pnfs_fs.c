// SPDX-License-Identifier: GPL-2.0-only
/* PNFS — Pineapple Native File System (filesystem de kernel).
 *
 * Primeiro estágio in-kernel do PNFS: registra o filesystem "pnfs" no VFS.
 * mount -t pnfs none /mnt/pnfs cria um volume PNFS em RAM com volume.info
 * (magic PNFS) — base para evoluir para disco real. O módulo de metadados
 * em userspace continua sendo .bfsprivate.
 */

#include <linux/fs.h>
#include <linux/init.h>
#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/mount.h>
#include <linux/pagemap.h>
#include <linux/statfs.h>
#include <linux/string.h>

#define PNFS_MAGIC 0x504E4653 /* "PNFS" */

static const char pnfs_volume_info[] =
	"{\"magic\":\"PNFS\",\"format\":\"pnfs-overlay\",\"version\":2}\n";

/* ---- arquivo volume.info (conteúdo fixo) ---- */

static ssize_t volume_info_read(struct file *file, char __user *buf,
				size_t count, loff_t *ppos)
{
	return simple_read_from_buffer(buf, count, ppos,
				       pnfs_volume_info,
				       sizeof(pnfs_volume_info) - 1);
}

static const struct file_operations volume_info_fops = {
	.owner	= THIS_MODULE,
	.read	= volume_info_read,
	.llseek	= generic_file_llseek,
};

/* ---- superblock ---- */

static int pnfs_fill_super(struct super_block *sb, void *data, int silent)
{
	static const struct tree_descr pnfs_files[] = {
		{ "volume.info", &volume_info_fops, 0444 },
		{ "", NULL, 0 }
	};

	return simple_fill_super(sb, PNFS_MAGIC, pnfs_files);
}

static struct dentry *pnfs_mount(struct file_system_type *fs_type,
				 int flags, const char *dev_name, void *data)
{
	return mount_single(fs_type, flags, data, pnfs_fill_super);
}

static int pnfs_statfs(struct dentry *dentry, struct kstatfs *buf)
{
	buf->f_type = PNFS_MAGIC;
	buf->f_bsize = PAGE_SIZE;
	buf->f_namelen = 255;
	return 0;
}

static struct file_system_type pnfs_fs_type = {
	.owner		= THIS_MODULE,
	.name		= "pnfs",
	.mount		= pnfs_mount,
	.kill_sb	= kill_litter_super,
	.statfs		= pnfs_statfs,
};

static int __init pnfs_init(void)
{
	int ret = register_filesystem(&pnfs_fs_type);

	if (ret)
		pr_err("pnfs: register_filesystem failed (%d)\n", ret);
	else
		pr_info("pnfs: Pineapple Native File System registered\n");
	return ret;
}

static void __exit pnfs_exit(void)
{
	unregister_filesystem(&pnfs_fs_type);
}

module_init(pnfs_init);
module_exit(pnfs_exit);

MODULE_DESCRIPTION("PNFS — Pineapple Native File System");
MODULE_LICENSE("GPL");
