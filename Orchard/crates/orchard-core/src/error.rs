use thiserror::Error;

#[derive(Error, Debug)]
pub enum Error {
    #[error("disco não encontrado: {0}")]
    DiskNotFound(String),

    #[error("configuração inválida: {0}")]
    InvalidConfig(String),

    #[error("falha ao executar {cmd}: {stderr}")]
    CommandFailed { cmd: String, stderr: String },

    #[error("etapa falhou: {step}: {reason}")]
    StepFailed { step: String, reason: String },

    #[error("io: {0}")]
    Io(#[from] std::io::Error),

    #[error("{0}")]
    Other(String),
}

pub type Result<T> = std::result::Result<T, Error>;
