import { create } from 'zustand';
import { Subsidy } from '../types';
import {
  getSubsidies, insertSubsidy, updateSubsidy,
  updateSubsidyRemaining, deleteSubsidy,
} from '../services/database';

interface SubsidyState {
  subsidies: Subsidy[];
  loading: boolean;

  load: () => Promise<void>;
  add: (s: Omit<Subsidy, 'id' | 'createdAt'>) => Promise<number>;
  update: (s: Subsidy) => Promise<void>;
  deduct: (id: number, amount: number) => Promise<void>;
  remove: (id: number) => Promise<void>;
  findMatchingSubsidy: (keyword: string, cardName: string) => Subsidy | null;
}

export const useSubsidyStore = create<SubsidyState>((set, get) => ({
  subsidies: [],
  loading: false,

  load: async () => {
    set({ loading: true });
    const data = await getSubsidies();
    set({ subsidies: data, loading: false });
  },

  add: async (s) => {
    const id = await insertSubsidy(s);
    await get().load();
    return id;
  },

  update: async (s) => {
    await updateSubsidy(s);
    await get().load();
  },

  deduct: async (id, amount) => {
    const subsidy = get().subsidies.find((s) => s.id === id);
    if (!subsidy) return;
    const newRemaining = Math.max(0, subsidy.remainingAmount - amount);
    await updateSubsidyRemaining(id, newRemaining);
    await get().load();
  },

  remove: async (id) => {
    await deleteSubsidy(id);
    await get().load();
  },

  findMatchingSubsidy: (keyword, cardName) => {
    const { subsidies } = get();
    return (
      subsidies.find((s) => {
        const keywordMatch = s.keywords.some(
          (kw) => keyword.toLowerCase().includes(kw.toLowerCase())
        );
        const cardMatch = !s.cardName || s.cardName === cardName;
        return s.isActive && (keywordMatch || cardMatch);
      }) ?? null
    );
  },
}));
