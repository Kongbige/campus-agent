# 城院小助手 · 校园服务智能体

> 2026 年沈阳城市学院计算机应用大赛 · 赛道 01「大模型与智能体应用开发」· 校园服务类智能体 参赛作品

「城院小助手」是一个以**大语言模型为推理核心**、采用 **Agent（ReAct：规划 → 工具调用 → 观察 → 回答）架构**的校园服务智能体。同学用一句自然语言即可完成：查课表/下节课/空教室、校园导航（基于学校官方鸟瞰图标注）、活动聚合与推荐、宿舍报修、办事指南问答、提醒待办、食堂与交通查询。界面会实时展示智能体的「思考与工具调用」过程，便于评审直观看到智能体架构。

![界面截图](docs/screenshot.png)

## ✨ 功能一览

| 场景 | 工具（Function） | 说明 |
|---|---|---|
| 智慧课表 | `query_schedule` `next_class` `free_classrooms` | 按天/周查课、下一节课、空教室（找自习室） |
| 校园导航 / 校园片区 | `locate_building` `plan_route` | 42 个真实地点（9 栋核心楼宇 + 食堂、图书馆水晶宫、宿舍社区、体育馆、校门等）；方向、直线距离、步行估算、沿途地标；**在官方鸟瞰图上高亮标注** |
| 活动信息聚合 | `search_events` `recommend_events` | 按标签/关键词/校区/时间筛选，按兴趣推荐 |
| 宿舍服务 | `create_repair_ticket` `query_repair_tickets` | 报修工单写入 SQLite，缺信息时多轮追问 |
| 校园知识库 | `search_knowledge` | BM25 检索 Markdown 办事指南（图书馆、选课、校园卡、宿舍、请假…） |
| 提醒待办 | `add_reminder` `list_reminders` | 相对时间自动换算为具体日期 |
| 生活服务（加分项） | `canteen_info` `transport_info` | 食堂/餐厅位置（绿岛俱乐部、西山会所等）与营业时间；到校公交/地铁 |

- **两种运行模式**：配置大模型密钥 → 🤖「大模型模式」；未配置 → 🧩「离线演示模式」（内置规则规划器，**调用同一套工具**，零密钥即可完整演示）。界面右上角徽章实时显示当前模式；大模型调用失败时自动降级。
- **多轮对话记忆**：按会话保存历史，支持“那周四呢？”等省略追问、报修槽位补全、“我在机电楼”位置记忆。
- **可解释**：每条回答下方可展开「🧠 思考与工具调用」，查看规划、调用参数与工具返回 JSON。
- **地图联动**：导航类回答自动附上学校官方鸟瞰图，并按图例位置高亮起点/终点/途经地标。
- **移动端友好**：手机浏览器可直接使用（侧边栏折叠为 ☰）。

## 🚀 一键运行

需要 Python 3.10+（推荐 3.11/3.12）。

```bash
pip install -r requirements.txt
python run.py
```

浏览器打开 <http://127.0.0.1:8000> 即可（启动时会自动打开浏览器）。

**国内网络建议使用清华镜像：**

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### Windows 用户

