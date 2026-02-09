**Media Cloud API 文档（含扩展接口）**

**Base URL**
- `/api/v1`

**统一返回（除健康检查）**
```json
{
  "code": 0,
  "msg": "ok",
  "data": {}
}
```

**认证**
- 受保护接口使用 `Authorization: Bearer <token>`

**HTTP 状态码说明**
- `200`：请求成功（业务成功时通常返回统一结构，`code=0`）
- `400`：请求参数格式错误或业务参数不合法（如 UUID 格式错误、非法 role）
- `401`：未认证或 token 无效/过期
- `403`：已认证但无权限，或签名 URL 无效/过期
- `404`：资源不存在（如用户/空间/图片/账号不存在）
- `409`：资源冲突（如注册时账号已存在）
- `422`：请求体字段缺失或类型不匹配（FastAPI 参数校验失败）
- `500`：服务端内部错误

---

**健康检查（扩展）**
1. `GET /api/v1/health`
- 返回（注意：不走统一包装）：
```json
{ "status": "ok" }
```

---

**登录**
1. `POST /api/v1/auth/register`
- 入参：
```json
{
  "provider": "wechat_mini",
  "code": "<wx.login code>",
  "accessCode": "<固定字符串码>",
  "nickname": "Luka",
  "avatar": "https://..."
}
```
- 说明：注册接口；`provider` 用于区分登录来源，`accessCode` 为固定字符串码；`nickname` 与 `avatar` 为可选
- 返回：
```json
{ "token": "jwt-token", "user": { "id": "u1", "name": "Luka", "avatar": "https://..." } }
```
- 常见状态码：`200`、`400`、`403`、`409`、`422`

2. `POST /api/v1/auth/login`
- 入参：
```json
{
  "provider": "wechat_mini",
  "code": "<wx.login code>"
}
```
- 说明：登录接口，仅登录已注册账号；若账号不存在返回 404；登录阶段不校验 `accessCode`
- 返回：
```json
{ "token": "jwt-token", "user": { "id": "u1", "name": "Luka", "avatar": "https://..." } }
```
- 常见状态码：`200`、`400`、`404`、`422`

---

**空间相关**
1. `GET /api/v1/spaces`
- 入参：`page`、`pageSize`、`order`(`asc|desc`)、`name`
- 说明：`coverUrl` 默认为空；当空间第一次创建图片时会自动设置为该图片的 `thumbUrl`
- 说明：当 `coverUrl` 指向系统文件接口时，响应中会自动下发短期签名 URL（带 `expires`、`sig`）
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

2. `POST /api/v1/spaces`
- 入参：
```json
{ "name": "旅行分享" }
```
- 返回：
```json
{ "id": "sp_2", "name": "旅行分享" }
```

3. `GET /api/v1/spaces/:spaceId`
- 说明：`coverUrl` 在适用时自动下发短期签名 URL
- 返回：
```json
{ "id": "sp_1", "name": "家庭相册", "memberCount": 4, "photoCount": 126, "coverUrl": "https://..." }
```

4. `PATCH /api/v1/spaces/:spaceId`（扩展）
- 入参：
```json
{ "name": "新名称", "coverUrl": "https://..." }
```
- 返回：同空间详情

5. `DELETE /api/v1/spaces/:spaceId`（扩展）
- 返回：
```json
{ "ok": true }
```

6. `POST /api/v1/spaces/:spaceId/share-code`
- 说明：生成分享码
- 入参：
```json
{ "expiresIn": 86400 }
```
- 返回：
```json
{ "shareCode": "ABC123", "expireAt": "2026-02-05T12:00:00Z" }
```

7. `POST /api/v1/spaces/join`
- 说明：使用分享码加入空间
- 入参：
```json
{ "shareCode": "ABC123" }
```
- 返回：
```json
{ "spaceId": "sp_1", "role": "member" }
```

8. `GET /api/v1/spaces/:spaceId/share-codes`（扩展）
- 入参：`page`、`pageSize`、`activeOnly`
- 返回：
```json
{
  "list": [
    { "id": "sc_1", "shareCode": "ABC123", "expireAt": "2026-02-05T12:00:00Z", "createdAt": "2026-02-04T12:00:00Z" }
  ],
  "page": 1,
  "pageSize": 20,
  "total": 1
}
```

9. `DELETE /api/v1/spaces/:spaceId/share-codes/:shareCodeId`（扩展）
- 返回：
```json
{ "ok": true }
```

---

**图片相关**
- 权限：需为该空间成员；`PATCH/DELETE`（含批量删除）需为图片所有者或空间 `owner/admin`
1. `GET /api/v1/spaces/:spaceId/photos`
- 入参：`page`、`pageSize`、`order`(`asc|desc`)、`ownerId`
- 返回（已与代码对齐，列表字段为 `thumbUrl`）：
- 说明：`thumbUrl` 为短期签名 URL（带 `expires`、`sig`），可直接用于小程序图片组件加载
```json
{
  "list": [
    {
      "id": "ph_1",
      "name": "封面照",
      "thumbUrl": "https://api.example.com/api/v1/files/file_1/thumb?expires=1760000000&sig=xxx",
      "ownerName": "Luka",
      "createdAt": "2026-02-04T10:00:00Z"
    }
  ],
  "page": 1,
  "pageSize": 30,
  "total": 1
}
```

