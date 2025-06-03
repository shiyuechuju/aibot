# telegram_bot/bot.py
import logging
import os
import json
import httpx
from telegram import Update, ForceReply      # ForceReply 还在 telegram 顶级模块
from telegram.constants import ParseMode   # ParseMode 移动到了这里
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
# from telegram.helpers import escape_markdown # 如果需要更复杂的Markdown转义

import database

# --- 配置 ---
BOT_TOKEN = "79102335*lLKgZ-B0pHnChVVPBZ_9WnyJraLmQ"
KIMI_API_KEY = "sk-mnZvTUApggdZ*z3lqGezqmNYwWh8ot0UFSpR"
KIMI_MODEL = "moonshot-v1-8k" # 或者更长的上下文模型如 moonshot-v1-32k，如果报价表很大
KIMI_CHAT_API_URL = "https://api.moonshot.cn/v1/chat/completions"

# --- 新增业务逻辑配置 ---
SERVER_DATA_FILE = "server.txt"  # 报价表文件名
SERVER_DATA_CONTENT = ""         # 用于存储 server.txt 内容
PAYMENT_INFO_TEXT = "TELW5kSV8eMXfwrVKYM*"  # 收款码文本
CUSTOMER_SERVICE_CONTACT = "@datingkefu"  # 客服联系方式
# Kimi需要输出这个精确的字符串（包括换行符，如果设计如此）来触发后续动作
TRIGGER_PURCHASE_PHRASE = "[USER_CONFIRMED_PURCHASE_SEND_PAYMENT_DETAILS]"

# 配置基础日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def load_server_data(filepath=SERVER_DATA_FILE):
    """加载服务器报价表数据到全局变量 SERVER_DATA_CONTENT"""
    global SERVER_DATA_CONTENT
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            SERVER_DATA_CONTENT = f.read()
        if not SERVER_DATA_CONTENT.strip():
            logger.warning(f"警告：报价文件 {filepath} 为空或只包含空白字符。")
            SERVER_DATA_CONTENT = "抱歉，产品报价信息当前不可用。" # 给Kimi一个明确的信号
        else:
            logger.info(f"报价文件 {filepath} 加载成功 (长度: {len(SERVER_DATA_CONTENT)} 字符)。")
    except FileNotFoundError:
        logger.error(f"错误：找不到报价文件 {filepath}。机器人将无法提供准确报价。")
        SERVER_DATA_CONTENT = "抱歉，我暂时无法访问产品报价信息，相关功能可能受限。"
    except Exception as e:
        logger.error(f"加载报价文件 {filepath} 时发生错误: {e}")
        SERVER_DATA_CONTENT = "抱歉，加载产品报价信息时出错，相关功能可能受限。"

