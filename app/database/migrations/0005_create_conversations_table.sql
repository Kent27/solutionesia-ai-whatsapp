CREATE TABLE IF NOT EXISTS conversations (
    id VARCHAR(255) PRIMARY KEY,
    contact_id BIGINT NOT NULL,
    metadata JSON,
    mode VARCHAR(50) DEFAULT NULL,
    status VARCHAR(50) DEFAULT 'active',
    FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE CASCADE,
    INDEX idx_conv_status (status)
);

CREATE TABLE IF NOT EXISTS messages (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    conversation_id VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    content_type VARCHAR(50) DEFAULT NULL,
    status VARCHAR(50) DEFAULT NULL,
    role VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    INDEX idx_conv_messages (conversation_id, created_at)
);

CREATE TABLE IF NOT EXISTS memory_units (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    conversation_id VARCHAR(255) NOT NULL,
    abstracted_content TEXT,
    embedding_vector BLOB, 
    keywords JSON,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    consolidation_level INT DEFAULT 0,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    INDEX idx_mem_conv_time (conversation_id, timestamp),
    INDEX idx_mem_level (consolidation_level)
);