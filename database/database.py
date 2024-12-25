import aiosqlite

DB_LOCATION = 'database/database.db'


async def init_db():
    async with aiosqlite.connect(DB_LOCATION) as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS users (
                                id INTEGER PRIMARY KEY,
                                queries_left INTEGER DEFAULT 20,
                                is_premium INTEGER DEFAULT 0
                            )''')
        await db.commit()


async def add_user(tg_id: int):
    async with aiosqlite.connect(DB_LOCATION) as db:
        await db.execute('''INSERT OR IGNORE INTO users (id) VALUES (?)''',
                         (tg_id,))
        await db.commit()


async def get_user_data(tg_id: int):
    async with aiosqlite.connect(DB_LOCATION) as db:
        async with db.execute("SELECT * FROM users WHERE id = ?", (tg_id,)) as cursor:
            row = await cursor.fetchone()
            return row


async def process_user_query(tg_id: int):
    user_data = await get_user_data(tg_id)
    if user_data[1] == 0 and user_data[2] == -1:
        raise Exception('Не осталось запросов')
    elif user_data[2] == 0:
        async with aiosqlite.connect(DB_LOCATION) as db:
            await db.execute('''UPDATE users SET queries_left = queries_left - 1 WHERE id = ?''',
                             (tg_id,))
            await db.commit()


async def set_premium(tg_id: int):
    async with aiosqlite.connect(DB_LOCATION) as db:
        await db.execute('''UPDATE users SET is_premium = 1 WHERE id = ?''',
                         (tg_id,))
        await db.commit()
