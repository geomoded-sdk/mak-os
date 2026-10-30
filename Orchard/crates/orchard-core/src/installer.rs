use crate::config::{InstallConfig, PartitionMode};
use crate::error::{Error, Result};
use std::process::Command;

/// Etapas da instalação, na ordem em que ocorrem.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum InstallStep {
    Validate,
    UnmountExisting,
    Partition,
    Format,
    Mount,
    CopySystem,
    ConfigureBootloader,
    ConfigureSystem,
    CreatePnfs,
    Finalize,
}

impl InstallStep {
    /// Descrição amigável exibida na UI.
    pub fn label(&self) -> &'static str {
        match self {
            InstallStep::Validate => "Validando configuração",
            InstallStep::UnmountExisting => "Desmontando partições existentes",
            InstallStep::Partition => "Particionando o disco",
            InstallStep::Format => "Formatando volumes",
            InstallStep::Mount => "Montando o novo sistema",
            InstallStep::CopySystem => "Copiando o sistema",
            InstallStep::ConfigureBootloader => "Configurando o boot",
            InstallStep::ConfigureSystem => "Configurando o sistema",
            InstallStep::CreatePnfs => "Criando o volume PNFS",
            InstallStep::Finalize => "Finalizando",
        }
    }

    /// Progresso aproximado (0.0–1.0) no início de cada etapa.
    pub fn start_percent(&self) -> f32 {
        match self {
            InstallStep::Validate => 0.02,
            InstallStep::UnmountExisting => 0.05,
            InstallStep::Partition => 0.10,
            InstallStep::Format => 0.20,
            InstallStep::Mount => 0.30,
            InstallStep::CopySystem => 0.35,
            InstallStep::ConfigureBootloader => 0.75,
            InstallStep::ConfigureSystem => 0.85,
            InstallStep::CreatePnfs => 0.92,
            InstallStep::Finalize => 0.98,
        }
    }
}

/// Progresso reportado à UI a cada mudança.
#[derive(Debug, Clone)]
pub struct InstallProgress {
    pub step: InstallStep,
    pub percent: f32,
    pub message: String,
}

/// Motor de instalação. Uso:
/// ```ignore
/// let mut inst = Installer::new(config, /* dry_run */ true);
/// inst.run(|p| println!("{:.0}% {}: {}", p.percent, p.step.label(), p.message))?;
/// ```
pub struct Installer {
    config: InstallConfig,
    dry_run: bool,
    /// Raiz onde o sistema seria montado (dry-run usa um dir temporário).
    mount_root: String,
}

impl Installer {
    pub fn new(config: InstallConfig, dry_run: bool) -> Self {
        let mount_root = if dry_run {
            std::env::temp_dir()
                .join("orchard-dry-run")
                .to_string_lossy()
                .into_owned()
        } else {
            "/mnt/pineapple".to_string()
        };
        Self {
            config,
            dry_run,
            mount_root,
        }
    }

    pub fn config(&self) -> &InstallConfig {
        &self.config
    }

    pub fn is_dry_run(&self) -> bool {
        self.dry_run
    }

    /// Executa a instalação completa, reportando progresso via `on_progress`.
    pub fn run<F: FnMut(InstallProgress)>(&mut self, mut on_progress: F) -> Result<()> {
        let steps = [
            InstallStep::Validate,
            InstallStep::UnmountExisting,
            InstallStep::Partition,
            InstallStep::Format,
            InstallStep::Mount,
            InstallStep::CopySystem,
            InstallStep::ConfigureBootloader,
            InstallStep::ConfigureSystem,
            InstallStep::CreatePnfs,
            InstallStep::Finalize,
        ];

        for step in steps {
            let progress = InstallProgress {
                step,
                percent: step.start_percent(),
                message: step.label().to_string(),
            };
            on_progress(progress);
            self.run_step(step)?;
        }

        on_progress(InstallProgress {
            step: InstallStep::Finalize,
            percent: 1.0,
            message: "Instalação concluída".into(),
        });
        Ok(())
    }

    fn run_step(&self, step: InstallStep) -> Result<()> {
        match step {
            InstallStep::Validate => self.config.validate().map_err(Error::InvalidConfig)?,
            InstallStep::UnmountExisting => self.unmount_existing(),
            InstallStep::Partition => self.partition(),
            InstallStep::Format => self.format(),
            InstallStep::Mount => self.mount(),
            InstallStep::CopySystem => self.copy_system(),
            InstallStep::ConfigureBootloader => self.configure_bootloader(),
            InstallStep::ConfigureSystem => self.configure_system(),
            InstallStep::CreatePnfs => self.create_pnfs(),
            InstallStep::Finalize => self.finalize(),
        }
    }

