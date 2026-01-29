# Solutionesia AI WhatsApp API Documentation

## Base URL

`/api`

## 1. Authentication (`/auth`)

### Login

Authenticate a user and return a JWT token.

- **URL**: `/auth/login`
- **Method**: `POST`
- **Request Body**: `UserLogin`
    ```json
    {
        "email": "user@example.com",
        "password": "password123"
    }
    ```
- **Response**: `AuthResponse`
    - **Cookie**: `access_token` (HttpOnly)
    ```json
    {
        "user": {
            "id": "user_123",
            "email": "user@example.com",
            "name": "User Name"
        }
    }
    ```

### Register

Register a new user.

- **URL**: `/auth/register`
- **Method**: `POST`
- **Request Body**: `UserRegister`
    ```json
    {
        "email": "newuser@example.com",
        "password": "securepassword",
        "name": "New User"
    }
    ```
- **Response**: `AuthResponse` (Same as Login)

### Update Username

Update the authenticated user's name.

- **URL**: `/auth/username`
- **Method**: `PUT`\
- **Cookie**: `access_token` (HttpOnly)
- **Request Body**: `UserNameUpdate`
    ```json
    {
        "name": "Updated Name"
    }
    ```
- **Response**:
    ```json
    {
        "message": "User name updated successfully"
    }
    ```

---

## 2. Contacts (`/contacts`)

### Get Contacts

Get a paginated list of contacts for the authenticated user.

- **URL**: `/contacts?page=1&limit=50`
- **Method**: `GET`
- **Cookie**: `access_token` (HttpOnly)
- **Query Params**:
    - `page` (int, default=1)
    - `limit` (int, default=50)
- **Response**: `ContactsListResponse`
    ```json
    {
        "items": [
            {
                "id": "contact_1",
                "name": "Contact Name",
                "phoneNumber": "1234567890",
                "labels": ["label1"],
                "organization_id": "org_1"
            }
        ],
        "total": 100,
        "page": 1,
        "limit": 50,
        "pages": 2
    }
    ```

### Create Contact

Create a new contact.

- **URL**: `/contacts`
- **Method**: `POST`
- **Cookie**: `access_token` (HttpOnly)
- **Request Body**: `ContactCreate`
    ```json
    {
        "name": "New Contact",
        "phoneNumber": "1234567890",
        "labels": ["lead"]
    }
    ```
- **Response**: `ContactResponse`

## 3. Labels (`/organizations/{org_id}/labels`)

### Get Labels

Get labels for an organization.

- **URL**: `/organizations/{org_id}/labels?page=1&limit=50`
- **Method**: `GET`
- **Cookie**: `access_token` (HttpOnly)
- **Query Params**:
    - `page` (int, default=1)
    - `limit` (int, default=50)
- **Response**: `LabelsListResponse`
    ```json
    {
        "labels": [
            {
                "id": "label_123",
                "name": "Important",
                "color": "#FF0000",
                "organization_id": "org_1"
            }
        ],
        "total": 10,
        "page": 1,
        "limit": 50
    }
    ```

### Create Label

Create a new label for an organization.

- **URL**: `/organizations/{org_id}/labels`
- **Method**: `POST`
- **Cookie**: `access_token` (HttpOnly)
- **Request Body**: `LabelCreate`
    ```json
    {
        "name": "New Label",
        "color": "#00FF00"
    }
    ```
- **Response**: `LabelResponse`

### Update Label

Update a label.

- **URL**: `/organizations/{org_id}/labels/{label_id}`
- **Method**: `PUT`
- **Cookie**: `access_token` (HttpOnly)
- **Request Body**: `LabelCreate`
    ```json
    {
        "name": "Updated Label",
        "color": "#0000FF"
    }
    ```
- **Response**: `LabelResponse`

### Delete Label

Delete a label.

- **URL**: `/organizations/{org_id}/labels/{label_id}`
- **Method**: `DELETE`
- **Cookie**: `access_token` (HttpOnly)
- **Response**:
    ```json
    {
        "message": "Label deleted successfully"
    }
    ```

### Assign Label to Contact

Assign a label to a contact.

- **URL**: `/organizations/{org_id}/labels/contacts/{contact_id}/assign/{label_id}`
- **Method**: `POST`
- **Cookie**: `access_token` (HttpOnly)
- **Response**:
    ```json
    {
        "message": "Label assigned successfully"
    }
    ```

### Remove Label from Contact

Remove a label from a contact.

- **URL**: `/organizations/{org_id}/labels/contacts/{contact_id}/remove/{label_id}`
- **Method**: `DELETE`
- **Cookie**: `access_token` (HttpOnly)
- **Response**:
    ```json
    {
        "message": "Label removed from contact successfully"
    }
    ```

