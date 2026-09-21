import React, { useState } from 'react';
import {
  View, Text, TextInput, StyleSheet, TouchableOpacity,
  ScrollView, Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import dayjs from 'dayjs';
import { useSubsidyStore } from '../../store/useSubsidyStore';
import { SubsidyType } from '../../types';

const PRESET_KEYWORDS: Record<string, string[]> = {
  '에너지바우처': ['에너지바우처', '에너지지원'],
  '지역사랑상품권': ['지역사랑', '지역화폐', '상품권'],
  '복지포인트': ['복지포인트', '복지카드', '국민행복'],
  '재난지원금': ['재난지원', '지원금'],
  '청년지원금': ['청년지원', '청년수당'],
  '출산장려금': ['출산장려', '출산지원', '아동수당'],
  '의료급여': ['의료급여', '의료지원'],
};

const SUBSIDY_TYPES: { key: SubsidyType; label: string }[] = [
  { key: 'government', label: '정부 지원금' },
  { key: 'local', label: '지자체 지원금' },
  { key: 'welfare', label: '복지 포인트' },
  { key: 'custom', label: '직접 등록' },
];

export default function AddSubsidyScreen({ navigation }: any) {
  const { add } = useSubsidyStore();
  const [name, setName] = useState('');
  const [type, setType] = useState<SubsidyType>('government');
  const [totalAmount, setTotalAmount] = useState('');
  const [cardName, setCardName] = useState('');
  const [startDate, setStartDate] = useState(dayjs().format('YYYY-MM-DD'));
  const [endDate, setEndDate] = useState('');
  const [keywordsText, setKeywordsText] = useState('');
  const [selectedPreset, setSelectedPreset] = useState<string | null>(null);

  function applyPreset(preset: string) {
    setName(preset);
    setSelectedPreset(preset);
    setKeywordsText(PRESET_KEYWORDS[preset].join(', '));
  }

  async function handleSave() {
    if (!name.trim()) { Alert.alert('오류', '지원금 이름을 입력하세요'); return; }
    const amt = parseInt(totalAmount.replace(/,/g, ''), 10);
    if (!amt || isNaN(amt)) { Alert.alert('오류', '총 지원금액을 입력하세요'); return; }

    const keywords = keywordsText
      .split(/[,，\s]+/)
      .map((k) => k.trim())
      .filter(Boolean);

    await add({
      name: name.trim(),
      type,
      totalAmount: amt,
      remainingAmount: amt,
      cardName: cardName.trim(),
      startDate,
      endDate: endDate.trim(),
      isActive: true,
      keywords,
    });
    navigation.goBack();
  }

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={styles.title}>지원금 등록</Text>

        {/* 프리셋 */}
        <Text style={styles.label}>빠른 선택</Text>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.presetRow}>
          {Object.keys(PRESET_KEYWORDS).map((p) => (
            <TouchableOpacity
              key={p}
              style={[styles.presetBtn, selectedPreset === p && styles.presetBtnActive]}
              onPress={() => applyPreset(p)}
            >
              <Text style={[styles.presetText, selectedPreset === p && styles.presetTextActive]}>{p}</Text>
            </TouchableOpacity>
          ))}
        </ScrollView>

        <Text style={styles.label}>지원금 이름 *</Text>
        <TextInput style={styles.input} placeholder="예) 에너지바우처" value={name} onChangeText={setName} />

        <Text style={styles.label}>유형</Text>
        <View style={styles.typeGrid}>
          {SUBSIDY_TYPES.map((t) => (
            <TouchableOpacity
              key={t.key}
              style={[styles.typeBtn, type === t.key && styles.typeBtnActive]}
              onPress={() => setType(t.key)}
            >
              <Text style={[styles.typeText, type === t.key && styles.typeTextActive]}>{t.label}</Text>
            </TouchableOpacity>
          ))}
        </View>

        <Text style={styles.label}>총 지원금액 *</Text>
        <TextInput
          style={styles.input} keyboardType="numeric"
          placeholder="0" value={totalAmount} onChangeText={setTotalAmount}
        />

        <Text style={styles.label}>연결 카드/계좌 (선택)</Text>
        <TextInput style={styles.input} placeholder="예) KB국민카드, 카카오뱅크" value={cardName} onChangeText={setCardName} />

        <Text style={styles.label}>시작일</Text>
        <TextInput style={styles.input} placeholder="YYYY-MM-DD" value={startDate} onChangeText={setStartDate} />

        <Text style={styles.label}>만료일 (선택)</Text>
        <TextInput style={styles.input} placeholder="YYYY-MM-DD" value={endDate} onChangeText={setEndDate} />

        <Text style={styles.label}>자동 감지 키워드</Text>
        <Text style={styles.hint}>SMS/알림에서 이 단어가 포함되면 자동으로 이 지원금으로 분류됩니다</Text>
        <TextInput
          style={[styles.input, { height: 80 }]}
          multiline
          placeholder="예) 에너지바우처, 에너지지원 (쉼표로 구분)"
          value={keywordsText}
          onChangeText={setKeywordsText}
          textAlignVertical="top"
        />

        <TouchableOpacity style={styles.saveBtn} onPress={handleSave}>
          <Text style={styles.saveBtnText}>등록하기</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F9FAFB' },
  scroll: { padding: 20 },
  title: { fontSize: 22, fontWeight: '700', color: '#111827', marginBottom: 20 },
  label: { fontSize: 14, fontWeight: '600', color: '#374151', marginBottom: 6, marginTop: 16 },
  hint: { fontSize: 12, color: '#9CA3AF', marginBottom: 6 },
  input: {
    backgroundColor: '#fff', borderRadius: 10, borderWidth: 1,
    borderColor: '#E5E7EB', padding: 12, fontSize: 15,
  },
  presetRow: { marginBottom: 8 },
  presetBtn: {
    marginRight: 8, paddingHorizontal: 14, paddingVertical: 8,
    backgroundColor: '#F3F4F6', borderRadius: 20,
  },
  presetBtnActive: { backgroundColor: '#7C3AED' },
  presetText: { fontSize: 13, color: '#374151' },
  presetTextActive: { color: '#fff', fontWeight: '600' },
  typeGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  typeBtn: {
    paddingHorizontal: 14, paddingVertical: 8,
    backgroundColor: '#F3F4F6', borderRadius: 20,
  },
  typeBtnActive: { backgroundColor: '#7C3AED' },
  typeText: { fontSize: 13, color: '#374151' },
  typeTextActive: { color: '#fff', fontWeight: '600' },
  saveBtn: {
    marginTop: 30, backgroundColor: '#7C3AED',
    paddingVertical: 16, borderRadius: 14, alignItems: 'center',
  },
  saveBtnText: { color: '#fff', fontSize: 17, fontWeight: '700' },
});
