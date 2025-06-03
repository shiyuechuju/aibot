# telegram_bot/database.py
import sqlite3
import datetime
import logging

DATABASE_NAME = 'chat_history.db'
HISTORY_LIMIT = 40  # 20轮对话 * 每轮2条消息 (用户 + 机器人)

# 配置基础日志
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row  # 允许通过列名访问数据
    return conn

def init_db():
    """初始化数据库，创建表（如果不存在）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            message_id INTEGER NOT NULL,
            user_id INTEGER, -- 用户ID, 机器人消息时可能为NULL或机器人ID
            username TEXT,   -- Telegram 用户名, 可能为NULL
            first_name TEXT, -- 用户名字
            text TEXT NOT NULL,
            sender_type TEXT NOT NULL CHECK(sender_type IN ('user', 'bot')), -- 'user' 或 'bot'
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_chat_id_timestamp ON chat_history (chat_id, timestamp);
    ''')
    conn.commit()
    conn.close()
    logger.info("数据库已初始化。")

def store_message(chat_id: int, message_id: int, user_id: int, username: str, first_name: str, text: str, sender_type: str):
    """存储消息到数据库"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO chat_history (chat_id, message_id, user_id, username, first_name, text, sender_type, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (chat_id, message_id, user_id, username, first_name, text, sender_type, datetime.datetime.now()))
        conn.commit()
        logger.info(f"已存储来自聊天 {chat_id} 的 {sender_type} 消息: {text[:50]}...")
    except sqlite3.Error as e:
        logger.error(f"存储消息时出错: {e}")
    finally:
        conn.close()

def get_recent_history(chat_id: int, limit: int = HISTORY_LIMIT) -> list:
    """
    检索指定 chat_id 的最近 'limit' 条消息,
    按时间顺序（从旧到新，在检索到的集合内）。
    返回的列表每项是一个字典，包含 'sender_type', 'text', 'username', 'first_name'
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT sender_type, text, username, first_name
            FROM chat_history
            WHERE chat_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (chat_id, limit))
        # 结果是最新消息在前, 所以我们反转它以获得用于上下文的时间顺序
        history = [dict(row) for row in cursor.fetchall()][::-1]
        return history
    except sqlite3.Error as e:
        logger.error(f"检索历史记录时出错: {e}")
        return []
    finally:
        conn.close()

if __name__ == '__main__':
    # 直接运行此脚本时初始化数据库
    init_db()
    print(f"数据库 '{DATABASE_NAME}' 已初始化/检查完毕。")
    # 示例用法 (可选, 用于测试)
    # store_message(123, 1, 1001, '测试用户', '测试', '你好，来自用户', 'user')
    # store_message(123, 2, 0, '我的机器人', '机器人', '你好 测试!', 'bot')
    # history = get_recent_history(123)
    # for entry in history:
    #     sender_name = entry.get('username') or entry.get('first_name') or ("机器人" if entry['sender_type'] == 'bot' else "未知用户")
    #     print(f"{sender_name} ({entry['sender_type']}): {entry['text']}")