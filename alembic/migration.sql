BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 54133b693f81

CREATE TABLE users (
    id SERIAL NOT NULL, 
    email VARCHAR, 
    hashed_password VARCHAR, 
    is_cs_rep BOOLEAN, 
    PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_users_email ON users (email);

CREATE INDEX ix_users_id ON users (id);

CREATE TYPE ticketstatus AS ENUM ('OPEN', 'IN_PROGRESS', 'CLOSED', 'REOPENED');

CREATE TABLE tickets (
    id SERIAL NOT NULL, 
    title VARCHAR, 
    description TEXT, 
    status ticketstatus, 
    created_at TIMESTAMP WITHOUT TIME ZONE, 
    updated_at TIMESTAMP WITHOUT TIME ZONE, 
    closed_at TIMESTAMP WITHOUT TIME ZONE, 
    user_id INTEGER, 
    category VARCHAR, 
    PRIMARY KEY (id), 
    FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE INDEX ix_tickets_id ON tickets (id);

CREATE TYPE messagetype AS ENUM ('CUSTOMER', 'CS_REP', 'SYSTEM');

CREATE TABLE messages (
    id SERIAL NOT NULL, 
    content TEXT, 
    message_type messagetype, 
    created_at TIMESTAMP WITHOUT TIME ZONE, 
    ticket_id INTEGER, 
    user_id INTEGER, 
    PRIMARY KEY (id), 
    FOREIGN KEY(ticket_id) REFERENCES tickets (id), 
    FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE INDEX ix_messages_id ON messages (id);

CREATE TABLE attachments (
    id SERIAL NOT NULL, 
    filename VARCHAR, 
    file_path VARCHAR, 
    content_type VARCHAR, 
    created_at TIMESTAMP WITHOUT TIME ZONE, 
    message_id INTEGER, 
    PRIMARY KEY (id), 
    FOREIGN KEY(message_id) REFERENCES messages (id)
);

CREATE INDEX ix_attachments_id ON attachments (id);

INSERT INTO alembic_version (version_num) VALUES ('54133b693f81') RETURNING alembic_version.version_num;

COMMIT;