---

## 4. Organizations (`/organizations`)

### Register Organization

Register a new organization. Requires App Admin privileges (or initial setup).

- **URL**: `/organizations/register`
- **Method**: `POST`
- **Cookie**: `access_token` (HttpOnly) (App Admin)
- **Request Body**: `OrganizationCreate`
    ```json
    {
        "name": "Acme Corp",
        "email": "contact@acmecorp.com",
        "status": "active",
        "phone_id": "pid_550e8400",
        "agent_id": "agent_12345",
        "password": "securePassword123!",
        "phone_number": "+15559876543"
    }
    ```
- **Response**:
    ```json
    {
        "org": {
            "id": "org_667788",
            "name": "Innovate Tech",
            "email": "admin@innovate.com",
            "status": "active",
            "created_at": "2026-01-29T10:00:00Z",
            "updated_at": "2026-01-29T10:00:00Z"
        },
        "user": {
            "id": "user_112233",
            "email": "founder@innovate.com",
            "name": "Jane Doe",
            "profile_picture": "https://api.innovate.com/avatars/jane.png"
        },
        "org_user": {
            "id": "ou_445566",
            "user": {
                "id": "user_112233",
                "name": "Jane Doe",
                "profile_picture": "https://api.innovate.com/avatars/jane.png",
                "email": "founder@innovate.com"
            },
            "organization_id": "org_667788",
            "phone_number": "+1555000111",
            "organization_role": {
                "id": "role_owner",
                "name": "Owner"
            },
            "created_at": "2026-01-29T10:00:01Z",
            "updated_at": "2026-01-29T10:00:01Z"
        }
    }
    ```

### Update Organization Status

Update status of an organization (App Admin only).

- **URL**: `/organizations/{org_id}/status`
- **Method**: `PUT`
- **Cookie**: `access_token` (HttpOnly)
- **Request Body**: `OrganizationUpdateStatus`
    ```json
    {
        "status": "active"
    }
    ```
- **Response**: `OrganizationResponse`

### Get Organization Users

Get all users in an organization.

- **URL**: `/organizations/{org_id}/users`
- **Method**: `GET`
- **Cookie**: `access_token` (HttpOnly)
- **Response**: List of `OrganizationUserResponse`
    ```json
    [
        {
            "id": "org_user_98765",
            "user": {
                "id": "user_12345",
                "name": "Alex Rivet",
                "profile_picture": "https://cdn.example.com/profiles/alex.jpg",
                "email": "alex@company.com"
            },
            "organization_id": "org_55443",
            "phone_number": "+1234567890",
            "organization_role": {
                "id": "role_admin",
                "name": "Administrator"
            },
            "created_at": "2024-05-20T10:30:00Z",
            "updated_at": "2024-05-20T14:15:00Z"
        },
        {
            "id": "org_user_98766",
            "user": {
                "id": "user_67890",
                "name": "Sam Smith",
                "profile_picture": null,
                "email": "sam@company.com"
            },
            "organization_id": "org_55443",
            "phone_number": "+1987654321",
            "organization_role": {
                "id": "role_editor",
                "name": "Editor"
            },
            "created_at": "2024-05-21T09:00:00Z",
            "updated_at": "2024-05-21T09:00:00Z"
        }
    ]
    ```

### Invite User

Invite a user to the organization (Org Admin or App Admin).

- **URL**: `/organizations/{org_id}/users/invite`
- **Method**: `POST`
- **Cookie**: `access_token` (HttpOnly)
- **Request Body**: `OrganizationUserInvite`
    ```json
    {
        "email": "invitee@example.com"
    }
    ```
- **Response**: `OrganizationUserResponse`

### Update User Role

Update a user's role in the organization (Org Admin only).

- **URL**: `/organizations/{org_id}/users/{target_user_id}/role`
- **Method**: `PUT`
- **Cookie**: `access_token` (HttpOnly)
- **Request Body**: `OrganizationUserUpdate`
    ```json
    {
        "role_id": "role_id_here"
    }
    ```
- **Response**: `OrganizationUserResponse`

### Update User Phone Number

Update a user's phone number within the organization.

- **URL**: `/organizations/{org_id}/users/{target_user_id}/phone-number`
- **Method**: `PUT`
- **Cookie**: `access_token` (HttpOnly)
- **Request Body**: `OrganizationUpdateUserPhoneNumber`
    ```json
    {
        "phone_number": "+1234567890"
    }
    ```
- **Response**: `OrganizationUserResponse`

### Remove User

