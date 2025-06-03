# Telegram Kimi AI 聊天机器人 (服务器报价助手)

这是一个基于 Python 的 Telegram 机器人，它集成了 Kimi AI (Moonshot AI) 来提供具有上下文感知能力的对话。机器人主要设计为一个服务器采购助手，能够根据用户需求从预定义的报价表 (`server.txt`) 中查询服务器配置和价格，并在用户确认购买后提供支付信息。

## 主要功能

*   **上下文感知对话**：利用 Kimi AI 和本地 SQLite 数据库存储的聊天记录（最近约20轮对话）来理解对话上下文。
*   **基于报价表的问答**：机器人会读取 `server.txt` 文件中的服务器配置和价格信息，并根据用户提出的需求进行匹配和报价。
*   **多轮需求理解**：能够理解用户分多步提出的服务器配置要求（如CPU、内存、硬盘、带宽、操作系统等）。
*   **购买流程**：当用户明确表示购买意向后，机器人会总结配置和价格，并提供预设的收款信息和客服联系方式。
*   **聊天记录存储**：所有用户与机器人的对话都存储在本地的 `chat_history.db` (SQLite) 数据库中。
*   **Kimi API 直接调用**：通过 HTTP 请求直接与 Kimi Chat API进行交互。

## 技术栈

