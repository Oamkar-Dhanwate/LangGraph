# SQL schema
-- ╔══════════════════════════════════════════════════════════════════════════╗
-- ║          ClientIQ — TiDB Database Schema                               ║
-- ║          Enterprise Multi-Agent Intelligence Platform                  ║
-- ╚══════════════════════════════════════════════════════════════════════════╝

CREATE DATABASE IF NOT EXISTS clientiq CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE clientiq;

-- ─────────────────────────────────────────────────────────────────────────────
-- RBAC: Users & Roles
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS roles (
    id          VARCHAR(36)  PRIMARY KEY DEFAULT (UUID()),
    name        VARCHAR(50)  NOT NULL UNIQUE,            -- admin, manager, analyst, viewer
    permissions JSON         NOT NULL,                   -- {"read_crm": true, "write_crm": false, ...}
    created_at  DATETIME     NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS users (
    id              VARCHAR(36)  PRIMARY KEY DEFAULT (UUID()),
    email           VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    full_name       VARCHAR(255) NOT NULL,
    role_id         VARCHAR(36)  NOT NULL,
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
    last_login      DATETIME,
    created_at      DATETIME     NOT NULL DEFAULT NOW(),
    FOREIGN KEY (role_id) REFERENCES roles(id)
);

-- ─────────────────────────────────────────────────────────────────────────────
-- CRM: Companies, Contacts
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS companies (
    id              VARCHAR(36)   PRIMARY KEY DEFAULT (UUID()),
    name            VARCHAR(255)  NOT NULL,
    industry        VARCHAR(100),
    size_category   ENUM('startup','smb','mid_market','enterprise') DEFAULT 'smb',
    annual_revenue  DECIMAL(15,2),
    country         VARCHAR(100)  DEFAULT 'United States',
    website         VARCHAR(255),
    account_tier    ENUM('bronze','silver','gold','platinum') DEFAULT 'silver',
    health_score    DECIMAL(5,2)  DEFAULT 70.00,         -- 0–100
    churn_risk      DECIMAL(5,4)  DEFAULT 0.1000,        -- 0.0–1.0
    created_at      DATETIME      NOT NULL DEFAULT NOW(),
    updated_at      DATETIME      NOT NULL DEFAULT NOW() ON UPDATE NOW()
);

CREATE TABLE IF NOT EXISTS contacts (
    id              VARCHAR(36)   PRIMARY KEY DEFAULT (UUID()),
    company_id      VARCHAR(36)   NOT NULL,
    first_name      VARCHAR(100)  NOT NULL,
    last_name       VARCHAR(100)  NOT NULL,
    email           VARCHAR(255)  NOT NULL,
    phone           VARCHAR(50),
    job_title       VARCHAR(150),
    department      VARCHAR(100),
    is_primary      BOOLEAN       DEFAULT FALSE,
    sentiment_score DECIMAL(5,4)  DEFAULT 0.0,           -- -1.0 to 1.0
    last_contacted  DATETIME,
    created_at      DATETIME      NOT NULL DEFAULT NOW(),
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
);

-- ─────────────────────────────────────────────────────────────────────────────
-- Sales: Opportunities / Pipeline
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS opportunities (
    id              VARCHAR(36)   PRIMARY KEY DEFAULT (UUID()),
    company_id      VARCHAR(36)   NOT NULL,
    owner_id        VARCHAR(36),                          -- FK to users
    name            VARCHAR(255)  NOT NULL,
    stage           ENUM('prospecting','qualification','proposal','negotiation','closed_won','closed_lost') DEFAULT 'prospecting',
    amount          DECIMAL(15,2) NOT NULL DEFAULT 0,
    probability     DECIMAL(5,2)  DEFAULT 0,              -- 0–100 %
    close_date      DATE,
    source          VARCHAR(100),
    notes           TEXT,
    created_at      DATETIME      NOT NULL DEFAULT NOW(),
    updated_at      DATETIME      NOT NULL DEFAULT NOW() ON UPDATE NOW(),
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
    FOREIGN KEY (owner_id)   REFERENCES users(id)
);

-- ─────────────────────────────────────────────────────────────────────────────
-- Contracts
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS contracts (
    id              VARCHAR(36)   PRIMARY KEY DEFAULT (UUID()),
    company_id      VARCHAR(36)   NOT NULL,
    opportunity_id  VARCHAR(36),
    title           VARCHAR(255)  NOT NULL,
    contract_type   ENUM('saas','professional_services','support','partnership','nda') DEFAULT 'saas',
    value           DECIMAL(15,2) NOT NULL,
    currency        VARCHAR(10)   DEFAULT 'USD',
    start_date      DATE          NOT NULL,
    end_date        DATE          NOT NULL,
    auto_renew      BOOLEAN       DEFAULT FALSE,
    status          ENUM('draft','active','expired','terminated') DEFAULT 'active',
    terms_text      LONGTEXT,
    signed_at       DATETIME,
    created_at      DATETIME      NOT NULL DEFAULT NOW(),
    FOREIGN KEY (company_id)     REFERENCES companies(id),
    FOREIGN KEY (opportunity_id) REFERENCES opportunities(id)
);

-- ─────────────────────────────────────────────────────────────────────────────
-- Communications: Emails, Meetings, Calls
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS emails (
    id              VARCHAR(36)   PRIMARY KEY DEFAULT (UUID()),
    company_id      VARCHAR(36)   NOT NULL,
    contact_id      VARCHAR(36),
    user_id         VARCHAR(36),
    direction       ENUM('inbound','outbound') DEFAULT 'outbound',
    subject         VARCHAR(500)  NOT NULL,
    body            LONGTEXT      NOT NULL,
    sentiment_score DECIMAL(5,4)  DEFAULT 0.0,
    sentiment_label ENUM('positive','neutral','negative') DEFAULT 'neutral',
    thread_id       VARCHAR(36),
    sent_at         DATETIME      NOT NULL DEFAULT NOW(),
    FOREIGN KEY (company_id) REFERENCES companies(id),
    FOREIGN KEY (contact_id) REFERENCES contacts(id),
    FOREIGN KEY (user_id)    REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS meetings (
    id              VARCHAR(36)   PRIMARY KEY DEFAULT (UUID()),
    company_id      VARCHAR(36)   NOT NULL,
    title           VARCHAR(255)  NOT NULL,
    meeting_type    ENUM('discovery','demo','qbr','renewal','support','kickoff','other') DEFAULT 'other',
    attendees       JSON,                                  -- [{name, email, role}]
    notes           LONGTEXT,
    action_items    JSON,                                  -- [{owner, task, due_date}]
    sentiment_score DECIMAL(5,4)  DEFAULT 0.0,
    duration_mins   INT           DEFAULT 60,
    scheduled_at    DATETIME      NOT NULL,
    created_at      DATETIME      NOT NULL DEFAULT NOW(),
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

CREATE TABLE IF NOT EXISTS call_transcripts (
    id              VARCHAR(36)   PRIMARY KEY DEFAULT (UUID()),
    company_id      VARCHAR(36)   NOT NULL,
    contact_id      VARCHAR(36),
    call_type       ENUM('sales','support','renewal','escalation','other') DEFAULT 'other',
    duration_secs   INT           DEFAULT 0,
    transcript      LONGTEXT      NOT NULL,
    summary         TEXT,
    sentiment_score DECIMAL(5,4)  DEFAULT 0.0,
    key_topics      JSON,                                  -- ["pricing", "integration", ...]
    called_at       DATETIME      NOT NULL,
    created_at      DATETIME      NOT NULL DEFAULT NOW(),
    FOREIGN KEY (company_id) REFERENCES companies(id),
    FOREIGN KEY (contact_id) REFERENCES contacts(id)
);

-- ─────────────────────────────────────────────────────────────────────────────
-- Support Tickets
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS support_tickets (
    id              VARCHAR(36)   PRIMARY KEY DEFAULT (UUID()),
    company_id      VARCHAR(36)   NOT NULL,
    contact_id      VARCHAR(36),
    ticket_number   VARCHAR(50)   NOT NULL UNIQUE,
    title           VARCHAR(500)  NOT NULL,
    description     LONGTEXT      NOT NULL,
    priority        ENUM('low','medium','high','critical') DEFAULT 'medium',
    status          ENUM('open','in_progress','pending_customer','resolved','closed') DEFAULT 'open',
    category        VARCHAR(100),
    resolution      TEXT,
    sentiment_score DECIMAL(5,4)  DEFAULT 0.0,
    first_response_hrs INT,
    resolution_hrs  INT,
    opened_at       DATETIME      NOT NULL DEFAULT NOW(),
    resolved_at     DATETIME,
    FOREIGN KEY (company_id) REFERENCES companies(id),
    FOREIGN KEY (contact_id) REFERENCES contacts(id)
);

-- ─────────────────────────────────────────────────────────────────────────────
-- Analytics: Health Snapshots, Sentiment Timeline
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS health_snapshots (
    id              VARCHAR(36)   PRIMARY KEY DEFAULT (UUID()),
    company_id      VARCHAR(36)   NOT NULL,
    health_score    DECIMAL(5,2)  NOT NULL,
    churn_risk      DECIMAL(5,4)  NOT NULL,
    sentiment_avg   DECIMAL(5,4),
    ticket_count    INT           DEFAULT 0,
    engagement_rate DECIMAL(5,4)  DEFAULT 0,
    snapshot_date   DATE          NOT NULL,
    computed_at     DATETIME      NOT NULL DEFAULT NOW(),
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

CREATE TABLE IF NOT EXISTS sentiment_timeline (
    id              VARCHAR(36)   PRIMARY KEY DEFAULT (UUID()),
    company_id      VARCHAR(36)   NOT NULL,
    source_type     ENUM('email','meeting','call','ticket') NOT NULL,
    source_id       VARCHAR(36)   NOT NULL,
    sentiment_score DECIMAL(5,4)  NOT NULL,
    sentiment_label ENUM('positive','neutral','negative') NOT NULL,
    recorded_at     DATETIME      NOT NULL,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

-- ─────────────────────────────────────────────────────────────────────────────
-- Knowledge Graph: Entities & Relationships
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS kg_entities (
    id              VARCHAR(36)   PRIMARY KEY DEFAULT (UUID()),
    entity_type     ENUM('company','contact','product','topic','event','risk') NOT NULL,
    name            VARCHAR(255)  NOT NULL,
    properties      JSON,
    source_id       VARCHAR(36),
    created_at      DATETIME      NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS kg_relationships (
    id              VARCHAR(36)   PRIMARY KEY DEFAULT (UUID()),
    source_entity   VARCHAR(36)   NOT NULL,
    target_entity   VARCHAR(36)   NOT NULL,
    relation_type   VARCHAR(100)  NOT NULL,               -- "contracted_with", "escalated_to", etc.
    weight          DECIMAL(5,4)  DEFAULT 1.0,
    properties      JSON,
    created_at      DATETIME      NOT NULL DEFAULT NOW(),
    FOREIGN KEY (source_entity) REFERENCES kg_entities(id),
    FOREIGN KEY (target_entity) REFERENCES kg_entities(id)
);

-- ─────────────────────────────────────────────────────────────────────────────
-- Audit Logs
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS audit_logs (
    id              VARCHAR(36)   PRIMARY KEY DEFAULT (UUID()),
    user_id         VARCHAR(36),
    action          VARCHAR(100)  NOT NULL,               -- "query_executed", "data_exported", etc.
    resource_type   VARCHAR(100),
    resource_id     VARCHAR(36),
    details         JSON,
    ip_address      VARCHAR(45),
    user_agent      VARCHAR(500),
    status          ENUM('success','failure','blocked') DEFAULT 'success',
    created_at      DATETIME      NOT NULL DEFAULT NOW(),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- ─────────────────────────────────────────────────────────────────────────────
-- Conversation Memory (Agent Sessions)
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS agent_sessions (
    id              VARCHAR(36)   PRIMARY KEY DEFAULT (UUID()),
    user_id         VARCHAR(36),
    session_token   VARCHAR(255)  NOT NULL UNIQUE,
    conversation    JSON          NOT NULL,               -- [{role, content, timestamp}]
    context         JSON,                                  -- current entity context
    total_tokens    INT           DEFAULT 0,
    created_at      DATETIME      NOT NULL DEFAULT NOW(),
    last_active     DATETIME      NOT NULL DEFAULT NOW(),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- ─────────────────────────────────────────────────────────────────────────────
-- Indexes for performance
-- ─────────────────────────────────────────────────────────────────────────────

CREATE INDEX idx_companies_health     ON companies(health_score);
CREATE INDEX idx_companies_churn      ON companies(churn_risk);
CREATE INDEX idx_contacts_company     ON contacts(company_id);
CREATE INDEX idx_emails_company       ON emails(company_id);
CREATE INDEX idx_emails_sent_at       ON emails(sent_at);
CREATE INDEX idx_tickets_company      ON support_tickets(company_id);
CREATE INDEX idx_tickets_status       ON support_tickets(status);
CREATE INDEX idx_health_company_date  ON health_snapshots(company_id, snapshot_date);
CREATE INDEX idx_sentiment_company    ON sentiment_timeline(company_id, recorded_at);
CREATE INDEX idx_audit_user           ON audit_logs(user_id, created_at);
CREATE INDEX idx_kg_source            ON kg_entities(source_id);
