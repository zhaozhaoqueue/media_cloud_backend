**新版接口文档（分享码方案）**

**统一返回**
```json
{
  "code": 0,
  "msg": "ok",
  "data": {}
}
```

**认证**
- `Authorization: Bearer <token>`

**空间相关**
1. `GET /api/v1/spaces`
- 入参：`page`、`pageSize`
- 返回：
```json
{
  "list": [
    { "id": "sp_1", "name": "家庭相册", "memberCount": 4, "photoCount": 126, "coverUrl": "https://..." }
  ],
  "page": 1,
  "pageSize": 20,
  "total": 1
}
```

1. `POST /api/v1/spaces`
- 入参：
```json
{ "name": "旅行分享" }
```
- 返回：
```json
{ "id": "sp_2", "name": "旅行分享" }
```

1. `GET /api/v1/spaces/:spaceId`
- 入参：`spaceId`
- 返回：
```json
{ "id": "sp_1", "name": "家庭相册", "memberCount": 4, "photoCount": 126, "coverUrl": "https://..." }
```

1. `POST /api/v1/spaces/:spaceId/share-code`
- 说明：生成分享码
- 入参：
```json
{ "expiresIn": 86400 }
```
- 返回：
```json
{ "shareCode": "ABC123", "expireAt": "2026-02-05T12:00:00Z" }
```

1. `POST /api/v1/spaces/join`
- 说明：使用分享码加入空间
- 入参：
```json
{ "shareCode": "ABC123" }
```
- 返回：
```json
{ "spaceId": "sp_1", "role": "member" }
```

**图片相关**
6. `GET /api/v1/spaces/:spaceId/photos`
- 入参：`page`、`pageSize`
- 返回：
```json
{
  "list": [
    { "id": "ph_1", "name": "封面照", "url": "https://...", "ownerName": "Luka", "createdAt": "2026-02-04T10:00:00Z" }
  ],
  "page": 1,
  "pageSize": 30,
  "total": 1
}
```

7. `GET /api/v1/photos/:photoId`
- 返回：
```json
{ "id": "ph_1", "name": "封面照", "url": "https://...", "ownerName": "Luka", "createdAt": "2026-02-04T10:00:00Z", "size": 123456 }
```

8. `POST /api/v1/photos/upload-token`
- 入参：
```json
{ "spaceId": "sp_1", "files": [{ "name": "a.jpg", "size": 123456, "type": "image/jpeg" }] }
```
- 返回：
```json
{
  "uploads": [
    {
      "fileId": "file_1",
      "uploadUrl": "https://upload...",
      "method": "PUT",
      "headers": { "Content-Type": "image/jpeg" },
      "finalUrl": "https://cdn..."
    }
  ]
}
```

9. `POST /api/v1/photos`
- 入参：
```json
{ "spaceId": "sp_1", "fileId": "file_1", "name": "封面照" }
```
- 返回：
```json
{ "id": "ph_1", "url": "https://cdn..." }
```

10. `GET /api/v1/photos/:photoId/download`
- 返回：
```json
{ "downloadUrl": "https://download..." }
```

11. `DELETE /api/v1/photos/:photoId`
- 返回：
```json
{ "ok": true }
```

**成员相关（保留）**
12. `GET /api/v1/spaces/:spaceId/members`
- 返回：
```json
{ "list": [{ "userId": "u1", "name": "Luka", "role": "owner" }] }
```

13. `POST /api/v1/spaces/:spaceId/members/:userId/role`
- 入参：
```json
{ "role": "admin" }
```
- 返回：
```json
{ "ok": true }
```

14. `DELETE /api/v1/spaces/:spaceId/members/:userId`
- 返回：
```json
{ "ok": true }
```

**登录**
15. `POST /api/v1/auth/login`
- 入参：
```json
{ "code": "<wx.login code>" }
```
- 返回：
```json
{ "token": "jwt-token", "user": { "id": "u1", "name": "Luka", "avatar": "https://..." } }
```