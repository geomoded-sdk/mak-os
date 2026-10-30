use crate::error::{Error, Result};
use serde::{Deserialize, Serialize};
use std::process::Command;

/// Informações de uma partição existente.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PartitionInfo {
    pub path: String,
    pub size_bytes: u64,
    pub fstype: String,
    pub mountpoint: Option<String>,
}

/// Informações de um disco block device.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DiskInfo {
    pub path: String,
    pub model: String,
    pub size_bytes: u64,
    pub is_removable: bool,
    pub is_read_only: bool,
    pub partitions: Vec<PartitionInfo>,
}

/// Lista os discos do sistema via `lsblk` (JSON), filtrando loop/ram.
pub fn list_disks() -> Result<Vec<DiskInfo>> {
    let out = Command::new("lsblk")
        .args([
            "-J",
            "-b",
            "-d",
            "-o",
            "NAME,MODEL,SIZE,RO,RM,TYPE",
        ])
        .output()
        .map_err(|e| Error::Other(format!("lsblk indisponível: {e}")))?;

    if !out.status.success() {
        return Err(Error::CommandFailed {
            cmd: "lsblk".into(),
            stderr: String::from_utf8_lossy(&out.stderr).into_owned(),
        });
    }

    let v: serde_json::Value =
        serde_json::from_slice(&out.stdout).map_err(|e| Error::Other(e.to_string()))?;

    let mut disks = Vec::new();
    if let Some(blockdevs) = v["blockdevices"].as_array() {
        for dev in blockdevs {
            let typ = dev["type"].as_str().unwrap_or("");
            if typ != "disk" {
                continue;
            }
            let name = dev["name"].as_str().unwrap_or("");
            if name.starts_with("loop") || name.starts_with("ram") || name.starts_with("zram") {
                continue;
            }
            disks.push(DiskInfo {
                path: format!("/dev/{name}"),
                model: dev["model"]
                    .as_str()
                    .unwrap_or("Desconhecido")
                    .trim()
                    .to_string(),
                size_bytes: dev["size"].as_u64().unwrap_or(0),
                is_removable: dev["rm"].as_u64().unwrap_or(0) == 1,
                is_read_only: dev["ro"].as_u64().unwrap_or(0) == 1,
                partitions: Vec::new(),
            });
        }
    }

    // Partições de cada disco (segundo lsblk sem -d).
    if let Ok(out2) = Command::new("lsblk")
        .args(["-J", "-b", "-o", "NAME,TYPE,SIZE,FSTYPE,MOUNTPOINT"])
        .output()
    {
        if let Ok(v2) = serde_json::from_slice::<serde_json::Value>(&out2.stdout) {
            if let Some(devs) = v2["blockdevices"].as_array() {
                for dev in devs {
                    if dev["type"].as_str() != Some("disk") {
                        continue;
                    }
                    let disk_name = dev["name"].as_str().unwrap_or("");
                    if let Some(children) = dev["children"].as_array() {
                        for p in children {
                            let pname = p["name"].as_str().unwrap_or("");
                            if let Some(d) = disks.iter_mut().find(|d| {
                                d.path == format!("/dev/{disk_name}")
                            }) {
                                d.partitions.push(PartitionInfo {
                                    path: format!("/dev/{pname}"),
                                    size_bytes: p["size"].as_u64().unwrap_or(0),
                                    fstype: p["fstype"]
                                        .as_str()
                                        .unwrap_or("")
                                        .to_string(),
                                    mountpoint: p["mountpoint"].as_str().map(String::from),
                                });
                            }
                        }
                    }
                }
            }
        }
    }

    Ok(disks)
}

/// Formata bytes em legível humano (KiB/MiB/GiB).
pub fn human_size(bytes: u64) -> String {
    const KIB: f64 = 1024.0;
    const MIB: f64 = KIB * 1024.0;
    const GIB: f64 = MIB * 1024.0;
    let b = bytes as f64;
    if b >= GIB {
        format!("{:.1} GiB", b / GIB)
    } else if b >= MIB {
        format!("{:.1} MiB", b / MIB)
    } else if b >= KIB {
        format!("{:.1} KiB", b / KIB)
    } else {
        format!("{bytes} B")
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn human_size_formats() {
        assert_eq!(human_size(0), "0 B");
        assert_eq!(human_size(1024), "1.0 KiB");
        assert_eq!(human_size(1024 * 1024 * 3), "3.0 MiB");
        assert_eq!(human_size(1024u64.pow(3) * 512 / 1024), "512.0 MiB");
    }
}