    /// Executa um comando externo; em dry-run apenas loga.
    fn cmd(&self, program: &str, args: &[&str]) -> Result<()> {
        if self.dry_run {
            eprintln!("[dry-run] {program} {}", args.join(" "));
            return Ok(());
        }
        let out = Command::new(program)
            .args(args)
            .output()
            .map_err(|e| Error::CommandFailed {
                cmd: format!("{program} {}", args.join(" ")),
                stderr: e.to_string(),
            })?;
        if !out.status.success() {
            return Err(Error::CommandFailed {
                cmd: format!("{program} {}", args.join(" ")),
                stderr: String::from_utf8_lossy(&out.stderr).into_owned(),
            });
        }
        Ok(())
    }

    fn unmount_existing(&self) -> Result<()> {
        // Desmonta tudo que esteja sob o disco de destino (ex.: /dev/sda1).
        let disk = &self.config.disk;
        if let Ok(out) = Command::new("lsblk")
            .args(["-ln", "-o", "NAME", disk])
            .output()
        {
            for name in String::from_utf8_lossy(&out.stdout).lines() {
                let name = name.trim();
                if name.is_empty() || name == disk.rsplit('/').next().unwrap_or("") {
                    continue;
                }
                let dev = format!("/dev/{name}");
                let _ = self.cmd("umount", &[&dev]);
                let _ = self.cmd("swapoff", &[&dev]);
            }
        }
        Ok(())
    }

    fn partition(&self) -> Result<()> {
        let disk = self.config.disk.clone();
        match self.config.mode {
            PartitionMode::Erase => {
                // GPT: p1 = EFI (512MiB), p2 = raiz (restante ou root_size_mib),
                // p3 = PNFS (2GiB fixo) se pnfs_device for None.
                let script = if self.config.pnfs_device.is_some() {
                    "label: gpt\n,512MiB,U\n,,L\n"
                } else {
                    "label: gpt\n,512MiB,U\n,,L\n,2GiB,L\n"
                };
                self.cmd_with_stdin("sfdisk", &["--force", &disk], script)?;
            }
            PartitionMode::Alongside | PartitionMode::Manual => {
                return Err(Error::Other(
                    "modos Alongside/Manual ainda não implementados — use Erase".into(),
                ));
            }
        }
        Ok(())
    }

    fn cmd_with_stdin(&self, program: &str, args: &[&str], stdin: &str) -> Result<()> {
        if self.dry_run {
            eprintln!("[dry-run] {program} {} <<< {stdin:?}", args.join(" "));
            return Ok(());
        }
        use std::io::Write;
        use std::process::Stdio;
        let mut child = Command::new(program)
            .args(args)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .map_err(|e| Error::CommandFailed {
                cmd: program.into(),
                stderr: e.to_string(),
            })?;
        if let Some(mut si) = child.stdin.take() {
            si.write_all(stdin.as_bytes()).ok();
        }
        let out = child
            .wait_with_output()
            .map_err(|e| Error::CommandFailed {
                cmd: program.into(),
                stderr: e.to_string(),
            })?;
        if !out.status.success() {
            return Err(Error::CommandFailed {
                cmd: format!("{program} {}", args.join(" ")),
                stderr: String::from_utf8_lossy(&out.stderr).into_owned(),
            });
        }
        Ok(())
    }

    fn format(&self) -> Result<()> {
        let disk = &self.config.disk;
        let p1 = format!("{disk}1");
        let p2 = format!("{disk}2");
        self.cmd("mkfs.vfat", &["-F", "32", "-n", "EFI", &p1])?;
        self.cmd("mkfs.ext4", &["-L", "pineapple-root", &p2])?;
        if self.config.pnfs_device.is_none() {
            let p3 = format!("{disk}3");
            self.cmd("mkfs.exfat", &["-n", "PINEAPPLE", &p3])?;
        }
        Ok(())
    }

    fn mount(&self) -> Result<()> {
        let disk = &self.config.disk;
        let root = self.mount_root.clone();
        self.cmd("mkdir", &["-p", &root])?;
        self.cmd("mount", &[&format!("{disk}2"), &root])?;
        self.cmd("mkdir", &["-p", &format!("{root}/boot/efi")])?;
        self.cmd("mount", &[&format!("{disk}1"), &format!("{root}/boot/efi")])?;
        Ok(())
    }