# --- Kimi API 相关函数 ---
def format_history_for_kimi(history: list) -> list:
    """将数据库历史记录格式化为 Kimi API 所需的 messages 格式。"""
    kimi_messages = []
    system_prompt = (
        "你是一位专业的服务器销售客服。你的主要任务是根据用户需求，从我提供给你的产品报价表中找到合适的服务器配置并进行报价。你的回答应该严格基于这份报价表。"
        "以下是当前的产品报价表：\n"
        "==================== 产品报价表 START ====================\n"
        f"{SERVER_DATA_CONTENT}\n"
        "==================== 产品报价表 END ======================\n\n"
        "你需要注意以下几点：\n"
        "1.  **上下文整合**：仔细理解用户的每一句话，并结合整个对话的上下文。用户可能会分多步提供服务器的配置信息（例如CPU型号、核心数、内存大小、硬盘类型和容量、带宽大小、线路类型、IP数量，甚至操作系统需求如Windows Server 2012等）。你需要将这些分散的信息整合起来，形成一个完整的用户需求画像。\n"
        "2.  **基于报价表回答**：当用户提供的信息足以在报价表中匹配到一个或多个产品时，请向用户推荐这些产品，并明确给出报价表中的**确切价格**。\n"
        "3.  **处理不明确需求**：如果用户需求不明确，或者报价表中没有完全匹配的产品，你可以尝试推荐最相似的配置，或者向用户提问以获取更详细的需求信息。明确告知用户哪些部分是匹配的，哪些是相似推荐的。\n"
        "4.  **价格准确性**：价格必须严格按照报价表中的信息给出，不要自行计算或杜撰价格。\n"
        "5.  **操作系统需求**：用户的操作系统需求（如Windows 2012）是一个重要参数。如果用户提到，请记录下来，并在最终确认配置时提及。如果报价表不含操作系统价格，你可以告知用户“报价表中的价格通常不包含操作系统费用，如需预装Windows Server 2012，请在支付后联系客服确认相关事宜或可能的额外费用”。\n"
        "6.  **购买确认流程**：当用户明确表示想要购买某个配置（例如说“来一台”、“就要这个了”、“下单”、“我买了”、“确定购买”、“付款”等类似意图），并且你已经向用户清晰地总结了他们选择的配置（包括所有已知的参数如CPU、内存、硬盘、带宽、地区、操作系统需求）和最终价格后：\n"
        "    *   你的回复应该首先是对用户选择的配置和价格的**最终确认总结**。\n"
        f"    *   然后，在这段总结之后，**另起一行，且该行只包含这个精确的特殊标记**：`{TRIGGER_PURCHASE_PHRASE}`。不要在这个标记前后添加任何其他文字、标点或空格。\n"
        "7.  **一般性问题**：对于一般的技术咨询或与服务器无关的问题，请尝试礼貌地回答，或者友好地引导用户回到服务器产品的主题上。\n"
        "请始终保持友好和专业的态度，回答尽量简洁明了，避免不必要的寒暄。"
    )
    kimi_messages.append({"role": "system", "content": system_prompt})

    for entry in history:
        role = "user" if entry['sender_type'] == 'user' else "assistant"
        kimi_messages.append({"role": role, "content": entry['text']})
    return kimi_messages

