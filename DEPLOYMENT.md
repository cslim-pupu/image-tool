# 🚀 部署指南 - Render 平台

本指南将帮助您将图片地址替换工具部署到 Render 平台。

## 📋 前置条件

- GitHub 账户：`cslim-pupu`
- Render 账户（免费）
- Git 已安装并配置

## 🔧 部署准备（已完成）

✅ 已修改 `app.py` 支持 Render 的 PORT 环境变量  
✅ 已添加 `gunicorn` 到 `requirements.txt`  
✅ 已创建 `.gitignore` 文件  
✅ 已创建必要的目录结构  

## 📤 第一步：推送到 GitHub

### 1. 初始化 Git 仓库（如果还没有）
```bash
cd /Users/slim/Desktop/VSCode/link-change
git init
```

### 2. 添加远程仓库
```bash
git remote add origin https://github.com/cslim-pupu/image-tool.git
```

### 3. 添加所有文件并提交
```bash
git add .
git commit -m "Initial commit: 图片地址替换工具"
```

### 4. 推送到 GitHub
```bash
git branch -M main
git push -u origin main
```

## 🌐 第二步：在 Render 上部署

### 1. 登录 Render
- 访问 [render.com](https://render.com)
- 使用 GitHub 账户登录

### 2. 创建新的 Web Service
- 点击 "New +" → "Web Service"
- 选择 "Connect a repository"
- 授权 Render 访问您的 GitHub
- 选择 `cslim-pupu/image-tool` 仓库

### 3. 配置部署设置
```
Name: image-tool
Environment: Python 3
Build Command: pip install -r requirements.txt
Start Command: python app.py
```

### 4. 高级设置（可选）
- **实例类型**: Free（免费）
- **自动部署**: 启用（推荐）
- **环境变量**:
  ```
  FLASK_ENV=production
  ```

### 5. 部署
- 点击 "Create Web Service"
- 等待构建和部署完成（通常 2-5 分钟）

## 🎯 第三步：验证部署

### 部署成功后，您将获得：
- 🌐 **访问地址**: `https://image-tool.onrender.com`
- 📊 **仪表板**: 监控应用状态
- 📝 **日志**: 查看应用运行日志

### 测试功能：
1. 访问主页
2. 测试图片抓取工具
3. 测试链接替换功能
4. 验证文件上传下载

## ⚙️ 环境变量配置

在 Render 仪表板中设置以下环境变量：

```
FLASK_ENV=production
PORT=10000  # Render 会自动设置
```

## 🔄 自动部署

配置完成后，每次推送到 `main` 分支都会自动触发部署：

```bash
# 本地修改后
git add .
git commit -m "更新功能"
git push origin main
# Render 会自动重新部署
```

## 📊 监控和维护

### Render 免费套餐限制：
- ✅ **750 小时/月**（足够个人使用）
- ✅ **自动休眠**（15分钟无访问后）
- ✅ **冷启动**（首次访问需要几秒钟）
- ✅ **512MB RAM**
- ✅ **自定义域名**（可选）

### 查看日志：
- Render 仪表板 → 您的服务 → "Logs" 标签

### 重启服务：
- Render 仪表板 → 您的服务 → "Manual Deploy"

## 🚨 故障排除

### 常见问题：

1. **构建失败**
   - 检查 `requirements.txt` 格式
   - 查看构建日志中的错误信息

2. **应用无法启动**
   - 确认 `app.py` 中的端口配置正确
   - 检查环境变量设置

3. **文件上传问题**
   - Render 使用临时文件系统
   - 重启后上传的文件会丢失（这是正常的）

4. **冷启动慢**
   - 免费套餐的正常现象
   - 可以考虑升级到付费套餐

## 🎉 完成！

您的图片地址替换工具现在已经成功部署到 Render！

- 🌐 **在线访问**: `https://image-tool.onrender.com`
- 📱 **移动友好**: 响应式设计
- 🔄 **自动更新**: 推送代码即自动部署
- 💰 **完全免费**: 使用 Render 免费套餐

---

**需要帮助？**
- [Render 官方文档](https://render.com/docs)
- [Flask 部署指南](https://flask.palletsprojects.com/en/2.3.x/deploying/)