2. `GET /api/v1/photos/:photoId`
- 说明：`url` 与 `thumbUrl` 均为短期签名 URL（带 `expires`、`sig`）
- 返回：
```json
{
  "id": "ph_1",
  "name": "封面照",
  "url": "https://...",
  "ownerName": "Luka",
  "createdAt": "2026-02-04T10:00:00Z",
  "size": 123456,
  "width": 1920,
  "height": 1080,
  "thumbUrl": "https://..."
}
```

3. `POST /api/v1/photos/upload-token`
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

4. `POST /api/v1/photos`
- 入参：
```json
{ "spaceId": "sp_1", "fileId": "file_1", "name": "封面照" }
```
- 说明：若该空间当前没有封面，会自动将本次图片的 `thumbUrl` 设为 `space.coverUrl`
- 返回：
```json
{ "id": "ph_1", "url": "https://cdn..." }
```

5. `POST /api/v1/photos/batch`（扩展）
- 入参：
```json
{
  "spaceId": "sp_1",
  "items": [
    { "fileId": "file_1", "name": "封面照1" },
    { "fileId": "file_2", "name": "封面照2" }
  ]
}
```
- 返回：
```json
{ "ids": ["ph_1", "ph_2"] }
```

6. `GET /api/v1/photos/:photoId/download`
- 说明：`downloadUrl` 为短期签名 URL（带 `expires`、`sig`）
- 返回：
```json
{ "downloadUrl": "https://download..." }
```

7. `PATCH /api/v1/photos/:photoId`（扩展）
- 入参：
```json
{ "name": "新名称" }
```
- 返回：同图片详情

8. `DELETE /api/v1/photos/:photoId`
- 说明：若删除的是当前空间封面图，会自动切换到该空间下一张图片的 `thumbUrl`；若无剩余图片则封面置空
- 返回：
```json
{ "ok": true }
```

9. `POST /api/v1/photos/batch-delete`（扩展）
- 入参：
```json
{ "ids": ["ph_1", "ph_2"] }
```
- 说明：批量删除多张图片，封面图删除后的回填逻辑与单删一致
- 返回：
```json
{ "ok": true, "ids": ["ph_1", "ph_2"] }
```

---

**成员相关**
- 权限：查看成员需为该空间成员；新增/改角色/删除/转移 owner 仅当前 `owner` 可操作
1. `GET /api/v1/spaces/:spaceId/members`
- 返回：
```json
{ "list": [{ "userId": "u1", "name": "Luka", "role": "owner" }] }
```

2. `POST /api/v1/spaces/:spaceId/members`（扩展）
- 入参：
```json
{ "userId": "u2", "role": "member" }
```
- 返回：
```json
{ "ok": true }
```

3. `POST /api/v1/spaces/:spaceId/members/:userId/role`
- 入参：
```json
{ "role": "admin" }
```
- 返回：
```json
{ "ok": true }
```

4. `DELETE /api/v1/spaces/:spaceId/members/:userId`
- 说明：仅 `owner` 可操作；不可删除当前 owner
- 返回：
```json
{ "ok": true }
```

5. `POST /api/v1/spaces/:spaceId/owner/transfer`（扩展）
- 入参：
```json
{ "newOwnerUserId": "u2", "previousOwnerRole": "admin" }
```
- 说明：将空间 owner 迁移给已在该空间中的成员；`previousOwnerRole` 仅支持 `member/admin`
- 返回：
```json
{ "ok": true }
```

---

**文件相关（扩展）**
1. `GET /api/v1/files`
- 入参：`spaceId`(必填)、`page`、`pageSize`、`order`(`asc|desc`)、`status`
- 返回：
```json
{
  "list": [
    {
      "id": "file_1",
      "spaceId": "sp_1",
      "name": "a.jpg",
      "mimeType": "image/jpeg",
      "size": 123456,
      "status": "uploaded",
      "finalUrl": "https://cdn...",
      "createdAt": "2026-02-04T10:00:00Z"
    }
  ],
  "page": 1,
  "pageSize": 30,
  "total": 1
}
```

2. `GET /api/v1/files/:fileId`
- 返回：同文件列表项字段

3. `PUT /api/v1/uploads/:fileId?token=xxx`
- 说明：客户端按 `upload-token` 接口返回的地址直接上传文件二进制流
- 返回：
```json
{ "ok": true }
```

4. `GET /api/v1/files/:fileId/raw`
- 说明：返回原图文件流；支持两种访问方式：
- 方式 A：请求头 `Authorization: Bearer <token>`
- 方式 B：签名参数 `?expires=<unix_ts>&sig=<signature>`

5. `GET /api/v1/files/:fileId/thumb`
- 说明：优先返回缩略图文件流（jpg）；若缩略图尚未生成则回退返回原图文件流
- 说明：同样支持 `Authorization: Bearer <token>` 或签名参数访问

6. `PATCH /api/v1/files/:fileId`
- 入参：
```json
{ "name": "new-name.jpg" }
```
- 返回：同文件详情

7. `DELETE /api/v1/files/:fileId`
- 返回：
```json
{ "ok": true }
```
