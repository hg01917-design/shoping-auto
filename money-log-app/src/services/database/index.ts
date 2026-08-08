import * as SQLite from 'expo-sqlite';
import { CREATE_TABLES_SQL, SEED_CATEGORIES_SQL } from './schema';
import { Transaction, Subsidy, Category } from '../../types';

let db: SQLite.SQLiteDatabase | null = null;

export async function getDb(): Promise<SQLite.SQLiteDatabase> {
  if (!db) {
    db = await SQLite.openDatabaseAsync('moneylog.db');
    await db.execAsync(CREATE_TABLES_SQL);
    await db.execAsync(SEED_CATEGORIES_SQL);
  }
  return db;
}

// ─── Transactions ────────────────────────────────────────────────────────────

export async function insertTransaction(
  t: Omit<Transaction, 'id' | 'createdAt'>
): Promise<number> {
  const db = await getDb();
  const result = await db.runAsync(
    `INSERT INTO transactions
      (amount, type, category, merchant, card_name, note, date, source, is_subsidy, subsidy_id, raw_text)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    [
      t.amount, t.type, t.category, t.merchant, t.cardName,
      t.note, t.date, t.source, t.isSubsidy ? 1 : 0,
      t.subsidyId ?? null, t.rawText,
    ]
  );
  return result.lastInsertRowId;
}

export async function getTransactions(opts?: {
  month?: string;
  isSubsidy?: boolean;
  subsidyId?: number;
}): Promise<Transaction[]> {
  const db = await getDb();
  let sql = 'SELECT * FROM transactions WHERE 1=1';
  const params: (string | number | null)[] = [];
  if (opts?.month) { sql += ' AND strftime("%Y-%m", date) = ?'; params.push(opts.month); }
  if (opts?.isSubsidy !== undefined) { sql += ' AND is_subsidy = ?'; params.push(opts.isSubsidy ? 1 : 0); }
  if (opts?.subsidyId !== undefined) { sql += ' AND subsidy_id = ?'; params.push(opts.subsidyId); }
  sql += ' ORDER BY date DESC, created_at DESC';
  const rows = await db.getAllAsync<Record<string, unknown>>(sql, params);
  return rows.map(rowToTransaction);
}

export async function deleteTransaction(id: number): Promise<void> {
  const db = await getDb();
  await db.runAsync('DELETE FROM transactions WHERE id = ?', [id]);
}

export async function getMonthlyStats(year: string) {
  const db = await getDb();
  return db.getAllAsync<{ month: string; income: number; expense: number; subsidy_used: number }>(
    `SELECT
       strftime('%Y-%m', date) as month,
       SUM(CASE WHEN type='income' AND is_subsidy=0 THEN amount ELSE 0 END) as income,
       SUM(CASE WHEN type='expense' AND is_subsidy=0 THEN amount ELSE 0 END) as expense,
       SUM(CASE WHEN type='expense' AND is_subsidy=1 THEN amount ELSE 0 END) as subsidy_used
     FROM transactions
     WHERE strftime('%Y', date) = ?
     GROUP BY month ORDER BY month`,
    [year]
  );
}

export async function getCategoryStats(month: string) {
  const db = await getDb();
  return db.getAllAsync<{ category: string; total: number }>(
    `SELECT category, SUM(amount) as total
     FROM transactions
     WHERE type='expense' AND strftime('%Y-%m', date) = ?
     GROUP BY category ORDER BY total DESC`,
    [month]
  );
}

// ─── Subsidies ────────────────────────────────────────────────────────────────

export async function getSubsidies(activeOnly = false): Promise<Subsidy[]> {
  const db = await getDb();
  const sql = activeOnly
    ? 'SELECT * FROM subsidies WHERE is_active=1 ORDER BY created_at DESC'
    : 'SELECT * FROM subsidies ORDER BY created_at DESC';
  const rows = await db.getAllAsync<Record<string, unknown>>(sql);
  return rows.map(rowToSubsidy);
}

export async function insertSubsidy(
  s: Omit<Subsidy, 'id' | 'createdAt'>
): Promise<number> {
  const db = await getDb();
  const result = await db.runAsync(
    `INSERT INTO subsidies
      (name, type, total_amount, remaining_amount, card_name, start_date, end_date, is_active, keywords)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    [
      s.name, s.type, s.totalAmount, s.remainingAmount,
      s.cardName, s.startDate, s.endDate, s.isActive ? 1 : 0,
      JSON.stringify(s.keywords),
    ]
  );
  return result.lastInsertRowId;
}

export async function updateSubsidyRemaining(id: number, remaining: number): Promise<void> {
  const db = await getDb();
  await db.runAsync('UPDATE subsidies SET remaining_amount = ? WHERE id = ?', [remaining, id]);
}

export async function updateSubsidy(s: Subsidy): Promise<void> {
  const db = await getDb();
  await db.runAsync(
    `UPDATE subsidies SET name=?, type=?, total_amount=?, remaining_amount=?,
      card_name=?, start_date=?, end_date=?, is_active=?, keywords=?
     WHERE id=?`,
    [
      s.name, s.type, s.totalAmount, s.remainingAmount,
      s.cardName, s.startDate, s.endDate, s.isActive ? 1 : 0,
      JSON.stringify(s.keywords), s.id,
    ]
  );
}

export async function deleteSubsidy(id: number): Promise<void> {
  const db = await getDb();
  await db.runAsync('DELETE FROM subsidies WHERE id = ?', [id]);
}

// ─── Categories ───────────────────────────────────────────────────────────────

export async function getCategories(): Promise<Category[]> {
  const db = await getDb();
  const rows = await db.getAllAsync<Category>('SELECT * FROM categories ORDER BY type, id');
  return rows;
}

// ─── Row mappers ──────────────────────────────────────────────────────────────

function rowToTransaction(row: Record<string, unknown>): Transaction {
  return {
    id: row.id as number,
    amount: row.amount as number,
    type: row.type as 'income' | 'expense',
    category: row.category as string,
    merchant: row.merchant as string,
    cardName: row.card_name as string,
    note: row.note as string,
    date: row.date as string,
    source: row.source as Transaction['source'],
    isSubsidy: (row.is_subsidy as number) === 1,
    subsidyId: row.subsidy_id as number | null,
    rawText: row.raw_text as string,
    createdAt: row.created_at as string,
  };
}

function rowToSubsidy(row: Record<string, unknown>): Subsidy {
  return {
    id: row.id as number,
    name: row.name as string,
    type: row.type as Subsidy['type'],
    totalAmount: row.total_amount as number,
    remainingAmount: row.remaining_amount as number,
    cardName: row.card_name as string,
    startDate: row.start_date as string,
    endDate: row.end_date as string,
    isActive: (row.is_active as number) === 1,
    keywords: JSON.parse((row.keywords as string) || '[]'),
    createdAt: row.created_at as string,
  };
}
