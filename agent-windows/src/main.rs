//! NEON SENTINEL — Phase 2 educational Windows Agent.
//! Only registration and heartbeat. No file monitoring or tamper protection.

use reqwest::StatusCode;
use reqwest::blocking::Client;
use serde::Serialize;
use std::env;
use std::error::Error;
use std::fs::{self, OpenOptions};
use std::io::{ErrorKind, Write};
use std::path::{Path, PathBuf};
use std::thread;
use std::time::Duration;
use uuid::Uuid;

pub mod event_queue;

// The HTTP address is intentionally fixed to the user's isolated lab.
// Replace this with an HTTPS configuration before any real deployment.
const SERVER: &str = "http://192.168.122.1:5000";
const HEARTBEAT_INTERVAL: Duration = Duration::from_secs(30 * 60);
const RETRY_INTERVAL: Duration = Duration::from_secs(60);

#[derive(Serialize)]
struct Registration<'a> {
    device_id: &'a str,
    hostname: &'a str,
    platform: &'a str,
}

fn identity_file() -> Result<PathBuf, Box<dyn Error>> {
    let local_appdata =
        env::var_os("LOCALAPPDATA").ok_or("LOCALAPPDATA environment variable is missing")?;
    Ok(PathBuf::from(local_appdata)
        .join("NeonSentinel")
        .join("device_id.txt"))
}

// A real endpoint keeps the same UUID even when the agent is restarted.
// A corrupt/unreadable file is an error, NOT a reason to silently change identity.
fn load_or_create_identity(path: &Path) -> Result<Uuid, Box<dyn Error>> {
    match fs::read_to_string(path) {
        Ok(existing) => return Ok(Uuid::parse_str(existing.trim())?),
        Err(e) if e.kind() == ErrorKind::NotFound => {}
        Err(e) => return Err(e.into()),
    }

    let parent = path.parent().ok_or("Invalid identity file path")?;
    fs::create_dir_all(parent)?;
    let id = Uuid::new_v4();
    let mut file = OpenOptions::new().write(true).create_new(true).open(path)?;
    writeln!(file, "{id}")?;
    file.sync_all()?;
    Ok(id)
}

fn hostname() -> Result<String, Box<dyn Error>> {
    let name = env::var("COMPUTERNAME")?;
    if name.trim().is_empty() || name.len() > 255 || name.chars().any(char::is_control) {
        return Err("Invalid COMPUTERNAME".into());
    }
    Ok(name)
}

fn heartbeat(client: &Client, token: &str, id: Uuid) -> Result<StatusCode, Box<dyn Error>> {
    let url = format!("{SERVER}/api/v1/devices/{id}/heartbeat");
    let response = client.post(url).bearer_auth(token).send()?;
    Ok(response.status())
}

fn register(
    client: &Client,
    token: &str,
    id: Uuid,
    name: &str,
) -> Result<StatusCode, Box<dyn Error>> {
    let id_text = id.to_string();
    let payload = Registration {
        device_id: &id_text,
        hostname: name,
        // Rust's stdlib identifies Windows, not the exact edition (10/11).
        platform: "Windows",
    };
    let response = client
        .post(format!("{SERVER}/api/v1/devices/register"))
        .bearer_auth(token)
        .json(&payload)
        .send()?;
    Ok(response.status())
}

fn sync_once(client: &Client, token: &str, id: Uuid, name: &str) -> Result<(), Box<dyn Error>> {
    let first_status = heartbeat(client, token, id)?;
    match first_status {
        StatusCode::OK => {
            println!("Heartbeat accepted: device {id}");
            Ok(())
        }
        StatusCode::NOT_FOUND => {
            println!("Device not registered; enrolling {name} ...");
            let register_status = register(client, token, id, name)?;
            match register_status {
                StatusCode::CREATED => println!("Device registration succeeded."),
                StatusCode::CONFLICT => println!("Device already registered; reusing its UUID."),
                other => return Err(format!("Registration failed: HTTP {other}").into()),
            }
            let second_status = heartbeat(client, token, id)?;
            if second_status != StatusCode::OK {
                return Err(
                    format!("Post-registration heartbeat failed: HTTP {second_status}").into(),
                );
            }
            println!("Initial heartbeat accepted.");
            Ok(())
        }
        other => Err(format!("Heartbeat failed: HTTP {other}").into()),
    }
}

