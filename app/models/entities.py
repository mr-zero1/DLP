"""Transport-neutral UI records. No Qt or network dependencies."""
from dataclasses import dataclass, field

@dataclass
class Endpoint:
    id: str
    name: str
    online: bool = True
    group: str = 'University Lab'
    os: str = 'Windows 11'
    agent: str = '1.0.3'
    ip: str = '10.10.0.21'
    policy_id: str = 'P-001'
    applied_policy_id: str = 'P-001'
    applied_version: int = 4
    last_seen: str = '12 seconds ago'
    activity: list[str] = field(default_factory=lambda: ['Agent heartbeat received', 'Policy applied successfully'])

@dataclass
class Incident:
    id: str
    endpoint_id: str
    channel: str
    rule_id: str
    severity: str
    action: str
    time: str
    status: str = 'Open'
    filename: str = 'finance_sample.txt'
    note: str = ''
    timeline: list[str] = field(default_factory=list)

@dataclass
class Rule:
    id: str
    name: str
    kind: str
    expression: str
    severity: str = 'Medium'
    revision: int = 1
    status: str = 'Draft'
    case_insensitive: bool = True
    match_mode: str = 'Any keyword'
    minimum: int = 1

@dataclass
class Policy:
    id: str
    name: str
    version: int = 1
    status: str = 'Draft'
    rule_ids: list[str] = field(default_factory=list)
    actions: dict[str, str] = field(default_factory=lambda: {'USB': 'Block', 'Clipboard': 'Audit', 'Browser upload': 'Warn', 'Email': 'Not supported'})
    group: str = 'University Lab'
    offline: str = 'Use last valid policy'
    published_snapshot: dict = field(default_factory=dict)

@dataclass
class AuditEvent:
    id: str
    timestamp: str
    actor: str
    action: str
    resource: str
    result: str = 'Success'
    before: dict = field(default_factory=dict)
    after: dict = field(default_factory=dict)

@dataclass
class EnrollmentToken:
    id: str
    name: str
    group: str
    policy_id: str
    expires_at: str
    maximum_uses: int
    uses: int = 0

@dataclass
class Release:
    version: str
    package: str
    size: int = 0
    verified: bool = False
    notes: str = 'Improved local scan queue\nPolicy sync reliability\nUSB event reporting'
