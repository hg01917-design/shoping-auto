import React, { useEffect, useState } from 'react';
import { View, Text, ScrollView, StyleSheet } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import dayjs from 'dayjs';
import { useSubsidyStore } from '../../store/useSubsidyStore';
import { useTransactionStore } from '../../store/useTransactionStore';
import { TransactionItem } from '../../components/TransactionItem';
import { Transaction } from '../../types';
import { getTransactions } from '../../services/database';

export default function SubsidyDetailScreen({ route }: any) {
  const { id } = route.params;
  const { subsidies } = useSubsidyStore();
  const subsidy = subsidies.find((s) => s.id === id);
  const [txns, setTxns] = useState<Transaction[]>([]);

  useEffect(() => {
    if (id) {
      getTransactions({ subsidyId: id }).then(setTxns);
    }
  }, [id]);

  if (!subsidy) return null;

  const usedPct = subsidy.totalAmount > 0
    ? Math.round(((subsidy.totalAmount - subsidy.remainingAmount) / subsidy.totalAmount) * 100)
    : 0;
  const used = subsidy.totalAmount - subsidy.remainingAmount;

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView>
        {/* 지원금 요약 카드 */}
        <View style={styles.topCard}>
          <Text style={styles.name}>{subsidy.name}</Text>
          {subsidy.cardName ? <Text style={styles.cardName}>{subsidy.cardName}</Text> : null}

          <View style={styles.amountGrid}>
            <View style={styles.amountItem}>
              <Text style={styles.amountLabel}>잔여금액</Text>
              <Text style={[styles.amountValue, { color: '#7C3AED' }]}>
                {subsidy.remainingAmount.toLocaleString()}원
              </Text>
            </View>
            <View style={styles.amountItem}>
              <Text style={styles.amountLabel}>사용금액</Text>
              <Text style={[styles.amountValue, { color: '#DC2626' }]}>
                {used.toLocaleString()}원
              </Text>
            </View>
            <View style={styles.amountItem}>
              <Text style={styles.amountLabel}>총지원금</Text>
              <Text style={styles.amountValue}>{subsidy.totalAmount.toLocaleString()}원</Text>
            </View>
          </View>

          <View style={styles.progressBg}>
            <View style={[styles.progressFill, { width: `${usedPct}%` as any }]} />
          </View>
          <Text style={styles.progressText}>{usedPct}% 사용됨</Text>

          {subsidy.endDate && (
            <Text style={styles.expireText}>
              만료일 {dayjs(subsidy.endDate).format('YYYY년 M월 D일')}
              {' ('}
              {dayjs(subsidy.endDate).diff(dayjs(), 'day')}일 남음)
            </Text>
          )}
        </View>

        {/* 키워드 */}
        {subsidy.keywords.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>자동 감지 키워드</Text>
            <View style={styles.keywordRow}>
              {subsidy.keywords.map((k) => (
                <View key={k} style={styles.keyword}>
                  <Text style={styles.keywordText}>{k}</Text>
                </View>
              ))}
            </View>
          </View>
        )}

        {/* 관련 거래 내역 */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>사용 내역 ({txns.length}건)</Text>
          {txns.length === 0 ? (
            <Text style={styles.emptyText}>아직 사용 내역이 없습니다</Text>
          ) : (
            txns.map((t) => <TransactionItem key={t.id} transaction={t} />)
          )}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F9FAFB' },
  topCard: {
    margin: 16, padding: 20,
    backgroundColor: '#fff', borderRadius: 16,
    elevation: 2, shadowColor: '#000', shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.08, shadowRadius: 4,
  },
  name: { fontSize: 22, fontWeight: '700', color: '#111827', marginBottom: 4 },
  cardName: { fontSize: 14, color: '#9CA3AF', marginBottom: 16 },
  amountGrid: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 16 },
  amountItem: { alignItems: 'center' },
  amountLabel: { fontSize: 11, color: '#9CA3AF', marginBottom: 4 },
  amountValue: { fontSize: 18, fontWeight: '700', color: '#111827' },
  progressBg: { height: 8, backgroundColor: '#F3F4F6', borderRadius: 4, marginBottom: 6 },
  progressFill: { height: 8, backgroundColor: '#7C3AED', borderRadius: 4 },
  progressText: { fontSize: 12, color: '#7C3AED', textAlign: 'right' },
  expireText: { fontSize: 13, color: '#6B7280', marginTop: 8 },
  section: { paddingHorizontal: 16, marginBottom: 16 },
  sectionTitle: { fontSize: 16, fontWeight: '600', color: '#374151', marginBottom: 10 },
  keywordRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  keyword: {
    backgroundColor: '#EDE9FE', paddingHorizontal: 12,
    paddingVertical: 6, borderRadius: 20,
  },
  keywordText: { color: '#7C3AED', fontSize: 13 },
  emptyText: { color: '#9CA3AF', textAlign: 'center', paddingVertical: 20 },
});
