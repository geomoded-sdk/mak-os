use serde::{Deserialize, Serialize};

/// Como o Orchard prepara o disco de destino.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum PartitionMode {
    /// Apaga o disco inteiro e cria as partições do Pineapple OS.
    Erase,
    /// Instala ao lado de outro sistema (reduz a partição existente).
    Alongside,
    /// Partições definidas manualmente (avançado).
    Manual,
}

/// Configuração completa de uma instalação — a fonte única de verdade
/// consumida pelo motor e pela UI.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InstallConfig {
    /// Disco de destino, ex.: "/dev/sda".
    pub disk: String,
    /// Modo de partição.
    pub mode: PartitionMode,
    /// Tamanho da partição raiz em MiB (0 = todo o disco disponível).
    pub root_size_mib: u64,

    /// Hostname do sistema.
    pub hostname: String,
    /// Usuário primário.
    pub username: String,
    /// Senha do usuário (em texto plano só durante a instalação).
    pub password: String,

    /// Locale, ex.: "pt_BR.UTF-8".
    pub locale: String,
    /// Layout de teclado, ex.: "br".
    pub keyboard_layout: String,
    /// Fuso horário, ex.: "America/Sao_Paulo".
    pub timezone: String,

    /// PowerBook ID obrigatório no boot (ver ids.txt).
    pub powerbook_id: String,
    /// Dispositivo do volume PNFS (ex.: "/dev/sda2"); None = criar um.
    pub pnfs_device: Option<String>,
}

impl Default for InstallConfig {
    fn default() -> Self {
        Self {
            disk: String::new(),
            mode: PartitionMode::Erase,
            root_size_mib: 0,
            hostname: "pineapple".into(),
            username: String::new(),
            password: String::new(),
            locale: "pt_BR.UTF-8".into(),
            keyboard_layout: "br".into(),
            timezone: "America/Sao_Paulo".into(),
            powerbook_id: String::new(),
            pnfs_device: None,
        }
    }
}

impl InstallConfig {
    /// Valida os campos antes de iniciar a instalação.
    pub fn validate(&self) -> Result<(), String> {
        if self.disk.is_empty() {
            return Err("nenhum disco selecionado".into());
        }
        if !self.disk.starts_with("/dev/") {
            return Err(format!("caminho de disco inválido: {}", self.disk));
        }
        if self.username.is_empty() {
            return Err("usuário vazio".into());
        }
        if self.username == "root" {
            return Err("não é possível usar 'root' como usuário".into());
        }
        if self.password.len() < 4 {
            return Err("a senha precisa de pelo menos 4 caracteres".into());
        }
        if self.hostname.is_empty() {
            return Err("hostname vazio".into());
        }
        if self.powerbook_id.is_empty() {
            return Err("PowerBook ID vazio (obrigatório no boot)".into());
        }
        Ok(())
    }

    /// Serializa a configuração em JSON (para a UI salvar/restaurar).
    pub fn to_json(&self) -> String {
        serde_json::to_string_pretty(self).unwrap_or_default()
    }

    /// Desserializa a configuração de JSON.
    pub fn from_json(s: &str) -> Result<Self, serde_json::Error> {
        serde_json::from_str(s)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn default_is_invalid_until_filled() {
        let c = InstallConfig::default();
        assert!(c.validate().is_err());
    }

    #[test]
    fn json_roundtrip() {
        let mut c = InstallConfig::default();
        c.disk = "/dev/sda".into();
        c.username = "flavi".into();
        c.password = "1234".into();
        c.powerbook_id = "PB-001".into();
        let j = c.to_json();
        let back = InstallConfig::from_json(&j).unwrap();
        assert_eq!(back.username, "flavi");
    }
}
