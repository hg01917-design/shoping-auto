import React, { useEffect, useState, useMemo } from 'react';
import { View, Text, ScrollView, StyleSheet, Dimensions, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import dayjs from 'dayjs';
import { useTransactionStore } from '../../store/useTransactionStore';

const CATEGORY_COLORS = [
  '#EF4444', '#F97316', '#EAB308', '#22C55E', '#06B6D4',
  '#8B5CF6', '#EC4899', '#64748B', '#78716C', '#6B7280',
];

const W = Dimensions.get('window').width;
const BAR_HEIGHT = 160;

export default function StatisticsScreen() {
  const { getMonthlyStats, getCategoryStats, currentMonth } = useTransactionStore();
  const [monthlyData, setMonthlyData] = useState<{ month: string; income: number; expense: number; subsidyUsed: number }[]>([]);
  const [catData, setCatData] = useState<{ category: string; total: number }[]>([]);
  const [year, setYear] = useState(dayjs().format('YYYY'));

  useEffect(() => {
    getMonthlyStats(year).then(setMonthlyData);
    getCategoryStats(currentMonth).then(setCatData);
  }, [year, currentMonth]);

  const maxExpense = Math.max(...monthlyData.map((d) => d.expense + d.subsidyUsed), 1);
  const totalCat = catData.reduce((acc, d) => acc + d.total, 0);

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView showsVerticalScrollIndicator={false}>
        {/* 연도 선택 */}
        <View style={styles.yearRow}>
          <TouchableOpacity onPress={() => setYear((y) => String(parseInt(y) - 1))}>
            <Text style={styles.arrow}>‹</Text>
          </TouchableOpacity>
          <Text style={styles.yearText}>{year}년</Text>
          <TouchableOpacity onPress={() => setYear((y) => String(parseInt(y) + 1))}>
            <Text style={styles.arrow}>›</Text>
          </TouchableOpacity>
        </View>

        {/* 월별 지출 바차트 */}
        <View style={styles.card}>
          <Text style={styles.cardTitle}>월별 지출 현황</Text>
          <View style={styles.barChart}>
            {Array.from({ length: 12 }, (_, i) => {
              const m = `${year}-${String(i + 1).padStart(2, '0')}`;
              const d = monthlyData.find((r) => r.month === m);
              const expense = d?.expense ?? 0;
              const subsidy = d?.subsidyUsed ?? 0;
              const total = expense + subsidy;
              const barH = maxExpense > 0 ? Math.round((total / maxExpense) * BAR_HEIGHT) : 0;
              const subsidyH = maxExpense > 0 ? Math.round((subsidy / maxExpense) * BAR_HEIGHT) : 0;

              return (
                <View key={m} style={styles.barCol}>
                  <View style={[styles.barStack, { height: BAR_HEIGHT }]}>
                    {barH > 0 && (
                      <View style={{ position: 'absolute', bottom: 0, width: '100%', height: barH }}>
                        <View style={{ flex: 1, backgroundColor: '#BFDBFE' }} />
                        {subsidyH > 0 && (
                          <View style={{ height: subsidyH, backgroundColor: '#7C3AED', position: 'absolute', bottom: 0, width: '100%' }} />
                        )}
                      </View>
                    )}
                  </View>
                  <Text style={styles.barLabel}>{i + 1}월</Text>
                </View>
              );
            })}
          </View>
          <View style={styles.legend}>
            <View style={styles.legendItem}>
              <View style={[styles.legendDot, { backgroundColor: '#BFDBFE' }]} />
              <Text style={styles.legendText}>일반 지출</Text>
            </View>
            <View style={styles.legendItem}>
              <View style={[styles.legendDot, { backgroundColor: '#7C3AED' }]} />
              <Text style={styles.legendText}>지원금 사용</Text>
            </View>
          </View>
        </View>

        {/* 카테고리별 지출 */}
        <View style={styles.card}>
          <Text style={styles.cardTitle}>{dayjs(currentMonth).format('M월')} 카테고리별 지출</Text>
          {catData.length === 0 ? (
            <Text style={styles.emptyText}>데이터가 없습니다</Text>
          ) : (
            catData.slice(0, 8).map((d, i) => {
              const pct = totalCat > 0 ? Math.round((d.total / totalCat) * 100) : 0;
              const color = CATEGORY_COLORS[i % CATEGORY_COLORS.length];
              return (
                <View key={d.category} style={styles.catRow}>
                  <View style={[styles.catDot, { backgroundColor: color }]} />
                  <Text style={styles.catName}>{d.category}</Text>
                  <View style={styles.catBarBg}>
                    <View style={[styles.catBarFill, { width: `${pct}%` as any, backgroundColor: color }]} />
                  </View>
                  <Text style={styles.catPct}>{pct}%</Text>
                  <Text style={styles.catAmount}>{d.total.toLocaleString()}원</Text>
                </View>
              );
            })
          )}
        </View>

        {/* 지원금 활용도 요약 */}
        {monthlyData.some((d) => d.subsidyUsed > 0) && (
          <View style={styles.card}>
            <Text style={styles.cardTitle}>지원금 활용 현황</Text>
            {monthlyData.filter((d) => d.subsidyUsed > 0).map((d) => (
              <View key={d.month} style={styles.subsidyRow}>
                <Text style={styles.subsidyMonth}>{dayjs(d.month).format('M월')}</Text>
                <Text style={styles.subsidyAmount}>{d.subsidyUsed.toLocaleString()}원</Text>
              </View>
            ))}
          </View>
        )}
        <View style={{ height: 40 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F9FAFB' },
  yearRow: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center', paddingVertical: 16,
  },
  arrow: { fontSize: 28, color: '#2563EB', paddingHorizontal: 20 },
  yearText: { fontSize: 20, fontWeight: '700', color: '#111827' },
  card: {
    margin: 16, marginTop: 0, padding: 16,
    backgroundColor: '#fff', borderRadius: 16,
    elevation: 2, shadowColor: '#000', shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.08, shadowRadius: 4, marginBottom: 16,
  },
  cardTitle: { fontSize: 16, fontWeight: '700', color: '#111827', marginBottom: 16 },
  barChart: { flexDirection: 'row', alignItems: 'flex-end', gap: 4 },
  barCol: { flex: 1, alignItems: 'center' },
  barStack: { width: '80%', justifyContent: 'flex-end', overflow: 'hidden' },
  barLabel: { fontSize: 10, color: '#9CA3AF', marginTop: 4 },
  legend: { flexDirection: 'row', gap: 16, marginTop: 12 },
  legendItem: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  legendDot: { width: 10, height: 10, borderRadius: 5 },
  legendText: { fontSize: 12, color: '#6B7280' },
  emptyText: { color: '#9CA3AF', textAlign: 'center', paddingVertical: 20 },
  catRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 10, gap: 6 },
  catDot: { width: 10, height: 10, borderRadius: 5 },
  catName: { width: 70, fontSize: 13, color: '#374151' },
  catBarBg: { flex: 1, height: 6, backgroundColor: '#F3F4F6', borderRadius: 3 },
  catBarFill: { height: 6, borderRadius: 3 },
  catPct: { width: 32, fontSize: 12, color: '#9CA3AF', textAlign: 'right' },
  catAmount: { width: 70, fontSize: 12, color: '#374151', textAlign: 'right' },
  subsidyRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: '#F3F4F6' },
  subsidyMonth: { fontSize: 14, color: '#374151' },
  subsidyAmount: { fontSize: 14, fontWeight: '600', color: '#7C3AED' },
});
