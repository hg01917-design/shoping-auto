import React, { useEffect, useMemo, useState } from 'react';
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity,
  Modal, TextInput, Platform, Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import * as Clipboard from 'expo-clipboard';
import dayjs from 'dayjs';
import { useTransactionStore } from '../../store/useTransactionStore';
import { useSubsidyStore } from '../../store/useSubsidyStore';
import { parsePaymentText } from '../../services/smsParser';
import { TransactionItem } from '../../components/TransactionItem';
import { SubsidyBadge } from '../../components/SubsidyBadge';

export default function DashboardScreen() {
  const { transactions, loadTransactions, addFromParsed, currentMonth } = useTransactionStore();
  const { subsidies, load: loadSubsidies, findMatchingSubsidy, deduct } = useSubsidyStore();
  const [pasteModalVisible, setPasteModalVisible] = useState(false);
  const [pasteText, setPasteText] = useState('');

  useEffect(() => {
    loadTransactions(currentMonth);
    loadSubsidies();
  }, [currentMonth]);

  const { totalIncome, totalExpense } = useMemo(() => {
    let totalIncome = 0;
    let totalExpense = 0;
    for (const t of transactions) {
      if (t.type === 'income') totalIncome += t.amount;
      else totalExpense += t.amount;
    }
    return { totalIncome, totalExpense };
  }, [transactions]);

  const activeSubsidies = subsidies.filter((s) => s.isActive && s.remainingAmount > 0);
  const recentTransactions = transactions.slice(0, 7);

  async function handlePasteSMS() {
    const text = pasteText.trim();
    if (!text) return;

    const parsed = parsePaymentText(text);
    if (!parsed) {
      Alert.alert('파싱 실패', '결제 내역을 인식하지 못했습니다. 카드/은행 SMS 또는 카카오페이 알림 내용을 붙여넣어 주세요.');
      return;
    }

    let subsidyId: number | undefined;
    if (parsed.isSubsidy && parsed.subsidyKeyword) {
      const matched = findMatchingSubsidy(parsed.subsidyKeyword, parsed.cardName);
      if (matched) {
        subsidyId = matched.id;
        await deduct(matched.id, parsed.amount);
      }
    }

    await addFromParsed({ ...parsed, source: 'paste' } as any, subsidyId);
    setPasteModalVisible(false);
    setPasteText('');
  }

  async function handleClipboardPaste() {
    const text = await Clipboard.getStringAsync();
    setPasteText(text);
  }

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView showsVerticalScrollIndicator={false}>
        {/* 헤더 */}
        <View style={styles.header}>
          <Text style={styles.monthText}>{dayjs(currentMonth).format('YYYY년 M월')}</Text>
          <Text style={styles.appTitle}>가계부</Text>
        </View>

        {/* 수입/지출 요약 */}
        <View style={styles.summaryCard}>
          <View style={styles.summaryRow}>
            <View style={styles.summaryItem}>
              <Text style={styles.summaryLabel}>수입</Text>
              <Text style={[styles.summaryAmount, { color: '#16A34A' }]}>
                +{totalIncome.toLocaleString()}원
              </Text>
            </View>
            <View style={styles.summaryDivider} />
            <View style={styles.summaryItem}>
              <Text style={styles.summaryLabel}>지출</Text>
              <Text style={[styles.summaryAmount, { color: '#DC2626' }]}>
                -{totalExpense.toLocaleString()}원
              </Text>
            </View>
          </View>
          <View style={styles.balanceRow}>
            <Text style={styles.balanceLabel}>잔여</Text>
            <Text style={styles.balanceAmount}>
              {(totalIncome - totalExpense).toLocaleString()}원
            </Text>
          </View>
        </View>

        {/* 지원금 현황 */}
        {activeSubsidies.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>🎁 지원금 현황</Text>
            <ScrollView horizontal showsHorizontalScrollIndicator={false}>
              {activeSubsidies.map((s) => (
                <SubsidyBadge key={s.id} subsidy={s} />
              ))}
            </ScrollView>
          </View>
        )}

        {/* 최근 거래 */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>최근 거래</Text>
          {recentTransactions.length === 0 ? (
            <Text style={styles.emptyText}>거래 내역이 없습니다</Text>
          ) : (
            recentTransactions.map((t) => (
              <TransactionItem key={t.id} transaction={t} />
            ))
          )}
        </View>
      </ScrollView>

      {/* FAB: SMS/알림 붙여넣기 */}
      <TouchableOpacity
        style={styles.fab}
        onPress={() => setPasteModalVisible(true)}
      >
        <Text style={styles.fabText}>+</Text>
      </TouchableOpacity>

      {/* SMS 붙여넣기 모달 */}
      <Modal visible={pasteModalVisible} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>결제 내역 입력</Text>
            <Text style={styles.modalSubtitle}>
              SMS, 카카오페이, 카드사 알림 내용을 붙여넣어 주세요
            </Text>
            <TextInput
              style={styles.pasteInput}
              multiline
              numberOfLines={5}
              placeholder="예) [KB국민카드] 5,000원 사용 스타벅스 잔액 100,000원"
              value={pasteText}
              onChangeText={setPasteText}
            />
            <TouchableOpacity style={styles.clipboardBtn} onPress={handleClipboardPaste}>
              <Text style={styles.clipboardBtnText}>📋 클립보드에서 가져오기</Text>
            </TouchableOpacity>
            <View style={styles.modalActions}>
              <TouchableOpacity
                style={[styles.modalBtn, styles.cancelBtn]}
                onPress={() => { setPasteModalVisible(false); setPasteText(''); }}
              >
                <Text style={styles.cancelBtnText}>취소</Text>
              </TouchableOpacity>
              <TouchableOpacity style={[styles.modalBtn, styles.confirmBtn]} onPress={handlePasteSMS}>
                <Text style={styles.confirmBtnText}>등록</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F9FAFB' },
  header: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingHorizontal: 20, paddingTop: 16, paddingBottom: 8,
  },
  monthText: { fontSize: 16, color: '#6B7280' },
  appTitle: { fontSize: 20, fontWeight: '700', color: '#111827' },
  summaryCard: {
    marginHorizontal: 16, marginBottom: 16,
    backgroundColor: '#2563EB', borderRadius: 16, padding: 20,
  },
  summaryRow: { flexDirection: 'row', justifyContent: 'space-around' },
  summaryItem: { alignItems: 'center' },
  summaryLabel: { color: '#BFDBFE', fontSize: 13, marginBottom: 4 },
  summaryAmount: { fontSize: 20, fontWeight: '700', color: '#fff' },
  summaryDivider: { width: 1, backgroundColor: '#3B82F6' },
  balanceRow: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    marginTop: 16, paddingTop: 16, borderTopWidth: 1, borderTopColor: '#3B82F6',
  },
  balanceLabel: { color: '#BFDBFE', fontSize: 14 },
  balanceAmount: { color: '#fff', fontSize: 18, fontWeight: '700' },
  section: { paddingHorizontal: 16, marginBottom: 16 },
  sectionTitle: { fontSize: 16, fontWeight: '600', color: '#374151', marginBottom: 10 },
  emptyText: { color: '#9CA3AF', textAlign: 'center', paddingVertical: 20 },
  fab: {
    position: 'absolute', right: 20, bottom: 24,
    width: 56, height: 56, borderRadius: 28,
    backgroundColor: '#2563EB', alignItems: 'center', justifyContent: 'center',
    elevation: 6, shadowColor: '#000', shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.3, shadowRadius: 4,
  },
  fabText: { color: '#fff', fontSize: 28, lineHeight: 32 },
  modalOverlay: {
    flex: 1, backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'flex-end',
  },
  modalCard: {
    backgroundColor: '#fff', borderTopLeftRadius: 24, borderTopRightRadius: 24,
    padding: 24, paddingBottom: 40,
  },
  modalTitle: { fontSize: 18, fontWeight: '700', color: '#111827', marginBottom: 6 },
  modalSubtitle: { fontSize: 13, color: '#6B7280', marginBottom: 16 },
  pasteInput: {
    borderWidth: 1, borderColor: '#D1D5DB', borderRadius: 12,
    padding: 12, fontSize: 14, color: '#111827', minHeight: 100,
    textAlignVertical: 'top',
  },
  clipboardBtn: {
    marginTop: 8, padding: 10, alignItems: 'center',
    backgroundColor: '#F3F4F6', borderRadius: 8,
  },
  clipboardBtnText: { color: '#374151', fontSize: 14 },
  modalActions: { flexDirection: 'row', gap: 12, marginTop: 16 },
  modalBtn: { flex: 1, paddingVertical: 14, borderRadius: 12, alignItems: 'center' },
  cancelBtn: { backgroundColor: '#F3F4F6' },
  cancelBtnText: { color: '#374151', fontSize: 15, fontWeight: '600' },
  confirmBtn: { backgroundColor: '#2563EB' },
  confirmBtnText: { color: '#fff', fontSize: 15, fontWeight: '600' },
});
