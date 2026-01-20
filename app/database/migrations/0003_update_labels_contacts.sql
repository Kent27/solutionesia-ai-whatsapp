-- Remove user relation
ALTER TABLE labels DROP FOREIGN KEY `1`;
ALTER TABLE labels DROP INDEX unique_label_name_user;
ALTER TABLE labels DROP COLUMN user_id;

-- Remove dependency to thread
ALTER TABLE contacts DROP INDEX idx_thread_id;
ALTER TABLE contacts DROP FOREIGN KEY `1`;
ALTER TABLE contacts DROP INDEX phone_number;
ALTER TABLE contacts 
    DROP COLUMN user_id, 
    DROP COLUMN thread_id, 
    DROP COLUMN chat_status;
    