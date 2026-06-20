import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import dayjs from 'dayjs';
import { Transaction } from '../types';

interface Props {
  transaction: Transaction;
  showDate?: boolean;
}

const CATEGORY_ICONS: Record<string, string> = {
  '식비': '🍱', '교통': '🚌', '쇼핑': '🛍️', '의료': '🏥',
  '문화/여가': '🎬', '카페': '☕', '마트/편의점': '🏪',
  '공과금': '💡', '주거': '🏠', '급여': '💰', '이체': '↔️',
  '지원금': '🎁', '기타수입': '📥', '기타': '💳',
};

export function TransactionItem({ transaction: t, showDate = true }: Props) {
  const icon = CATEGORY_ICONS[t.category] ?? '💳';
  const isIncome = t.type === 'income';

  return (
    <View style={styles.container}>
      <View style={styles.iconBox}>
        <Text style={styles.icon}>{icon}</Text>
        {t.isSubsidy && <View style={styles.subsidyDot} />}
      </View>
      <View style={styles.info}>
        <Text style={styles.merchant} numberOfLines={1}>
          {t.merchant || t.cardName || t.category}
        </Text>
        <Text style={styles.meta}>
          {t.cardName ? `${t.cardName} · ` : ''}
          {showDate ? dayjs(t.date).format('M/D HH:mm') : t.category}
          {t.isSubsidy ? ' · 🎁지원금' : ''}
        </Text>
      </View>
      <Text style={[styles.amount, isIncome ? styles.incomeColor : styles.expenseColor]}>
        {isIncome ? '+' : '-'}{t.amount.toLocaleString()}원
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row', alignItems: 'center',
    paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: '#F3F4F6',
  },
  iconBox: { position: 'relative', marginRight: 12 },
  icon: { fontSize: 28 },
  subsidyDot: {
    position: 'absolute', top: 0, right: -2,
    width: 8, height: 8, borderRadius: 4, backgroundColor: '#7C3AED',
  },
  info: { flex: 1 },
  merchant: { fontSize: 15, fontWeight: '500', color: '#111827' },
  meta: { fontSize: 12, color: '#9CA3AF', marginTop: 2 },
  amount: { fontSize: 16, fontWeight: '600' },
  incomeColor: { color: '#16A34A' },
  expenseColor: { color: '#DC2626' },
});
