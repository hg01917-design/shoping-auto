import React, { useEffect, useState, useMemo } from 'react';
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity,
  TextInput, Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import dayjs from 'dayjs';
import { useTransactionStore } from '../../store/useTransactionStore';
import { TransactionItem } from '../../components/TransactionItem';
import { Transaction } from '../../types';

type FilterTab = 'all' | 'expense' | 'income' | 'subsidy';

export default function TransactionListScreen() {
  const { transactions, loading, loadTransactions, remove, currentMonth, setMonth } = useTransactionStore();
  const [tab, setTab] = useState<FilterTab>('all');
  const [search, setSearch] = useState('');

  useEffect(() => {
    loadTransactions(currentMonth);
  }, [currentMonth]);

  const filtered = useMemo(() => {
    let list = transactions;
    if (tab === 'expense') list = list.filter((t) => t.type === 'expense' && !t.isSubsidy);
    else if (tab === 'income') list = list.filter((t) => t.type === 'income');
    else if (tab === 'subsidy') list = list.filter((t) => t.isSubsidy);
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(
        (t) =>
          t.merchant.toLowerCase().includes(q) ||
          t.category.toLowerCase().includes(q) ||
          t.cardName.toLowerCase().includes(q)
      );
    }
    return list;
  }, [transactions, tab, search]);

  function prevMonth() {
    setMonth(dayjs(currentMonth).subtract(1, 'month').format('YYYY-MM'));
  }
  function nextMonth() {
    setMonth(dayjs(currentMonth).add(1, 'month').format('YYYY-MM'));
  }

  async function handleDelete(t: Transaction) {
    Alert.alert('삭제', `"${t.merchant || t.category}" 내역을 삭제할까요?`, [
      { text: '취소', style: 'cancel' },
      { text: '삭제', style: 'destructive', onPress: () => remove(t.id) },
    ]);
  }

  const tabs: { key: FilterTab; label: string }[] = [
    { key: 'all', label: '전체' },
    { key: 'expense', label: '지출' },
    { key: 'income', label: '수입' },
    { key: 'subsidy', label: '🎁 지원금' },
  ];

  return (
    <SafeAreaView style={styles.container}>
      {/* 월 선택 */}
      <View style={styles.monthRow}>
        <TouchableOpacity onPress={prevMonth} style={styles.arrowBtn}>
          <Text style={styles.arrow}>‹</Text>
        </TouchableOpacity>
        <Text style={styles.monthText}>{dayjs(currentMonth).format('YYYY년 M월')}</Text>
        <TouchableOpacity onPress={nextMonth} style={styles.arrowBtn}>
          <Text style={styles.arrow}>›</Text>
        </TouchableOpacity>
      </View>

      {/* 필터 탭 */}
      <View style={styles.tabRow}>
        {tabs.map((t) => (
          <TouchableOpacity
            key={t.key}
            style={[styles.tab, tab === t.key && styles.tabActive]}
            onPress={() => setTab(t.key)}
          >
            <Text style={[styles.tabText, tab === t.key && styles.tabTextActive]}>
              {t.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* 검색 */}
      <View style={styles.searchBox}>
        <Text style={styles.searchIcon}>🔍</Text>
        <TextInput
          style={styles.searchInput}
          placeholder="가맹점, 카테고리 검색"
          value={search}
          onChangeText={setSearch}
        />
      </View>

      <ScrollView>
        {filtered.length === 0 ? (
          <Text style={styles.emptyText}>내역이 없습니다</Text>
        ) : (
          filtered.map((t) => (
            <TouchableOpacity
              key={t.id}
              onLongPress={() => handleDelete(t)}
              style={styles.itemWrap}
            >
              <TransactionItem transaction={t} />
            </TouchableOpacity>
          ))
        )}
        <View style={{ height: 40 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F9FAFB' },
  monthRow: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    paddingVertical: 12,
  },
  arrowBtn: { padding: 8 },
  arrow: { fontSize: 24, color: '#2563EB' },
  monthText: { fontSize: 18, fontWeight: '700', color: '#111827', marginHorizontal: 16 },
  tabRow: {
    flexDirection: 'row', paddingHorizontal: 16, gap: 8, marginBottom: 12,
  },
  tab: {
    paddingHorizontal: 16, paddingVertical: 8,
    borderRadius: 20, backgroundColor: '#F3F4F6',
  },
  tabActive: { backgroundColor: '#2563EB' },
  tabText: { fontSize: 14, color: '#6B7280' },
  tabTextActive: { color: '#fff', fontWeight: '600' },
  searchBox: {
    flexDirection: 'row', alignItems: 'center',
    marginHorizontal: 16, marginBottom: 8,
    backgroundColor: '#fff', borderRadius: 10, paddingHorizontal: 12,
    borderWidth: 1, borderColor: '#E5E7EB',
  },
  searchIcon: { fontSize: 16, marginRight: 8 },
  searchInput: { flex: 1, paddingVertical: 10, fontSize: 14 },
  emptyText: { color: '#9CA3AF', textAlign: 'center', paddingVertical: 40 },
  itemWrap: { paddingHorizontal: 16 },
});