fn main() -> Result<(), Box<dyn Error>> {
    if !cfg!(target_os = "windows") {
        return Err("Run this Agent on Windows, not Linux".into());
    }

    let args: Vec<String> = env::args().skip(1).collect();
    if args.iter().any(|s| s == "--help" || s == "-h") {
        println!(
            "Usage: neon-sentinel-agent.exe [--once | --demo-event | --queue-status]\n\
             --once: register/heartbeat once, then exit\n\
             --demo-event: add one synthetic metadata-only event\n\
             --queue-status: display queued event counts"
        );
        return Ok(());
    }
    if args.len() > 1
        || (args.len() == 1
            && !["--once", "--demo-event", "--queue-status"].contains(&args[0].as_str()))
    {
        return Err("Unknown argument. Use --help".into());
    }
    match args.first().map(String::as_str) {
        Some("--demo-event") => {
            let queue = event_queue::EventQueue::open_default()?;
            let mut payload = std::collections::BTreeMap::new();
            payload.insert("source".into(), "command_line".into());
            payload.insert("purpose".into(), "synthetic demonstration event".into());
            let event = event_queue::Event::new("demo", "info", payload);
            if queue.insert(&event)? {
                println!("Queued demo event: {}", event.id);
            }
            return Ok(());
        }
        Some("--queue-status") => {
            let queue = event_queue::EventQueue::open_default()?;
            let counts = queue.counts()?;
            println!(
                "Events: total={}, pending={}, sent={}",
                counts.total, counts.pending, counts.sent
            );
            return Ok(());
        }
        _ => {}
    }
    let once = args.first().is_some_and(|s| s == "--once");

    let token = env::var("NEON_SENTINEL_API_TOKEN")
        .map_err(|_| "Set NEON_SENTINEL_API_TOKEN in this PowerShell session first")?;
    if token.trim().is_empty() {
        return Err("NEON_SENTINEL_API_TOKEN must not be empty".into());
    }

    let id_file = identity_file()?;
    let id = load_or_create_identity(&id_file)?;
    let name = hostname()?;

    let client = Client::builder()
        .no_proxy() // Bypass any system proxy for the isolated lab address.
        .connect_timeout(Duration::from_secs(5))
        .timeout(Duration::from_secs(10))
        .build()?;

    println!("NEON SENTINEL Agent (lab Phase 2)");
    println!("Host: {name}; ID: {id}");
    println!("Identity path: {}", id_file.display());
    println!("Server: {SERVER}");
    println!("Interval: 30 min; failure retry: 60 sec");
    println!("No monitoring, enforcement, event uploads, or Windows Service is active.");

    loop {
        let next_delay = match sync_once(&client, &token, id, &name) {
            Ok(()) => HEARTBEAT_INTERVAL,
            Err(error) => {
                eprintln!("Network/API issue: {error}");
                RETRY_INTERVAL
            }
        };
        if once {
            break;
        }
        thread::sleep(next_delay);
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn identity_is_reused() {
        let folder = env::temp_dir().join(format!("neon-agent-test-{}", Uuid::new_v4()));
        let file = folder.join("id.txt");
        let a = load_or_create_identity(&file).unwrap();
        let b = load_or_create_identity(&file).unwrap();
        assert_eq!(a, b);
        fs::remove_dir_all(folder).unwrap();
    }

    #[test]
    fn corrupt_identity_causes_error() {
        let folder = env::temp_dir().join(format!("neon-agent-test-{}", Uuid::new_v4()));
        fs::create_dir_all(&folder).unwrap();
        let file = folder.join("id.txt");
        fs::write(&file, "corrupt-id").unwrap();
        assert!(load_or_create_identity(&file).is_err());
        fs::remove_dir_all(folder).unwrap();
    }
}
