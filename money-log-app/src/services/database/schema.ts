export const CREATE_TABLES_SQL = `
  CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    icon TEXT NOT NULL DEFAULT '💳',
    color TEXT NOT NULL DEFAULT '#6B7280',
    type TEXT NOT NULL CHECK(type IN ('income','expense'))
  );

  CREATE TABLE IF NOT EXISTS subsidies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'government',
    total_amount INTEGER NOT NULL,
    remaining_amount INTEGER NOT NULL,
    card_name TEXT NOT NULL DEFAULT '',
    start_date TEXT NOT NULL DEFAULT '',
    end_date TEXT NOT NULL DEFAULT '',
    is_active INTEGER NOT NULL DEFAULT 1,
    keywords TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
  );

  CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    amount INTEGER NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('income','expense')),
    category TEXT NOT NULL DEFAULT '기타',
    merchant TEXT NOT NULL DEFAULT '',
    card_name TEXT NOT NULL DEFAULT '',
    note TEXT NOT NULL DEFAULT '',
    date TEXT NOT NULL,
    source TEXT NOT NULL CHECK(source IN ('sms','notification','manual','paste')),
    is_subsidy INTEGER NOT NULL DEFAULT 0,
    subsidy_id INTEGER REFERENCES subsidies(id),
    raw_text TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
  );
`;

export const SEED_CATEGORIES_SQL = `
  INSERT OR IGNORE INTO categories (id, name, icon, color, type) VALUES
    (1, '식비', '🍱', '#EF4444', 'expense'),
    (2, '교통', '🚌', '#F97316', 'expense'),
    (3, '쇼핑', '🛍️', '#EAB308', 'expense'),
    (4, '의료', '🏥', '#22C55E', 'expense'),
    (5, '문화/여가', '🎬', '#06B6D4', 'expense'),
    (6, '카페', '☕', '#8B5CF6', 'expense'),
    (7, '마트/편의점', '🏪', '#EC4899', 'expense'),
    (8, '공과금', '💡', '#64748B', 'expense'),
    (9, '주거', '🏠', '#78716C', 'expense'),
    (10, '기타', '💳', '#6B7280', 'expense'),
    (11, '급여', '💰', '#16A34A', 'income'),
    (12, '이체', '↔️', '#2563EB', 'income'),
    (13, '지원금', '🎁', '#7C3AED', 'income'),
    (14, '기타수입', '📥', '#059669', 'income');
`;