    fn copy_system(&self) -> Result<()> {
        // Live system: copia a raiz do live (exeto /mnt, /media, /proc…).
        let dest = format!("{}/", self.mount_root);
        self.cmd(
            "rsync",
            &[
                "-aHAX",
                "--numeric-ids",
                "--exclude=/mnt/*",
                "--exclude=/media/*",
                "--exclude=/proc/*",
                "--exclude=/sys/*",
                "--exclude=/dev/*",
                "--exclude=/tmp/*",
                "--exclude=/run/*",
                "--exclude=/boot/*",
                "--one-file-system",
                "/",
                &dest,
            ],
        )
    }

    fn configure_bootloader(&self) -> Result<()> {
        let root = &self.mount_root;
        let disk = &self.config.disk;
        // grub-install + configuração com os boot args do Pineapple.
        self.cmd("chroot", &[root, "grub-install", disk])?;
        let grub_default = format!(
            "{root}/etc/default/grub"
        );
        self.cmd(
            "chroot",
            &[
                root,
                "sed",
                "-i",
                &format!(
                    "s/^GRUB_CMDLINE_LINUX_DEFAULT=.*/GRUB_CMDLINE_LINUX_DEFAULT=\"quiet loglevel=0 splash -pineapplepowerbookid={}\"/",
                    self.config.powerbook_id
                ),
                &grub_default,
            ],
        )?;
        self.cmd("chroot", &[root, "update-grub"])?;
        Ok(())
    }

    fn configure_system(&self) -> Result<()> {
        let root = &self.mount_root;
        // hostname
        if !self.dry_run {
            let hostname = &self.config.hostname;
            std::fs::write(format!("{root}/etc/hostname"), hostname)?;
        } else {
            eprintln!(
                "[dry-run] hostname={} locale={} tz={} user={}",
                self.config.hostname,
                self.config.locale,
                self.config.timezone,
                self.config.username
            );
        }
        // usuário
        self.cmd(
            "chroot",
            &[
                root,
                "useradd",
                "-m",
                "-s",
                "/bin/bash",
                &self.config.username,
            ],
        )?;
        // senha (via chpasswd)
        if !self.dry_run {
            let pw_line = format!("{}:{}", self.config.username, self.config.password);
            self.cmd_with_stdin("chroot", &[root, "chpasswd"], &pw_line)?;
        }
        Ok(())
    }

    fn create_pnfs(&self) -> Result<()> {
        let dev = match &self.config.pnfs_device {
            Some(d) => d.clone(),
            None => format!("{}3", self.config.disk),
        };
        let mnt = format!("{}/data", self.mount_root);
        self.cmd("mkdir", &["-p", &mnt])?;
        self.cmd("mount", &[&dev, &mnt])?;
        // Inicializa o PNFS (exFAT + .bfsprivate) via script existente do projeto.
        self.cmd(
            "python3",
            &[
                "/usr/share/pineappleos/Filesystem/pineapplefs.py",
                "init",
                &mnt,
                "--name",
                "PINEAPPLE",
            ],
        )?;
        // fstab
        if !self.dry_run {
            let uuid = self
                .blkid(&dev, "UUID")
                .unwrap_or_else(|_| "UUID=none".into());
            let line = format!("{uuid} /data exfat defaults,nofail 0 0\n");
            use std::io::Write;
            let mut f = std::fs::OpenOptions::new()
                .append(true)
                .open(format!("{}/etc/fstab", self.mount_root))?;
            writeln!(f, "{line}")?;
        }
        Ok(())
    }

    fn blkid(&self, dev: &str, key: &str) -> Result<String> {
        let out = Command::new("blkid")
            .args(["-s", key, "-o", "value", dev])
            .output()
            .map_err(|e| Error::Other(e.to_string()))?;
        let val = String::from_utf8_lossy(&out.stdout).trim().to_string();
        if val.is_empty() {
            return Err(Error::Other(format!("blkid: {key} vazio em {dev}")));
        }
        Ok(format!("{key}={val}"))
    }

    fn finalize(&self) -> Result<()> {
        if !self.dry_run {
            let _ = self.cmd("umount", &["-R", &self.mount_root]);
        } else {
            eprintln!("[dry-run] desmontaria {}", self.mount_root);
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn dry_run_completes() {
        let mut cfg = InstallConfig::default();
        cfg.disk = "/dev/sdz".into();
        cfg.username = "test".into();
        cfg.password = "1234".into();
        cfg.powerbook_id = "PB-TEST".into();
        let mut inst = Installer::new(cfg, true);
        let mut last = 0.0f32;
        inst.run(|p| last = p.percent).unwrap();
        assert!((last - 1.0).abs() < f32::EPSILON);
    }

    #[test]
    fn step_labels_exist() {
        assert_eq!(InstallStep::Validate.label(), "Validando configuração");
        assert!(InstallStep::CopySystem.start_percent() > 0.3);
    }
}