*   Python 3.x
*   [python-telegram-bot](https://python-telegram-bot.org/) (v20.0+)
*   [Kimi AI (Moonshot AI)](https://www.moonshot.cn/) - 通过其 HTTP API 访问
*   [SQLite](https://www.sqlite.org/index.html) - 用于本地数据存储
*   [httpx](https://www.python-httpx.org/) - 用于发送异步 HTTP 请求

## 项目结构     Use code with caution.Markdown  telegram_bot_kimi/
├── bot.py # 主要的机器人逻辑和 Telegram 交互
├── database.py # SQLite 数据库操作模块
├── server.txt # 服务器产品报价表 (需用户自行提供)
├── requirements.txt # Python 依赖库
├── README.md # 本文档
└── .env.example # (可选) 环境变量示例文件 ## 安装与运行

### 1. 先决条件

*   Python 3.8 或更高版本。
*   一个 Telegram Bot Token (从 @BotFather 获取)。
*   一个 Kimi AI API Key (从 Moonshot AI 官网获取)。

### 2. 克隆仓库 (或下载文件)

```bash
git clone <your-repository-url>
cd telegram_bot_kimi     Use code with caution.  3. 创建并激活虚拟环境 (推荐) python -m venv venv
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate     Use code with caution.Bash  4. 安装依赖 pip install -r requirements.txt     Use code with caution.Bash  5. 配置 API 密钥和报价表 方式一：直接修改  bot.py  (不推荐用于公共仓库) 打开  bot.py  文件，找到以下行并填入你的密钥： BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
KIMI_API_KEY = "YOUR_KIMI_API_KEY"     Use code with caution.Python  方式二：使用  .env  文件 (推荐) a. 确保  python-dotenv  在你的  requirements.txt  中并已安装。
b. 复制或重命名  .env.example  (如果提供了) 为  .env ，或者手动创建一个  .env  文件。
c. 在  .env  文件中添加以下内容： ```env
  TELEGRAM_BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"
  KIMI_API_KEY="YOUR_KIMI_API_KEY"
  ```     Use code with caution.  d. (重要) 在  bot.py  文件的顶部，确保以下代码被取消注释或添加（如果之前没有使用）： ```python
  import os
  from dotenv import load_dotenv
  load_dotenv() # 这会从 .env 文件加载变量到环境变量

  BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
  KIMI_API_KEY = os.getenv("KIMI_API_KEY")

  if not BOT_TOKEN or not KIMI_API_KEY:
      logger.critical("错误：TELEGRAM_BOT_TOKEN 或 KIMI_API_KEY 未配置。机器人无法启动。")
      # exit("API密钥缺失") # 或者其他处理方式
  ```     Use code with caution.
6. 准备报价表 将你的服务器报价数据放入名为  server.txt  的文件中，并确保它与  bot.py  在同一目录下。文件应为 UTF-8 编码。
报价表的格式应与机器人系统提示（ bot.py  中的  system_prompt ）中 Kimi 被告知的格式一致，以便 AI 能正确解析。
7. 初始化数据库 运行数据库初始化脚本（此脚本会创建  chat_history.db  文件及所需表结构）： python database.py     Use code with caution.Bash  你会看到类似 "数据库 'chat_history.db' 已初始化/检查完毕。" 的输出。
8. 运行机器人 python bot.py     Use code with caution.Bash  如果一切配置正确，机器人应该会启动并开始轮询 Telegram 更新。你会在控制台看到类似 "机器人正在启动..." 的日志。 如何与机器人交互
1.  在 Telegram 中找到你的机器人。
2.  发送  /start  命令查看欢迎信息和使用示例。
 3.  开始向机器人咨询服务器配置，例如： ◦  "你好，我想找个香港的服务器"  ◦  "CPU E3 的有吗？"  ◦  "内存需要16G"  ◦  "硬盘1TB，带宽20M CN2线路"  ◦  "这款服务器支持安装 Windows Server 2012 吗？"  ◦  "这个配置价格多少？"  ◦  "好的，我买这个了，来一台。"
 4.  如果机器人成功识别购买意图并确认配置，它会提供支付信息。   注意事项 •  API 密钥安全：绝对不要将你的真实 API 密钥直接提交到公共 GitHub 仓库中。 强烈建议使用  .env  文件配合  .gitignore  来管理敏感信息，或者使用服务器端环境变量。  •  Kimi API 的遵循度：机器人的回复质量和流程执行的准确性高度依赖于 Kimi AI 对系统提示的理解和遵循。你可能需要根据实际测试结果调整  bot.py  中的  system_prompt 。  •  Token 限制：报价表  server.txt  的内容会被包含在发送给 Kimi 的每次请求中。如果报价表非常大，可能会超出 Kimi 模型的上下文窗口限制（如  moonshot-v1-8k  约8000 tokens）。对于非常大的数据集，可能需要考虑更高级的 RAG (Retrieval Augmented Generation) 方案。  •  日志：请关注运行  bot.py  时控制台输出的日志，它们对于调试问题非常重要。   贡献 欢迎提交 Pull Requests 或报告 Issues。 许可证 MIT (如果选择MIT许可证，请创建一个 LICENSE 文件并放入MIT许可证文本) **在 `README.md` 中还需要注意：**

*   **`<your-repository-url>`**：记得替换成你实际的 GitHub 仓库 URL。
*   **`.env.example` 文件**：如果你选择使用 `.env` 文件的方式管理密钥，最好在仓库中提供一个 `.env.example` 文件，内容如下：
    ```
    # .env.example
    TELEGRAM_BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN_HERE"
    KIMI_API_KEY="YOUR_KIMI_API_KEY_HERE"
    ```
    并且，**确保将真实的 `.env` 文件添加到 `.gitignore` 文件中**，以防止它被提交：
    ```
    # .gitignore
    __pycache__/
    *.pyc
    *.pyo
    *.pyd
    .Python
    env/
    venv/
    pip-selfcheck.json
    *.db
    *.sqlite3
    .env  # <--- 这一行非常重要
    ```
*   **`LICENSE` 文件**：如果你想为项目添加一个开源许可证（如 MIT），你需要创建一个名为 `LICENSE` 的文件，并将许可证的文本内容粘贴进去。例如，MIT 许可证文本可以从 [choosealicense.com](https://choosealicense.com/licenses/mit/) 获取。


*   **`代码交流群`**： https://t.me/fwqjlq
作者： @kdnick
