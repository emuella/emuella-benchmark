//! Versioned experiments, isolated workers and conservative codec comparisons.
pub mod compare;
pub mod contract;
pub mod journey;
pub mod metrics;
pub mod report;
pub mod runner;
pub mod series;

pub type Result<T> = std::result::Result<T, Box<dyn std::error::Error + Send + Sync>>;

pub fn read_json<T: serde::de::DeserializeOwned>(path: &std::path::Path) -> Result<T> {
    Ok(serde_json::from_reader(std::fs::File::open(path)?)?)
}
