CREATE TABLE IF NOT EXISTS contacts (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    phone_number VARCHAR(20) NOT NULL UNIQUE,
    email VARCHAR(255) DEFAULT NULL,
    stamps INT DEFAULT 0,
    chat_status VARCHAR(50) DEFAULT NULL,
    thread_id VARCHAR(100) DEFAULT NULL,
    user_id BIGINT NULL,  -- NULLABLE! WhatsApp contacts don't have users
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_phone_number (phone_number),
    INDEX idx_thread_id (thread_id),
    INDEX idx_user_id (user_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS contact_labels (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    contact_id BIGINT NOT NULL,
    label_id BIGINT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_contact_label (contact_id, label_id),
    FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE CASCADE,
    FOREIGN KEY (label_id) REFERENCES labels(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS labels (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    color VARCHAR(20) DEFAULT '#3b82f6',
    user_id BIGINT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_label_name_user (name, user_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
); 