CREATE TABLE IF NOT EXISTS organizations (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    phone_id VARCHAR(255), -- WhatsApp Business phone ID
    agent_id VARCHAR(255), -- LLM Agent ID
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE,
    status VARCHAR(50) DEFAULT "active",
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS organization_roles (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    organization_id BIGINT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
);
ALTER TABLE organization_users 
ADD COLUMN organization_role_id BIGINT DEFAULT NULL,
ADD CONSTRAINT fk_organization_role 
    FOREIGN KEY (organization_role_id) 
    REFERENCES organization_roles(id) 
    ON DELETE SET NULL;

CREATE TABLE IF NOT EXISTS organization_permissions (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    description VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS organization_role_permissions (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    organization_role_id BIGINT NOT NULL,
    organization_permission_id BIGINT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (organization_role_id) REFERENCES organization_roles(id) ON DELETE CASCADE,
    FOREIGN KEY (organization_permission_id) REFERENCES organization_permissions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS roles (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS organization_users (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    organization_id BIGINT NOT NULL,
    role_id BIGINT NOT NULL,
    phone_number VARCHAR(255) NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES roles(id),
    INDEX (user_id, organization_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

ALTER TABLE contacts
ADD COLUMN organization_id BIGINT NULL,
ADD FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
ADD INDEX (organization_id);
