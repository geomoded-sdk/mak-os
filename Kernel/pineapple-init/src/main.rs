// =============================================================================
//  pineapple-init — init de validação do Pineapple OS (initramfs)
//
//  Substitui gradualmente o script shell Installer/initramfs/.../pineapple-
//  powerbook-check. Roda no estágio init-bottom (com /proc e /sys montados):
//
//   1. Lê /proc/cmdline e extrai -pineapplepowerbookid=<ID> e -pineapplefs=<dev>.
//   2. Valida o ID contra a lista embutida (ids.txt copiado para
//      /pineappleos-ids.txt no initramfs).
//   3. Fora do modo live, valida o volume PNFS (exFAT + .bfsprivate/volume.info).
//   4. Sem ID válido ou sem BFS → imprime o panic estilo macOS e força
//      kernel panic via SysRq (echo c > /proc/sysrq-trigger).
//
//  É um binário pequeno (idealmente estático/musl) embutido no initramfs
//  pelo hook pineapple-powerbook-check. Exit code 0 = boot pode continuar.
// =============================================================================

use std::fs;
use std::io::Write;
use std::path::Path;
use std::process::{Command, Stdio};

const IDS_PATH: &str = "/pineappleos-ids.txt";

fn read_cmdline() -> String {
    fs::read_to_string("/proc/cmdline").unwrap_or_default()
}

fn arg_value<'a>(cmdline: &'a str, name: &str) -> Option<&'a str> {
    for tok in cmdline.split_whitespace() {
        if let Some(v) = tok.strip_prefix(name) {
            return Some(v);
        }
    }
    None
}

/// Panic estilo macOS + SysRq (mesmo comportamento do script shell).
fn panic_macos(reason: &str) -> ! {
    let msg = format!(
        "\n*** Pineapple OS - kernel panic ***\n\n\
         Você precisa reiniciar o computador.\n\
         Mantenha pressionado o botão de energia até que ele desligue,\n\
         e depois pressione novamente.\n\n\
         Motivo: {reason}.\n\n"
    );
    // Tenta escrever no console.
    if let Ok(mut f) = fs::OpenOptions::new().write(true).open("/dev/console") {
        let _ = f.write_all(msg.as_bytes());
    }
    eprintln!("{msg}");

    // Dá tempo de ler.
    std::thread::sleep(std::time::Duration::from_secs(5));

    // Kernel panic de verdade via SysRq.
    if let Ok(mut f) = fs::OpenOptions::new()
        .write(true)
        .open("/proc/sysrq-trigger")
    {
        let _ = f.write_all(b"c");
    }

    // Fallback: trava o boot.
    loop {
        std::thread::sleep(std::time::Duration::from_secs(3600));
    }
}

fn check_pnfs_root(dir: &Path) -> bool {
    let info = dir.join(".bfsprivate/volume.info");
    match fs::read_to_string(&info) {
        Ok(s) => s.contains("\"PNFS\"") && s.contains("\"pnfs-overlay\""),
        Err(_) => false,
    }
}

fn mount_pnfs_check(dev: &str) -> bool {
    // Espera o dispositivo aparecer (até ~30s).
    for _ in 0..30 {
        if Path::new(dev).exists() {
            break;
        }
        std::thread::sleep(std::time::Duration::from_secs(1));
    }
    if !Path::new(dev).exists() {
        return false;
    }
    let mnt = "/pnfs-check";
    let _ = fs::create_dir_all(mnt);
    let mounted = Command::new("mount")
        .args(["-o", "ro", dev, mnt])
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .map(|s| s.success())
        .unwrap_or(false);
    if !mounted {
        let _ = fs::remove_dir(mnt);
        return false;
    }
    let ok = check_pnfs_root(Path::new(mnt));
    let _ = Command::new("umount").arg(mnt).status();
    let _ = fs::remove_dir(mnt);
    ok
}

fn resolve_fstab_dev(field: &str) -> String {
    if let Some(u) = field.strip_prefix("UUID=") {
        format!("/dev/disk/by-uuid/{u}")
    } else if let Some(u) = field.strip_prefix("PARTUUID=") {
        format!("/dev/disk/by-partuuid/{u}")
    } else if let Some(u) = field.strip_prefix("LABEL=") {
        format!("/dev/disk/by-label/{u}")
    } else if let Some(u) = field.strip_prefix("PARTLABEL=") {
        format!("/dev/disk/by-partlabel/{u}")
    } else {
        field.to_string()
    }
}

fn main() {
    let cmdline = read_cmdline();

    let boot_id = arg_value(&cmdline, "-pineapplepowerbookid=");
    let boot_fs = arg_value(&cmdline, "-pineapplefs=");
    let is_live = cmdline.split_whitespace().any(|t| t == "boot=live");

    // ---- 1. PowerBook ID ----
    let ids = fs::read_to_string(IDS_PATH).unwrap_or_default();
    let valid = match boot_id {
        Some(id) if !id.is_empty() => ids.lines().any(|l| l.trim() == id),
        _ => false,
    };
    if !valid {
        let reason = match boot_id {
            None => "o argumento de boot '-pineapplepowerbookid=<ID>' não foi fornecido",
            Some(id) if id.is_empty() => "o PowerBook ID fornecido está vazio",
            Some(id) => {
                // formata a mensagem com o id sem allocation extras demais
                let _ = id;
                "o PowerBook ID fornecido não é reconhecido"
            }
        };
        panic_macos(reason);
    }

    // ---- 2. Volume PNFS (obrigatório fora do live) ----
    if is_live {
        return;
    }

    let rootmnt = std::env::var("rootmnt").unwrap_or_else(|_| "/".into());

    if let Some(fs_arg) = boot_fs {
        if fs_arg == "root" {
            if !check_pnfs_root(Path::new(&rootmnt)) {
                panic_macos(
                    "o volume PNFS obrigatório não foi encontrado no sistema raiz \
                     (rode Scripts/setup-pnfs.sh)",
                );
            }
        } else if !mount_pnfs_check(fs_arg) {
            panic_macos(&format!(
                "o volume PNFS obrigatório '-pineapplefs={fs_arg}' não é um volume \
                 BFS válido (falta .bfsprivate/volume.info)"
            ));
        }
        return;
    }

    // Sem argumento: detecta /home ou /data no fstab do sistema raiz.
    let fstab_path = format!("{rootmnt}/etc/fstab");
    let mut found = false;
    if let Ok(fstab) = fs::read_to_string(&fstab_path) {
        for line in fstab.lines() {
            let line = line.trim();
            if line.is_empty() || line.starts_with('#') {
                continue;
            }
            let mut it = line.split_whitespace();
            let (Some(dev), Some(mnt), Some(fstype)) = (it.next(), it.next(), it.next()) else {
                continue;
            };
            let is_data = mnt == "/home" || mnt.starts_with("/home/") || mnt == "/data";
            let skip_fs = matches!(fstype, "swap" | "tmpfs" | "proc" | "sysfs" | "devpts");
            if is_data && !skip_fs {
                found = true;
                let real = resolve_fstab_dev(dev);
                if !mount_pnfs_check(&real) {
                    panic_macos(&format!(
                        "o volume de dados BFS montado em '{mnt}' não é um volume \
                         BFS válido (falta .bfsprivate/volume.info)"
                    ));
                }
            }
        }
    }
    if !found && !check_pnfs_root(Path::new(&rootmnt)) {
        panic_macos(
            "volume PNFS obrigatório não encontrado \
             (adicione -pineapplefs=<dispositivo> ou inicialize com Scripts/setup-pnfs.sh)",
        );
    }
}
