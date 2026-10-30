// =============================================================================
//  orchard-core — motor de instalação do Pineapple OS (sem UI)
//
//  A UI (GTK4 ou GLS Render) consome apenas esta API. O motor é quem toca disco,
//  copia o sistema e configura o boot. Tudo é serializável em JSON para a UI
//  salvar/restaurar o estado da instalação.
// =============================================================================

pub mod config;
pub mod disk;
pub mod error;
pub mod installer;

pub use config::{InstallConfig, PartitionMode};
pub use disk::{list_disks, DiskInfo, PartitionInfo};
pub use error::Error;
pub use installer::{InstallProgress, InstallStep, Installer};