Remove a user from the organization (Org Admin only).

- **URL**: `/organizations/{org_id}/users/{target_user_id}`
- **Method**: `DELETE`
- **Cookie**: `access_token` (HttpOnly)
- **Response**:
    ```json
    {
        "message": "User removed from organization"
    }
    ```

### Get Organization Contacts

Get contacts in an organization.

- **URL**: `/organizations/{org_id}/contacts?page=1&limit=10`
- **Method**: `GET`
- **Cookie**: `access_token` (HttpOnly)
- **Response**: `ContactsListResponse`
    ```json
    {
        "contacts": [
            {
                "id": "contact_1",
                "name": "John Doe",
                "phoneNumber": "+123456",
                "email": "john@example.com",
                "profilePicture": "url..."
            }
        ],
        "total": 50,
        "page": 1,
        "limit": 10
    }
    ```

### Get Contact Conversations

Get conversations for a specific contact.

- **URL**: `/organizations/{org_id}/contacts/{contact_id}/conversations?page=1&limit=10&mode=ai|human&status=active|inactive&start_date=2024-01-01&end_date=2024-01-31`
- **Method**: `GET`
- **Cookie**: `access_token` (HttpOnly)
- **Response**: `ConversationsListResponse`
    ```json
    {
        "conversations": [
            {
                "id": "conv_1",
                "status": "active",
                "mode": "ai",
                "created_at": "..."
            }
        ],
        "total": 5,
        "page": 1,
        "limit": 10
    }
    ```

### Get Organization Human Conversations

Get all conversations in 'human' mode for an organization.

- **URL**: `/organizations/{org_id}/conversations/human?page=1&limit=10`
- **Method**: `GET`
- **Cookie**: `access_token` (HttpOnly)
- **Response**: `ConversationsListResponse`
    ```json
    {
        "conversations": [
            {
                "id": "conv_2",
                "name": "John Doe",
                "phoneNumber": "621234567890",
                "metadata": {},
                "status": "active",
                "mode": "human",
                "lastMessage": "Hello!",
                "timestamp": "2026-01-26T14:16:21+07:00"
            }
        ],
        "total": 1,
        "page": 1,
        "limit": 10
    }
    ```

### Search Organization Conversations

Get conversations for an organization with optional filters.

- **URL**: `/organizations/{org_id}/conversations`
- **Method**: `POST`
- **Cookie**: `access_token` (HttpOnly)
- **Request Body**: `ConversationFilter`
    ```json
    {
        "mode": "human",
        "status": "active",
        "query": "John",
        "start_date": "2024-01-01",
        "end_date": "2024-01-31",
        "page": 1,
        "limit": 10
    }
    ```
- **Response**: `ConversationsListResponse`
    ```json
    {
        "conversations": [
            {
                "id": "conv_2",
                "status": "active",
                "mode": "human",
                "name": "John Doe",
                "phoneNumber": "+123456",
                "lastMessage": "Help me!",
                "timestamp": "..."
            }
        ],
        "total": 1,
        "page": 1,
        "limit": 10
    }
    ```

### List Organizations

List all organizations.

- **URL**: `/organizations`
- **Method**: `GET`
- **Cookie**: `access_token` (HttpOnly) (App Admin only)
- **Query Params**:
    - `page` (int, default=1)
    - `limit` (int, default=10)
    - `query` (str, optional): Search by organization name or email.
    - `status` (str, optional): Filter by status (active, inactive).
- **Response**: `OrganizationsListResponse`

    ```json
    {
        "organizations": [
            {
                "id": "org_1",
                "name": "Org Name",
                "email": "org@example.com",
                "status": "active"
            }
        ],
        "total": 10,
        "page": 1,
        "limit": 10
    }
    ```

### Organization Permissions (App Admin)

### Create Permission

Create a new global organization permission.

- **URL**: `/organizations/permissions`
- **Method**: `POST`
- **Cookie**: `access_token` (HttpOnly) (App Admin only)
- **Request Body**: `OrganizationPermissionCreate`
    ```json
    {
        "name": "can_manage_billing",
        "description": "Allows managing billing information"
    }
    ```
- **Response**: `OrganizationPermissionResponse`
    ```json
    {
        "id": "perm_1",
        "name": "can_manage_billing",
        "description": "Allows managing billing information"
    }
    ```

### List Permissions

List all global organization permissions.

- **URL**: `/organizations/permissions`
- **Method**: `GET`
- **Cookie**: `access_token` (HttpOnly) (App Admin only)
- **Response**: List of `OrganizationPermissionResponse`

