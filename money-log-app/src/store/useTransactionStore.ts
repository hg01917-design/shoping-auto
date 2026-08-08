import { create } from 'zustand';
import { Transaction, ParsedPayment } from '../types';
import {
  getTransactions, insertTransaction, deleteTransaction,
  getMonthlyStats, getCategoryStats,
} from '../services/database';
import { guessCategory } from '../services/smsParser';
import dayjs from 'dayjs';

interface TransactionState {
  transactions: Transaction[];
  loading: boolean;
  currentMonth: string;

  loadTransactions: (month?: string, isSubsidy?: boolean) => Promise<void>;
  addFromParsed: (parsed: ParsedPayment, subsidyId?: number) => Promise<number>;
  addManual: (t: Omit<Transaction, 'id' | 'createdAt'>) => Promise<number>;
  remove: (id: number) => Promise<void>;
  getMonthlyStats: (year: string) => Promise<{ month: string; income: number; expense: number; subsidyUsed: number }[]>;
  getCategoryStats: (month: string) => Promise<{ category: string; total: number }[]>;
  setMonth: (month: string) => void;
}

export const useTransactionStore = create<TransactionState>((set, get) => ({
  transactions: [],
  loading: false,
  currentMonth: dayjs().format('YYYY-MM'),

  setMonth: (month) => set({ currentMonth: month }),

  loadTransactions: async (month, isSubsidy) => {
    set({ loading: true });
    const m = month ?? get().currentMonth;
    const data = await getTransactions({ month: m, isSubsidy });
    set({ transactions: data, loading: false });
  },

  addFromParsed: async (parsed, subsidyId) => {
    const category = parsed.isSubsidy ? '지원금' : guessCategory(parsed.merchant);
    const id = await insertTransaction({
      amount: parsed.amount,
      type: parsed.type,
      category,
      merchant: parsed.merchant,
      cardName: parsed.cardName,
      note: '',
      date: dayjs(parsed.date).format('YYYY-MM-DD HH:mm:ss'),
      source: 'notification',
      isSubsidy: parsed.isSubsidy,
      subsidyId: subsidyId ?? null,
      rawText: parsed.rawText,
    });
    await get().loadTransactions();
    return id;
  },

  addManual: async (t) => {
    const id = await insertTransaction(t);
    await get().loadTransactions();
    return id;
  },

  remove: async (id) => {
    await deleteTransaction(id);
    await get().loadTransactions();
  },

  getMonthlyStats: async (year) => {
    const rows = await getMonthlyStats(year);
    return rows.map((r) => ({
      month: r.month,
      income: r.income,
      expense: r.expense,
      subsidyUsed: r.subsidy_used,
    }));
  },

  getCategoryStats: async (month) => {
    return getCategoryStats(month);
  },
}));
