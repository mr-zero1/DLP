use chrono::{SecondsFormat, Utc};
use rusqlite::{Connection, params};
use std::collections::BTreeMap;
use std::env;
use std::error::Error;
use std::path::{Path, PathBuf};
use uuid::Uuid;

#[derive(Debug, PartialEq, Eq)]
pub struct Event {
    pub id: Uuid,
    pub event_type: String,
    pub severity: String,
    pub timestamp: String,
    pub payload: BTreeMap<String, String>,
}

#[derive(Debug, PartialEq, Eq)]
pub struct EventCounts {
    pub total: i64,
    pub pending: i64,
    pub sent: i64,
}

pub struct EventQueue {
    connection: Connection,
}

impl Event {
    pub fn new(
        event_type: impl Into<String>,
        severity: impl Into<String>,
        payload: BTreeMap<String, String>,
    ) -> Self {
        Self {
            id: Uuid::new_v4(),
            event_type: event_type.into(),
            severity: severity.into(),
            timestamp: Utc::now().to_rfc3339_opts(SecondsFormat::Millis, true),
            payload,
        }
    }
}

impl EventQueue {
    pub fn default_path() -> Result<PathBuf, Box<dyn Error>> {
        let local_appdata =
            env::var_os("LOCALAPPDATA").ok_or("LOCALAPPDATA environment variable is missing")?;
        Ok(PathBuf::from(local_appdata)
            .join("NeonSentinel")
            .join("events.sqlite3"))
    }

    pub fn open_default() -> Result<Self, Box<dyn Error>> {
        let path = Self::default_path()?;
        let parent = path.parent().ok_or("Invalid event database path")?;
        std::fs::create_dir_all(parent)?;
        Ok(Self::open(path)?)
    }

    pub fn open(path: impl AsRef<Path>) -> rusqlite::Result<Self> {
        let connection = Connection::open(path)?;
        connection.execute_batch(
            "CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY NOT NULL,
                event_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'sent'))
            );
            CREATE INDEX IF NOT EXISTS events_pending_timestamp
                ON events(timestamp, id) WHERE status = 'pending';",
        )?;
        Ok(Self { connection })
    }

    pub fn insert(&self, event: &Event) -> rusqlite::Result<bool> {
        let payload = serde_json::to_string(&event.payload)
            .map_err(|error| rusqlite::Error::ToSqlConversionFailure(Box::new(error)))?;
        let inserted = self.connection.execute(
            "INSERT INTO events
                (id, event_type, severity, timestamp, payload_json)
             VALUES (?1, ?2, ?3, ?4, ?5)
             ON CONFLICT(id) DO NOTHING",
            params![
                event.id.to_string(),
                event.event_type,
                event.severity,
                event.timestamp,
                payload
            ],
        )?;
        Ok(inserted == 1)
    }

    pub fn pending_events(&self) -> rusqlite::Result<Vec<Event>> {
        let mut statement = self.connection.prepare(
            "SELECT id, event_type, severity, timestamp, payload_json
             FROM events WHERE status = 'pending'
             ORDER BY timestamp, id",
        )?;
        let rows = statement.query_map([], |row| {
            let id: String = row.get(0)?;
            let payload: String = row.get(4)?;
            Ok((
                id,
                row.get::<_, String>(1)?,
                row.get::<_, String>(2)?,
                row.get::<_, String>(3)?,
                payload,
            ))
        })?;

        rows.map(|row| {
            let (id, event_type, severity, timestamp, payload) = row?;
            let id = Uuid::parse_str(&id).map_err(|error| {
                rusqlite::Error::FromSqlConversionFailure(
                    0,
                    rusqlite::types::Type::Text,
                    Box::new(error),
                )
            })?;
            let payload = serde_json::from_str(&payload).map_err(|error| {
                rusqlite::Error::FromSqlConversionFailure(
                    4,
                    rusqlite::types::Type::Text,
                    Box::new(error),
                )
            })?;
            Ok(Event {
                id,
                event_type,
                severity,
                timestamp,
                payload,
            })
        })
        .collect()
    }

    pub fn mark_sent(&self, id: Uuid) -> rusqlite::Result<bool> {
        let changed = self.connection.execute(
            "UPDATE events SET status = 'sent' WHERE id = ?1 AND status = 'pending'",
            [id.to_string()],
        )?;
        Ok(changed == 1)
    }

    pub fn counts(&self) -> rusqlite::Result<EventCounts> {
        self.connection.query_row(
            "SELECT COUNT(*),
                    COALESCE(SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END), 0),
                    COALESCE(SUM(CASE WHEN status = 'sent' THEN 1 ELSE 0 END), 0)
             FROM events",
            [],
            |row| {
                Ok(EventCounts {
                    total: row.get(0)?,
                    pending: row.get(1)?,
                    sent: row.get(2)?,
                })
            },
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn test_database() -> (PathBuf, PathBuf) {
        let folder = env::temp_dir().join(format!("neon-queue-test-{}", Uuid::new_v4()));
        std::fs::create_dir_all(&folder).unwrap();
        let database = folder.join("events.sqlite3");
        (folder, database)
    }

    fn demo_event() -> Event {
        let mut payload = BTreeMap::new();
        payload.insert("source".into(), "demo".into());
        payload.insert("purpose".into(), "queue test".into());
        Event::new("demo", "info", payload)
    }

    #[test]
    fn events_persist_across_reopening_database() {
        let (folder, database) = test_database();
        let event = demo_event();
        {
            let queue = EventQueue::open(&database).unwrap();
            assert!(queue.insert(&event).unwrap());
        }
        {
            let queue = EventQueue::open(&database).unwrap();
            assert_eq!(queue.pending_events().unwrap(), vec![event]);
        }
        std::fs::remove_dir_all(folder).unwrap();
    }

    #[test]
    fn duplicate_event_ids_are_not_inserted_twice() {
        let (folder, database) = test_database();
        let queue = EventQueue::open(&database).unwrap();
        let event = demo_event();
        assert!(queue.insert(&event).unwrap());
        assert!(!queue.insert(&event).unwrap());
        assert_eq!(queue.counts().unwrap().total, 1);
        drop(queue);
        std::fs::remove_dir_all(folder).unwrap();
    }

    #[test]
    fn marking_sent_updates_pending_events_and_counts() {
        let (folder, database) = test_database();
        let queue = EventQueue::open(&database).unwrap();
        assert_eq!(
            queue.counts().unwrap(),
            EventCounts {
                total: 0,
                pending: 0,
                sent: 0,
            }
        );
        let event = demo_event();
        assert!(queue.insert(&event).unwrap());
        assert_eq!(
            queue.counts().unwrap(),
            EventCounts {
                total: 1,
                pending: 1,
                sent: 0,
            }
        );
        assert!(queue.mark_sent(event.id).unwrap());
        assert!(!queue.mark_sent(event.id).unwrap());
        assert!(queue.pending_events().unwrap().is_empty());
        assert_eq!(
            queue.counts().unwrap(),
            EventCounts {
                total: 1,
                pending: 0,
                sent: 1,
            }
        );
        drop(queue);
        std::fs::remove_dir_all(folder).unwrap();
    }
}