```json
[
    {
        "id": "perm_1",
        "name": "can_manage_billing",
        "description": "Allows managing billing information"
    }
]
```

### Delete Permission

Delete a global organization permission.

- **URL**: `/organizations/permissions/{perm_id}`
- **Method**: `DELETE`
- **Cookie**: `access_token` (HttpOnly) (App Admin only)
- **Response**:
    ```json
    {
        "message": "Permission deleted"
    }
    ```

### Organization Roles (Org Admin)

### Get Organization Roles

Get all roles in an organization.

- **URL**: `/organizations/{org_id}/roles`
- **Method**: `GET`
- **Cookie**: `access_token` (HttpOnly) (Org Admin)
- **Response**: List of `OrganizationRoleResponse`
    ```json
    [
        {
            "id": "role_1",
            "name": "admin",
            "permissions": ["perm_1", "perm_2"]
        }
    ]
    ```

### Create Organization Role

Create a new role for organization.

- **URL**: `/organizations/{org_id}/roles`
- **Method**: `POST`
- **Cookie**: `access_token` (HttpOnly) (Org Admin)
- **Request Body**: `OrganizationRoleCreate`
    ```json
    {
        "name": "Manager"
    }
    ```
- **Response**: `OrganizationRoleResponse`

### Update Organization Role

Update role name.

- **URL**: `/organizations/{org_id}/roles/{role_id}`
- **Method**: `PUT`
- **Cookie**: `access_token` (HttpOnly) (Org Admin)
- **Request Body**: `OrganizationRoleUpdate`
    ```json
    {
        "name": "Senior Manager"
    }
    ```
- **Response**: `OrganizationRoleUpdate`

### Delete Organization Role

Delete a role.

- **URL**: `/organizations/{org_id}/roles/{role_id}`
- **Method**: `DELETE`
- **Cookie**: `access_token` (HttpOnly) (Org Admin)
- **Response**:
    ```json
    {
        "message": "Role deleted"
    }
    ```

### Assign Permission to Role

Assign permission to a role.

- **URL**: `/organizations/{org_id}/roles/{role_id}/permissions`
- **Method**: `POST`
- **Cookie**: `access_token` (HttpOnly) (Org Admin)
- **Request Body**: `AssignPermissionRequest`
    ```json
    {
        "permission_id": "perm_1"
    }
    ```
- **Response**:
    ```json
    {
        "message": "Permission assigned"
    }
    ```

### Remove Permission from Role

Remove permission from a role.

- **URL**: `/organizations/{org_id}/roles/{role_id}/permissions/{perm_id}`
- **Method**: `DELETE`
- **Cookie**: `access_token` (HttpOnly) (Org Admin)
- **Response**:
    ```json
    {
        "message": "Permission removed"
    }
    ```

---

### Check Organization Permission

Check if the current user has a specific permission in the organization.

- **URL**: `/organizations/{org_id}/permissions/check`
- **Method**: `POST`
- **Cookie**: `access_token` (HttpOnly) (Organization Member)
- **Request Body**: `CheckPermissionRequest`
    ```json
    {
        "permission": "can_manage_conversations"
    }
    ```
- **Response**:
    ```json
    {
        "has_permission": true
    }
    ```

---

### Get Organization User Permissions

Get all permissions for the current user in the organization.

- **URL**: `/organizations/{org_id}/permissions/me`
- **Method**: `GET`
- **Cookie**: `access_token` (HttpOnly) (Organization Member)
- **Response**: List of strings
    ```json
    ["can_manage_conversations", "can_view_reports"]
    ```

---

## 4. Conversations (`/conversations`)

### Get Conversation Details

Get details of a specific conversation.

- **URL**: `/conversations/{conversation_id}`
- **Method**: `GET`
- **Cookie**: `access_token` (HttpOnly)
- **Response**: `ConversationDetailResponse`
    ```json
    {
        "id": "conv_123",
        "status": "active | inactive",
        "mode": "ai | human",
        "contact": {
            "name": "John Doe",
            "phoneNumber": "+123456"
        },
        "messages": [
            {
                "content": "Hi",
                "contentType": "text",
                "role": "user | assistant",
                "status": null,
                "timestamp": "2023-01-01T12:00:00"
            }
        ]
    }
    ```

### Update Conversation Mode

Update the mode of a conversation (e.g., switch between 'human' and 'ai').
Allowed for: App Admin or Organization Member.

- **URL**: `/conversations/{conversation_id}/mode`
- **Method**: `PUT`
- **Request Body**: `ConversationModeUpdate`
    ```json
    {
        "mode": "human"
    }
    ```
