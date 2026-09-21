export type TransactionType = 'income' | 'expense';
export type TransactionSource = 'sms' | 'notification' | 'manual' | 'paste';
export type SubsidyType = 'government' | 'local' | 'welfare' | 'custom';

export interface Transaction {
  id: number;
  amount: number;
  type: TransactionType;
  category: string;
  merchant: string;
  cardName: string;
  note: string;
  date: string;
  source: TransactionSource;
  isSubsidy: boolean;
  subsidyId: number | null;
  rawText: string;
  createdAt: string;
}

export interface Subsidy {
  id: number;
  name: string;
  type: SubsidyType;
  totalAmount: number;
  remainingAmount: number;
  cardName: string;
  startDate: string;
  endDate: string;
  isActive: boolean;
  keywords: string[];
  createdAt: string;
}

export interface Category {
  id: number;
  name: string;
  icon: string;
  color: string;
  type: TransactionType;
}

export interface ParsedPayment {
  amount: number;
  type: TransactionType;
  merchant: string;
  cardName: string;
  remainingBalance: number | null;
  isSubsidy: boolean;
  subsidyKeyword: string | null;
  date: Date;
  rawText: string;
}

export interface MonthlyStats {
  month: string;
  income: number;
  expense: number;
  subsidyUsed: number;
}

export interface CategoryStats {
  category: string;
  amount: number;
  color: string;
  percentage: number;
}
