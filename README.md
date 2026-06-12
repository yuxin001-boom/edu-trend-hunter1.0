# 🎓 教育热点捕手

> 教育行业全网热搜 & 热销日更看板  
> 每天早上 9:00 自动更新，无需人工操作

---

## 🌟 这是什么？

一个自动运行的网页，每天帮你追踪：
- 📡 微博/百度/夸克/抖音/360 五大平台的 **教育行业热搜 TOP5**
- 🛒 淘宝天猫/京东/快手 三大电商的 **教育热销商品 TOP10**
- 🏆 全平台合并去重的 **今日热度 TOP15**
- 💡 成人教育/K12/图书/电子教育 四大赛道的 **AI自动营销建议**

---

## 🚀 如何让它跑起来？（保姆级教程）

### 第一步：注册 GitHub 账号（5分钟）

1. 打开 https://github.com/signup
2. 用你的邮箱注册（公司邮箱或个人邮箱都行）
3. 验证邮箱，完成注册

### 第二步：创建你的仓库（3分钟）

1. 登录 GitHub 后，点右上角 **+** 号 → **New repository**
2. 填写信息：
   - Repository name：填 `edu-trend-hunter`
   - Description：填 `教育行业热点捕手`
   - 选择 **Public**（公开，这样才能免费用 GitHub Pages）
   - ✅ 勾选 **Add a README file**
3. 点 **Create repository**

### 第三步：上传项目文件（5分钟）

1. 在你的仓库页面，点击 **Add file** → **Upload files**
2. 把下面这些文件/文件夹全部拖进去：
   ```
   index.html          ← 网页主文件
   data.json           ← 数据文件
   scripts/            ← 脚本文件夹（含 fetch_data.py）
   .github/            ← 自动化配置文件夹
   ```
3. 在下面的 "Commit changes" 里写 `初始化项目`，点 **Commit changes**

> ⚠️ 注意：`.github` 文件夹在 Mac/Windows 上可能是隐藏的，记得在文件管理器里开启"显示隐藏文件"

### 第四步：开启 GitHub Pages（2分钟）

1. 进入仓库页面，点顶部的 **Settings**（设置）
2. 左侧菜单找到 **Pages**
3. 在 "Source" 下面选择：
   - Branch：选 **main**
   - Folder：选 **/ (root)**
4. 点 **Save**
5. 等 1-2 分钟，页面顶部会出现你的网址：
   ```
   https://你的用户名.github.io/edu-trend-hunter/
   ```

### 第五步：确认自动更新生效（1分钟）

1. 进入仓库页面，点顶部的 **Actions**
2. 你应该能看到一个叫 "📚 每日自动更新教育热点数据" 的工作流
3. 点进去，右边有个 **Run workflow** 按钮，点一下手动触发测试
4. 等 1-2 分钟，如果显示绿色 ✓，说明一切正常！

**搞定！以后每天早上 9:00 它会自动更新数据，你只需要打开网页看就行了。**

---

## 📁 项目文件说明

```
edu-trend-hunter/
├── index.html                    # 网页主文件（不需要动）
├── data.json                     # 数据文件（自动更新）
├── scripts/
│   └── fetch_data.py             # 数据采集脚本（自动运行）
├── .github/
│   └── workflows/
│       └── daily-update.yml      # 定时任务配置（每天9点）
└── README.md                     # 你正在看的这个文件
```

---

## ❓ 常见问题

**Q：GitHub Pages 网址打不开？**  
A：等 5 分钟，GitHub 需要一点时间来部署。如果还不行，去 Settings → Pages 检查是否开启成功。

**Q：Actions 报错了？**  
A：可能是数据源网站暂时不可用，等第二天会自动重试。如果持续报错，联系我看看。

**Q：我想改热搜的筛选关键词？**  
A：打开 `scripts/fetch_data.py`，找到最上面的 `EDU_KEYWORDS` 列表，加上你想要的关键词就行。

**Q：我想加更多平台？**  
A：在 `scripts/fetch_data.py` 的 `TOPHUB_NODES` 字典里加上新的平台ID。ID 可以从 tophub.today 网站上找。

---

## 📞 联系

有问题随时找我！

---

*Made with ❤️ for 教育行业运营团队*