- **Response**:
    ```json
    {
        "status": "success",
        "message": "Conversation mode updated to 'human'",
        "conversation_id": "...",
        "mode": "human"
    }
    ```

### Update Conversation Status

Update the status of a conversation (e.g., 'active' or 'inactive').
Allowed for: App Admin or Organization Member.

- **URL**: `/conversations/{conversation_id}/status`
- **Method**: `PUT`
- **Request Body**: `ConversationStatusUpdate`
    ```json
    {
        "status": "inactive"
    }
    ```
- **Response**:
    ```json
    {
        "status": "success",
        "message": "Conversation status updated to 'inactive'",
        "conversation_id": "...",
        "status": "inactive"
    }
    ```

### Open Conversation (Takeover)

Mark a conversation as opened (set `is_opened` to true).
Allowed for: Organization User with 'takeover' permission.

- **URL**: `/conversations/{conversation_id}/open`
- **Method**: `POST`
- **Cookie**: `access_token` (HttpOnly)
- **Response**:
    ```json
    {
        "message": "Conversation opened successfully",
        "conversation_id": "..."
    }
    ```

### WebSocket: Conversation Updates

Listen for real-time updates for a specific conversation.

- **URL**: `/conversations/ws`
- **Protocol**: `ws://` or `wss://`
- **Query Parameters**:
    - `conversation_id`: The ID of the conversation to listen to.
    - `token`: Valid JWT access token.
- **Example**:
  `ws://api.example.com/api/conversations/ws?conversation_id=123&token=eyJ...`

- **Events**:
    - `conversation_created`: Broadcast when a new conversation starts.
        ```json
        {
          "type": "conversation_created",
          "data": { ...conversation_object... }
        }
        ```

---

## 5. Users (`/users`)

### List Users

List all users with optional filters.
Allowed for: App Admin only.

- **URL**: `/users`
- **Method**: `GET`
- **Cookie**: `access_token` (HttpOnly)
- **Query Params**:
    - `page` (int, default=1)
    - `limit` (int, default=10)
    - `role` (str, optional): Filter by global role ('admin' or 'user').
    - `search` (str, optional): Search by name or email.
- **Response**: `UsersListResponse`
    ```json
    {
        "users": [
            {
                "id": "user_123",
                "name": "User Name",
                "email": "user@example.com",
                "role": "user",
                "profile_picture": "url..."
            }
        ],
        "total": 1,
        "page": 1,
        "limit": 10
    }
    ```

### Get Current User Profile

Get the profile of the current authenticated user.

- **URL**: `/users/me`
- **Method**: `GET`
- **Cookie**: `access_token` (HttpOnly)
- **Response**: `UserProfileResponse`
    ```json
    {
        "id": "user_123",
        "name": "User Name",
        "email": "user@example.com",
        "role": "user",
        "profile_picture": "url..."
    }
    ```

### Get User Organizations

Get organizations a specific user belongs to, including their role and phone number in that organization.

- **URL**: `/users/{user_id}/organizations`
- **Method**: `GET`
- **Cookie**: `access_token` (HttpOnly)
- **Response**: List of `UserOrganizationResponse`
    ```json
    [
        {
            "id": "org_1",
            "name": "Org A",
            "email": "org@a.com",
            "status": "active",
            "organization_user": {
                "phone_number": "+123456",
                "role": {
                    "id": "role_1",
                    "name": "admin"
                }
            }
        }
    ]
    ```

### Search Users

List and search users with filters (App Admin only).

- **URL**: `/users/search`
- **Method**: `POST`
- **Cookie**: `access_token` (HttpOnly)
- **Request Body**: `UserListFilter`
    ```json
    {
        "role": "user",
        "search": "john",
        "page": 1,
        "limit": 10
    }
    ```
- **Response**: `UsersListResponse`
    ```json
    {
        "users": [
            {
                "id": "user_123",
                "name": "John Doe",
                "email": "john@example.com",
                "role": "user",
                "profile_picture": "..."
            }
        ],
        "total": 1,
        "page": 1,
        "limit": 10
    }
    ```

---

## 6. Messages (`/api/messages`)

### Create Message

Create a new message.
Allowed for: App Admin or Organization Member.

- **URL**: `/api/messages`
- **Method**: `POST`
- **Cookie**: `access_token` (HttpOnly)
- **Request Body**: `MessageCreate`
    ```json
    {
        "conversation_id": "conv_123",
        "content": "Hello",
        "role": "admin",
        "content_type": "text"
    }
    ```
- **Response**: `MessageResponse`

```json
{
    "content": "Hello",
    "content_type": "text",
    "timestamp": "2023-01-01T12:00:00",
    "role": "admin"
}
```