1. 安装 Python（[python.org](https://www.python.org/downloads/) 或应用商店），安装时勾选 **Add Python to PATH**。
2. 解压 `campus-agent.zip`，在文件夹地址栏输入 `cmd` 回车打开命令行。
3. 依次执行：
   ```bat
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
   python run.py
   ```
4. 如 8000 端口被占用：在 `.env` 中设置 `PORT=8080`。

## 🤖 接入大模型（可选）

复制 `.env.example` 为 `.env`（Windows：`copy .env.example .env`），填写三项即可，任意 **OpenAI 兼容接口**均可：

| 平台 | LLM_BASE_URL | LLM_MODEL 示例 |
|---|---|---|
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` |
| 通义千问（DashScope 兼容模式） | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-plus` / `qwen-turbo` |
| 智谱 GLM | `https://open.bigmodel.cn/api/paas/v4` | `glm-4-flash` / `glm-4-plus` |
| Kimi（月之暗面） | `https://api.moonshot.cn/v1` | `moonshot-v1-8k` |
| 本地 Ollama | `http://localhost:11434/v1` | `qwen2.5:7b`（需支持工具调用） |

```ini
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
LLM_API_KEY=sk-xxxx
```

重启 `python run.py`，徽章变为「🤖 大模型模式」。所选模型需支持 Function Calling（以上列出的模型均支持）。**不要把含密钥的 `.env` 提交或打包上交。**

其他配置：`FORCE_MOCK=1` 强制离线模式；`DEMO_TODAY=2026-11-02` 固定演示日期（录制视频/答辩时保证数据稳定）。

## 🧪 测试与效果评估

```bash
python -m pytest -q                  # 单元/接口测试（22 项）
python eval/evaluate.py              # 效果评估：28 条用例（离线模式）
python eval/evaluate.py --holdout    # 泛化测试集：12 条未针对调参的新问法
python eval/evaluate.py --llm        # 配置密钥后，评估大模型模式
```

## 📁 目录结构

```
campus-agent/
├── run.py                  # 一键启动
├── app/
│   ├── main.py             # FastAPI 接口
│   ├── agent.py            # 智能体核心：LLM ReAct 循环 + 离线降级
│   ├── mock_planner.py     # 离线规则规划器（意图识别/多意图拆解/槽位追问）
│   ├── responder.py        # 离线模式回答组织
│   ├── memory.py           # 多轮会话记忆
│   ├── llm_client.py       # OpenAI 兼容客户端
│   └── tools/              # 14 个工具 + 注册表（JSON Schema）
├── prompts/system_prompt.md  # 系统提示词
├── data/                   # campus_map.json（导航地点）、map/（官方鸟瞰图与调研数据）、课表等示例数据、knowledge/ 知识库
├── scripts/                # build_campus_map.py（由调研数据生成导航数据）、take_screenshots.py
├── static/                 # 前端单页（HTML/CSS/JS）
├── eval/                   # 效果评估脚本与用例
├── tests/                  # pytest 测试
└── docs/                   # 设计文档、演示视频脚本、答辩提纲、团队分工、截图
```

## ⚠️ 关于数据（重要）

**真实数据（来自学校官方鸟瞰图、学校官网、OpenStreetMap，详见 `data/map/调研摘要.md`）**
- 沈阳城市学院为**单一校园**（沈阳市苏家屯区梧桐大街2号）；“北校区/西校区/南校区”是校园内片区。
- 9 栋核心楼宇：建工楼、医工楼、机电楼、经管楼、西山会所、绿岛俱乐部、传媒楼、南楼、医科楼；其中 **西山会所、绿岛俱乐部为食堂**（也可作为活动场地）。
- 关键地标来自官方图例（96 项）：校园大门（东侧）、图书馆水晶宫、苹果书屋、体育馆、绿岛湖、东湖、各宿舍社区（园中园、梧桐园、金菊园、白桦园、金栎园、紫薇园、玫瑰园、百荷园）等。
- 到校公交（389/395 路至“沈阳城市学院(绿岛)”站，地铁 2 号线奥体中心站换乘）。

**估算 / 待核实**
- 建工楼、传媒楼、经管楼、机电楼、南楼坐标取自 OSM（较可靠）；医工楼、医科楼、西山会所、绿岛俱乐部及其他地标坐标由地图像素换算，误差约 40–100 米，标注“待核实”。
- 步行时间 = 直线距离 ÷ 80 米/分钟，**实际路线更长**；片区归属部分为依地图推断（`zone_source` 字段）。
- 公寓号 → 宿舍社区的对应依据地图推断（官网与地图对金菊园楼号的说法不一致）。

**示例数据（虚构，仅供演示，界面与回答中均有标注）**：课表、教室编号与占用、活动、食堂营业时间、知识库中的具体规则（借阅、选课、校园卡、请假等）。

**团队待办**：实地核实“待核实”坐标与楼间真实步行路线（编辑 `scripts/build_campus_map.py` 或直接编辑 `data/campus_map.json`），并替换 `schedule.json`、`classrooms.json`、`events.json`、`canteens.json` 与 `data/knowledge/*.md` 中的示例内容。修改后重启即可生效，无需改代码。

## 📄 文档

- [设计文档](docs/设计文档.md)（[Word 版](docs/设计文档.docx)）
- [演示视频脚本](docs/演示视频脚本.md)
- [答辩提纲（8 分钟）](docs/答辩提纲.md)
- [团队分工与进度计划](docs/团队分工与进度计划.md)：3 人分工；**11 月 13 日前**完成报名（报名表命名：`2026年计算机应用大赛-第一作者姓名-作品名称-01`），**12 月 1 日前**提交作品。

## 🛠️ 辅助脚本（可选）

```bash
python scripts/build_campus_map.py          # 核实坐标后，重新生成 data/campus_map.json
pip install playwright pypandoc_binary && playwright install chromium
python scripts/take_screenshots.py          # 服务运行时，为文档截图
python scripts/build_docx.py                # 设计文档.md → 设计文档.docx（含架构图）
```
