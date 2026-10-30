// SPDX-License-Identifier: GPL-2.0-only
/* PNFS — Pineapple Native File System (filesystem de kernel).
 *
 * PNFS nativo: valida o superbloco próprio no dispositivo e expõe a raiz
 * através do VFS. O formato de bloco é criado por pineapplefs-mkfs.
 */

#include <linux/fs.h>
#include <linux/buffer_head.h>
#include <linux/init.h>
#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/mount.h>
#include <linux/pagemap.h>
#include <linux/statfs.h>
#include <linux/string.h>

#define PNFS_MAGIC 0x504E4653 /* "PNFS" */
#define PNFS_VERSION 1
#define PNFS_BLOCK_SIZE 4096

struct pnfs_super {
	__le32 magic;
	__le32 version;
	__le32 block_size;
	__le32 flags;
	__le64 volume_blocks;
	__le64 metadata_start;
	__le64 metadata_blocks;
} __packed;

static const char pnfs_volume_info[] =
	"{\"magic\":\"PNFS\",\"format\":\"pnfs-native\",\"version\":1}\n";

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
	struct buffer_head *bh;
	struct pnfs_super *disk_sb;
	static const struct tree_descr pnfs_files[] = {
		{ "volume.info", &volume_info_fops, 0444 },
		{ "", NULL, 0 }
	};

	if (!sb_set_blocksize(sb, PNFS_BLOCK_SIZE))
		return -EINVAL;
	bh = sb_bread(sb, 0);
	if (!bh)
		return -EIO;
	disk_sb = (struct pnfs_super *)bh->b_data;
	if (le32_to_cpu(disk_sb->magic) != PNFS_MAGIC ||
	    le32_to_cpu(disk_sb->version) != PNFS_VERSION ||
	    le32_to_cpu(disk_sb->block_size) != PNFS_BLOCK_SIZE) {
		brelse(bh);
		return -EINVAL;
	}
	sb->s_magic = PNFS_MAGIC;
	sb->s_maxbytes = MAX_LFS_FILESIZE;
	brelse(bh);
	return simple_fill_super(sb, PNFS_MAGIC, pnfs_files);
}

static struct dentry *pnfs_mount(struct file_system_type *fs_type,
				 int flags, const char *dev_name, void *data)
{
	return mount_bdev(fs_type, flags, data, pnfs_fill_super);
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
	.kill_sb	= kill_block_super,
	.statfs		= pnfs_statfs,
	.fs_flags	= FS_REQUIRES_DEV,
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
