import React, { useState } from 'react';
import {
  View, Text, TextInput, StyleSheet, TouchableOpacity,
  ScrollView, Alert, Switch,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import dayjs from 'dayjs';
import { useTransactionStore } from '../../store/useTransactionStore';
import { useSubsidyStore } from '../../store/useSubsidyStore';
import { TransactionType } from '../../types';

const EXPENSE_CATEGORIES = [
  '식비', '교통', '쇼핑', '의료', '문화/여가',
  '카페', '마트/편의점', '공과금', '주거', '기타',
];
const INCOME_CATEGORIES = ['급여', '이체', '지원금', '기타수입'];

export default function AddTransactionScreen({ navigation }: any) {
  const { addManual } = useTransactionStore();
  const { subsidies } = useSubsidyStore();
  const [type, setType] = useState<TransactionType>('expense');
  const [amount, setAmount] = useState('');
  const [merchant, setMerchant] = useState('');
  const [cardName, setCardName] = useState('');
  const [category, setCategory] = useState('기타');
  const [note, setNote] = useState('');
  const [isSubsidy, setIsSubsidy] = useState(false);
  const [subsidyId, setSubsidyId] = useState<number | null>(null);
  const [date, setDate] = useState(dayjs().format('YYYY-MM-DD'));

  const categories = type === 'expense' ? EXPENSE_CATEGORIES : INCOME_CATEGORIES;

  async function handleSave() {
    const amt = parseInt(amount.replace(/,/g, ''), 10);
    if (!amt || isNaN(amt)) {
      Alert.alert('오류', '금액을 입력해주세요');
      return;
    }

    await addManual({
      amount: amt,
      type,
      category,
      merchant,
      cardName,
      note,
      date: `${date} ${dayjs().format('HH:mm:ss')}`,
      source: 'manual',
      isSubsidy,
      subsidyId: isSubsidy ? subsidyId : null,
      rawText: '',
    });
    navigation.goBack();
  }

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={styles.title}>거래 직접 입력</Text>

        {/* 수입/지출 토글 */}
        <View style={styles.typeRow}>
          {(['expense', 'income'] as TransactionType[]).map((t) => (
            <TouchableOpacity
              key={t}
              style={[styles.typeBtn, type === t && styles.typeBtnActive]}
              onPress={() => { setType(t); setCategory(t === 'expense' ? '기타' : '기타수입'); }}
            >
              <Text style={[styles.typeBtnText, type === t && styles.typeBtnTextActive]}>
                {t === 'expense' ? '지출' : '수입'}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        <Text style={styles.label}>금액</Text>
        <TextInput
          style={styles.input}
          keyboardType="numeric"
          placeholder="0"
          value={amount}
          onChangeText={setAmount}
        />

        <Text style={styles.label}>가맹점/내용</Text>
        <TextInput style={styles.input} placeholder="예) 스타벅스" value={merchant} onChangeText={setMerchant} />

        <Text style={styles.label}>카드/계좌</Text>
        <TextInput style={styles.input} placeholder="예) KB국민카드" value={cardName} onChangeText={setCardName} />

        <Text style={styles.label}>날짜</Text>
        <TextInput style={styles.input} placeholder="YYYY-MM-DD" value={date} onChangeText={setDate} />

        <Text style={styles.label}>카테고리</Text>
        <View style={styles.catGrid}>
          {categories.map((c) => (
            <TouchableOpacity
              key={c}
              style={[styles.catBtn, category === c && styles.catBtnActive]}
              onPress={() => setCategory(c)}
            >
              <Text style={[styles.catText, category === c && styles.catTextActive]}>{c}</Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* 지원금 여부 */}
        <View style={styles.switchRow}>
          <Text style={styles.label}>지원금 사용 여부</Text>
          <Switch value={isSubsidy} onValueChange={setIsSubsidy} trackColor={{ true: '#7C3AED' }} />
        </View>

        {isSubsidy && subsidies.filter((s) => s.isActive).length > 0 && (
          <>
            <Text style={styles.label}>연결할 지원금</Text>
            {subsidies.filter((s) => s.isActive).map((s) => (
              <TouchableOpacity
                key={s.id}
                style={[styles.subsidyOption, subsidyId === s.id && styles.subsidyOptionActive]}
                onPress={() => setSubsidyId(s.id)}
              >
                <Text style={styles.subsidyOptionText}>
                  {s.name} (잔액 {s.remainingAmount.toLocaleString()}원)
                </Text>
              </TouchableOpacity>
            ))}
          </>
        )}

        <Text style={styles.label}>메모</Text>
        <TextInput
          style={[styles.input, { height: 80 }]}
          multiline
          placeholder="메모 (선택)"
          value={note}
          onChangeText={setNote}
          textAlignVertical="top"
        />

        <TouchableOpacity style={styles.saveBtn} onPress={handleSave}>
          <Text style={styles.saveBtnText}>저장</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F9FAFB' },
  scroll: { padding: 20 },
  title: { fontSize: 22, fontWeight: '700', color: '#111827', marginBottom: 20 },
  typeRow: { flexDirection: 'row', gap: 12, marginBottom: 20 },
  typeBtn: {
    flex: 1, paddingVertical: 12, borderRadius: 10,
    backgroundColor: '#F3F4F6', alignItems: 'center',
  },
  typeBtnActive: { backgroundColor: '#2563EB' },
  typeBtnText: { fontSize: 15, fontWeight: '600', color: '#6B7280' },
  typeBtnTextActive: { color: '#fff' },
  label: { fontSize: 14, fontWeight: '600', color: '#374151', marginBottom: 6, marginTop: 16 },
  input: {
    backgroundColor: '#fff', borderRadius: 10, borderWidth: 1,
    borderColor: '#E5E7EB', padding: 12, fontSize: 15,
  },
  catGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  catBtn: {
    paddingHorizontal: 14, paddingVertical: 8,
    backgroundColor: '#F3F4F6', borderRadius: 20,
  },
  catBtnActive: { backgroundColor: '#2563EB' },
  catText: { fontSize: 13, color: '#374151' },
  catTextActive: { color: '#fff', fontWeight: '600' },
  switchRow: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 16,
  },
  subsidyOption: {
    padding: 12, borderRadius: 10, borderWidth: 1,
    borderColor: '#E5E7EB', marginBottom: 8, backgroundColor: '#fff',
  },
  subsidyOptionActive: { borderColor: '#7C3AED', backgroundColor: '#EDE9FE' },
  subsidyOptionText: { fontSize: 14, color: '#374151' },
  saveBtn: {
    marginTop: 30, backgroundColor: '#2563EB',
    paddingVertical: 16, borderRadius: 14, alignItems: 'center',
  },
  saveBtnText: { color: '#fff', fontSize: 17, fontWeight: '700' },
});
