INSERT INTO roles (id, name, created_at, updated_at)
VALUES
    (1, 'user',   NOW(), NOW()),
    (2, 'admin',  NOW(), NOW())
ON DUPLICATE KEY UPDATE 
    name = VALUES(name),
    updated_at = NOW();