async def call_kimi_api_http(messages: list, model: str = KIMI_MODEL, api_key: str = KIMI_API_KEY) -> str:
    """使用 HTTP 请求调用 Kimi Chat API。"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,  # 降低温度，使其更具确定性，减少创意发挥，专注于报价表
        # "max_tokens": 1500, # 可以根据需要设置，防止回复过长无法发送
    }

    async with httpx.AsyncClient(timeout=90.0) as client: # 增加超时，Kimi处理复杂上下文可能耗时
        try:
            logger.info(f"向 Kimi API ({KIMI_CHAT_API_URL}) 发送包含 {len(messages)} 条消息的请求...")
            response = await client.post(KIMI_CHAT_API_URL, headers=headers, json=payload)
            response.raise_for_status()
            response_data = response.json()
            if response_data and "choices" in response_data and len(response_data["choices"]) > 0:
                content = response_data["choices"][0].get("message", {}).get("content")
                if content:
                    logger.info("Kimi API 成功返回回复。")
                    return content.strip()
                else:
                    logger.error(f"Kimi API 返回了空的 content: {response_data}")
                    return "抱歉，AI助手未能生成有效回复。"
            else:
                logger.error(f"Kimi API 返回的响应格式不符合预期: {response_data}")
                return "抱歉，从AI助手收到的响应格式不正确。"
        except httpx.HTTPStatusError as e:
            error_detail = "未知错误"
            try:
                error_data = e.response.json()
                error_detail = error_data.get("error", {}).get("message", e.response.text)
            except json.JSONDecodeError: # 如果错误响应不是JSON
                error_detail = e.response.text
            logger.error(f"Kimi API HTTP 状态错误: {e.response.status_code} - {error_detail}")
            return f"抱歉，调用AI服务时出错 (HTTP {e.response.status_code})。请稍后再试。"
        except httpx.RequestError as e: #例如 httpx.ConnectTimeout, httpx.ReadTimeout
            logger.error(f"Kimi API 请求错误 (例如网络问题或超时): {e}")
            return f"抱歉，连接AI服务时发生网络错误或超时。请稍后再试。"
        except json.JSONDecodeError as e:
            logger.error(f"解析 Kimi API 响应 JSON 时出错: {e}. Response text: {response.text if 'response' in locals() else 'N/A'}")
            return "抱歉，解析AI服务响应时出错。"
        except Exception as e:
            logger.exception("调用 Kimi API 时发生未知错误")
            return "抱歉，与AI服务交互时发生未知错误。"

# --- Bot Command Handlers ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    welcome_message = (
        f"你好 {user.mention_html()}！\n"
        f"我是您的专属服务器采购助手，由 Kimi AI 驱动。\n"
        f"请告诉我您的服务器需求，例如CPU、内存、硬盘、带宽、地区等，我会根据我们的报价表为您推荐合适的配置和价格。\n"
        f"您可以分多步告诉我您的需求，我会努力理解并整合它们。\n"
        f"例如：\n"
        f"  用户: \"有没有E3的服务器？\"\n"
        f"  用户: \"内存要16G\"\n"
        f"  用户: \"硬盘1T HDD，香港地区的\"\n"
        f"  用户: \"带宽20M CN2\"\n"
        f"  用户: \"需要Windows Server 2012系统\"\n"
        f"  用户: \"这款多少钱？\" 或 \"就这个，来一台\"\n"
        f"准备好了吗？请开始您的咨询吧！"
    )
    await update.message.reply_html(welcome_message, reply_markup=ForceReply(selective=True))
    logger.info(f"用户 {user.id} ({user.username}) 启动了机器人。")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "我是您的服务器采购助手。\n"
        "- 我可以根据您提供的CPU、内存、硬盘、带宽、地区等需求，从报价表中查询产品和价格。\n"
        "- 我会记住我们最近的对话（约20轮）来理解上下文。\n"
        "- 如果您确定购买，我会提供支付信息。\n"
        f"- 支付遇到问题或需要人工服务，请联系客服：{CUSTOMER_SERVICE_CONTACT}\n"
        "请直接告诉我您的需求。"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_message_text = update.message.text
    chat_id = update.message.chat_id
    user = update.effective_user

    # 1. 存储用户消息
    database.store_message(
        chat_id=chat_id,
        message_id=update.message.message_id,
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        text=user_message_text,
        sender_type='user'
    )

    # 2. 检索最近的聊天记录 (为Kimi准备上下文)
    # HISTORY_LIMIT - 1 是因为当前用户消息会另外添加
    db_history = database.get_recent_history(chat_id, limit=database.HISTORY_LIMIT - 1)

    # 3. 准备 Kimi API 的输入
    kimi_messages_context = format_history_for_kimi(db_history)
    kimi_messages_context.append({"role": "user", "content": user_message_text})

    # 4. 调用 Kimi API 生成回复
    logger.info(f"准备向 Kimi 发送 {len(kimi_messages_context)} 条消息进行处理。用户最新消息: {user_message_text[:100]}...")
    bot_reply_from_kimi = await call_kimi_api_http(messages=kimi_messages_context)

    # 5. 处理Kimi的回复，检查是否有购买触发标记
    final_bot_reply_to_send = bot_reply_from_kimi
    is_purchase_confirmed = False

    # 精确匹配触发短语，并确保它可能独立一行或在文本末尾
    if TRIGGER_PURCHASE_PHRASE in bot_reply_from_kimi:
        is_purchase_confirmed = True
        # 从Kimi的回复中移除触发标记，得到纯粹的对话内容
        # 使用 split 来处理标记可能在单独一行的情况
        parts = bot_reply_from_kimi.split(TRIGGER_PURCHASE_PHRASE)
        final_bot_reply_to_send = parts[0].strip() # 取标记之前的部分
        if len(parts) > 1 and parts[1].strip(): # 如果标记后还有内容（不应该有，但做兼容）
            final_bot_reply_to_send += "\n" + parts[1].strip()

        logger.info("Kimi 返回了购买确认标记。")

    # 6. 发送Kimi的主要回复 (移除标记后的)
    if not final_bot_reply_to_send.strip() and is_purchase_confirmed:
        # 如果Kimi只返回了标记（理论上不应该），给一个通用购买确认
        final_bot_reply_to_send = "好的，已收到您的购买请求，正在为您准备订单详情。"
    elif not final_bot_reply_to_send.strip():
        final_bot_reply_to_send = "AI助手正在思考，请稍等片刻..."


    # 对Kimi的回复进行长度检查和发送
    # Telegram消息长度限制约为4096字符
    if len(final_bot_reply_to_send) > 4000: # 留一些余量
        logger.warning(f"Kimi 主要回复过长 ({len(final_bot_reply_to_send)} chars)，将被截断。")
        # 尝试按段落或句子截断，而不是硬截断
        safe_ตัด = final_bot_reply_to_send[:3900].rfind('\n')
        if safe_ตัด == -1: safe_ตัด = final_bot_reply_to_send[:3900].rfind('.')
        if safe_ตัด == -1: safe_ตัด = 3900
        final_bot_reply_to_send = final_bot_reply_to_send[:safe_ตัด] + "\n\n[回复内容过长，已截断...]"

    sent_message = await update.message.reply_text(final_bot_reply_to_send)

    # 7. 如果是确认购买，则追加发送支付信息和客服联系方式
    if is_purchase_confirmed:
        payment_message_text = (
            f"请使用以下方式支付您选定的配置：\n"
            f"收款地址: `{PAYMENT_INFO_TEXT}`\n" # Markdown代码块使其易于复制
            f"_(点击上方地址即可复制)_\n\n"
            f"支付完成后，请联系客服 {CUSTOMER_SERVICE_CONTACT} 为您安排开通服务器事宜。"
        )
        try:
            # 使用 MarkdownV2 发送支付信息
            await update.message.reply_text(payment_message_text, parse_mode=ParseMode.MARKDOWN_V2)
            logger.info(f"已向用户 {chat_id} 发送支付信息 (MarkdownV2)。")
        except Exception as e:
            logger.error(f"发送MarkdownV2支付信息失败: {e}, 将尝试发送纯文本。")
            # 降级为纯文本发送
            plain_text_payment_message = (
                f"请使用以下方式支付您选定的配置：\n"
                f"收款地址: {PAYMENT_INFO_TEXT}\n\n"
                f"支付完成后，请联系客服 {CUSTOMER_SERVICE_CONTACT} 为您安排开通服务器事宜。"
            )
            await update.message.reply_text(plain_text_payment_message)

    # 8. 存储机器人发送给用户的主要回复 (不含特殊标记，也不含独立发送的支付信息)
    database.store_message(
        chat_id=chat_id,
        message_id=sent_message.message_id, # ID of the Kimi's main reply
        user_id=context.bot.id,
        username=context.bot.username,
        first_name=context.bot.first_name,
        text=final_bot_reply_to_send, # 存储的是Kimi回复的主体部分
        sender_type='bot'
    )
    logger.info(f"机器人已回复聊天 {chat_id}。Kimi上下文消息数: {len(kimi_messages_context)}")


# --- Main Bot Execution ---
def main() -> None:
    """启动机器人。"""
    load_server_data() # 在启动时加载报价表数据
    if not SERVER_DATA_CONTENT or "无法访问" in SERVER_DATA_CONTENT or "不可用" in SERVER_DATA_CONTENT or "出错" in SERVER_DATA_CONTENT:
        logger.critical("警告：服务器报价数据未能成功加载。机器人核心功能可能严重受限。请检查 " + SERVER_DATA_FILE)
        # 可以考虑是否在这种情况下阻止机器人启动，或者让其以受限模式运行

    if not BOT_TOKEN or not KIMI_API_KEY:
        logger.critical("错误：TELEGRAM_BOT_TOKEN 或 KIMI_API_KEY 未配置。机器人无法启动。")
        return

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("机器人正在启动...")
    application.run_polling()
    logger.info("机器人已停止。")

if __name__ == '__main__':
    main()
