import React, { useEffect } from 'react';
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity, Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useNavigation } from '@react-navigation/native';
import dayjs from 'dayjs';
import { useSubsidyStore } from '../../store/useSubsidyStore';
import { Subsidy } from '../../types';

export default function SubsidyScreen() {
  const { subsidies, load, remove } = useSubsidyStore();
  const navigation = useNavigation<any>();

  useEffect(() => { load(); }, []);

  const active = subsidies.filter((s) => s.isActive);
  const inactive = subsidies.filter((s) => !s.isActive);

  function handleDelete(s: Subsidy) {
    Alert.alert('삭제', `"${s.name}" 지원금을 삭제할까요?`, [
      { text: '취소', style: 'cancel' },
      { text: '삭제', style: 'destructive', onPress: () => remove(s.id) },
    ]);
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>🎁 지원금 관리</Text>
        <TouchableOpacity
          style={styles.addBtn}
          onPress={() => navigation.navigate('AddSubsidy')}
        >
          <Text style={styles.addBtnText}>+ 추가</Text>
        </TouchableOpacity>
      </View>

      <ScrollView contentContainerStyle={styles.scroll}>
        {active.length === 0 && inactive.length === 0 && (
          <View style={styles.empty}>
            <Text style={styles.emptyIcon}>🎁</Text>
            <Text style={styles.emptyTitle}>등록된 지원금이 없습니다</Text>
            <Text style={styles.emptyDesc}>
              에너지바우처, 지역화폐, 복지포인트 등{'\n'}
              카드에 있는 지원금을 등록하면{'\n'}
              잔액과 사용 내역을 분리해 관리할 수 있습니다
            </Text>
          </View>
        )}

        {active.map((s) => <SubsidyCard key={s.id} subsidy={s} onDelete={handleDelete} onPress={() => navigation.navigate('SubsidyDetail', { id: s.id })} />)}

        {inactive.length > 0 && (
          <>
            <Text style={styles.sectionLabel}>만료/비활성</Text>
            {inactive.map((s) => <SubsidyCard key={s.id} subsidy={s} inactive onDelete={handleDelete} onPress={() => navigation.navigate('SubsidyDetail', { id: s.id })} />)}
          </>
        )}
        <View style={{ height: 40 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

function SubsidyCard({
  subsidy: s, inactive = false, onDelete, onPress,
}: { subsidy: Subsidy; inactive?: boolean; onDelete: (s: Subsidy) => void; onPress: () => void }) {
  const usedPct = s.totalAmount > 0
    ? Math.round(((s.totalAmount - s.remainingAmount) / s.totalAmount) * 100)
    : 0;
  const isExpiring = s.endDate && dayjs(s.endDate).diff(dayjs(), 'day') <= 7;

  return (
    <TouchableOpacity onPress={onPress} onLongPress={() => onDelete(s)} style={[styles.card, inactive && styles.cardInactive]}>
      <View style={styles.cardHeader}>
        <View>
          <Text style={styles.cardName}>{s.name}</Text>
          {s.cardName ? <Text style={styles.cardSub}>{s.cardName}</Text> : null}
        </View>
        {isExpiring && <Text style={styles.expiringBadge}>⚠️ 곧 만료</Text>}
      </View>

      <View style={styles.amountRow}>
        <View>
          <Text style={styles.amountLabel}>잔여</Text>
          <Text style={styles.remainingAmount}>{s.remainingAmount.toLocaleString()}원</Text>
        </View>
        <View style={{ alignItems: 'flex-end' }}>
          <Text style={styles.amountLabel}>총액</Text>
          <Text style={styles.totalAmount}>{s.totalAmount.toLocaleString()}원</Text>
        </View>
      </View>

      <View style={styles.progressBg}>
        <View style={[styles.progressFill, { width: `${usedPct}%` as any }]} />
      </View>
      <View style={styles.progressLabels}>
        <Text style={styles.progressText}>사용 {(s.totalAmount - s.remainingAmount).toLocaleString()}원</Text>
        <Text style={styles.progressText}>{usedPct}%</Text>
      </View>

      {s.endDate && (
        <Text style={[styles.expireText, isExpiring && styles.expireTextRed]}>
          만료일: {dayjs(s.endDate).format('YYYY.MM.DD')}
        </Text>
      )}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F9FAFB' },
  header: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingHorizontal: 20, paddingVertical: 16,
  },
  title: { fontSize: 22, fontWeight: '700', color: '#111827' },
  addBtn: {
    backgroundColor: '#7C3AED', paddingHorizontal: 16,
    paddingVertical: 8, borderRadius: 20,
  },
  addBtnText: { color: '#fff', fontWeight: '600', fontSize: 14 },
  scroll: { padding: 16 },
  sectionLabel: { fontSize: 14, color: '#9CA3AF', marginTop: 16, marginBottom: 8 },
  empty: { alignItems: 'center', paddingTop: 60 },
  emptyIcon: { fontSize: 48, marginBottom: 16 },
  emptyTitle: { fontSize: 18, fontWeight: '600', color: '#374151', marginBottom: 8 },
  emptyDesc: { fontSize: 14, color: '#9CA3AF', textAlign: 'center', lineHeight: 22 },
  card: {
    backgroundColor: '#fff', borderRadius: 16, padding: 16,
    marginBottom: 12, elevation: 2,
    shadowColor: '#000', shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.08, shadowRadius: 4,
  },
  cardInactive: { opacity: 0.6 },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 12 },
  cardName: { fontSize: 16, fontWeight: '700', color: '#111827' },
  cardSub: { fontSize: 12, color: '#9CA3AF', marginTop: 2 },
  expiringBadge: { fontSize: 12, color: '#DC2626', backgroundColor: '#FEE2E2', paddingHorizontal: 8, paddingVertical: 4, borderRadius: 8 },
  amountRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 12 },
  amountLabel: { fontSize: 11, color: '#9CA3AF', marginBottom: 2 },
  remainingAmount: { fontSize: 22, fontWeight: '700', color: '#7C3AED' },
  totalAmount: { fontSize: 14, color: '#6B7280' },
  progressBg: { height: 6, backgroundColor: '#F3F4F6', borderRadius: 3, marginBottom: 4 },
  progressFill: { height: 6, backgroundColor: '#7C3AED', borderRadius: 3 },
  progressLabels: { flexDirection: 'row', justifyContent: 'space-between' },
  progressText: { fontSize: 12, color: '#9CA3AF' },
  expireText: { fontSize: 12, color: '#9CA3AF', marginTop: 8 },
  expireTextRed: { color: '#DC2626', fontWeight: '500' },
});
