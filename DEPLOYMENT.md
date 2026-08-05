# 东南亚观察 · 免费域名部署指南

目标：把网站部署到 Vercel，获得免费子域名（如 `your-name.vercel.app`），自带 HTTPS + 全球 CDN。

---

## 路线 A：Vercel CLI 直接部署（推荐，最快拿域名）

> 本机环境已就绪：Node v22.22.2 / npm 10.9.7，项目已 git 初始化并提交。

### 步骤 1：安装 Vercel CLI（一次性）

在你电脑的终端执行：

```bash
npm install -g vercel
```

> 不想全局安装也可以用 `npx vercel`，每次自动拉取。

### 步骤 2：登录（需你在浏览器授权，邓肯没法代做）

```bash
cd /Users/xiechang/WorkBuddy/东南亚研究网站开发
vercel login
```

- 选择登录方式（GitHub / GitLab / 邮箱任选其一）
- 浏览器会自动打开授权页，确认即可
- 终端显示 `Congratulations! You are now logged in.` 表示成功

### 步骤 3：部署到生产

```bash
vercel --prod
```

首次会问几个问题，**一路回车即可**：

| 问题 | 回答 |
|------|------|
| Set up and deploy? | Y（回车） |
| Which scope? | 选你的账号（回车） |
| Link to existing project? | N（回车） |
| Project name | 回车用默认，或输入自定义如 `southeast-asia-watch` |
| In which directory... | `./`（回车） |
| Want to modify settings? | N（回车） |

完成后终端会输出一个 `https://xxx.vercel.app` 地址——这就是你的免费域名，立即可访问。

### 步骤 4（可选）：换一个更好记的子域名前缀

1. 登录 [vercel.com](https://vercel.com) → 进入刚创建的项目
2. **Settings → Domains**
3. 在输入框输入你想要的前缀，如 `sea-watch`，得到 `sea-watch.vercel.app`
4. 若未被占用，点 Add 即可生效

---

## 路线 B：GitHub + Vercel 自动部署（长期方案）

> 适合配合你已有的"工作日 8:00 自动更新文章"——每次推送新文章，Vercel 自动重新部署上线。

### 步骤 1：在 GitHub 建仓库

- 登录 [github.com](https://github.com) → New repository
- 名称如 `southeast-asia-watch`，Public，**不要**勾选 README/.gitignore（本地已有）
- 创建后会给你一段推送命令

### 步骤 2：把本地代码推上去

```bash
cd /Users/xiechang/WorkBuddy/东南亚研究网站开发
git remote add origin https://github.com/你的用户名/southeast-asia-watch.git
git branch -M main
git push -u origin main
```

> 若用 HTTPS 首次推送要输 GitHub 账号密码（建议配 Personal Access Token 当密码）。

### 步骤 3：在 Vercel 导入仓库

1. 登录 [vercel.com](https://vercel.com) → **Add New → Project**
2. 选你的 GitHub 账号，找到 `southeast-asia-watch` 仓库 → **Import**
3. Framework Preset 选 **Other**（纯静态无构建）
4. 直接点 **Deploy**，几十秒后拿到 `xxx.vercel.app` 域名

之后每次 `git push`，Vercel 自动重新部署。

---

## 路线 C：想要更专业的真域名（非免费，但极便宜）

1. 在 [Cloudflare Registrar](https://cloudflare.com) 或阿里云买 `.xyz`/`.top`，**首年约 5-10 元**
2. 在 Vercel 项目 **Settings → Domains** 添加你买的域名
3. 按提示在域名 DNS 加一条 CNAME 指向 `cname.vercel-dns.com`
4. Vercel 自动签发 HTTPS 证书

---

## 已配置好的部署文件

- `vercel.json` —— 声明纯静态站点、干净 URL、安全响应头
- `.gitignore` —— 忽略 `.workbuddy/`（工作区数据）、系统文件、依赖
- git 仓库已初始化，17 个文件已提交到 `main` 分支

## 与 CloudStudio 的关系

部署到 Vercel 后，你可以：
- 把 Vercel 域名作为正式门面（`your-name.vercel.app`，好记、自带 CDN）
- 保留 CloudStudio 沙箱作为预览/草稿环境
- 或在 Vercel 设置里把 CloudStudio 地址设为旧域名重定向

## 推荐路径

**立刻要域名** → 走路线 A，3 条命令，5 分钟拿到 `xxx.vercel.app`。
**想长期自动更新即上线** → 走路线 B，配好后工作日 8:00 自动化更新文章 + push → Vercel 自动部署，全程无人值守。
