import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Subsidy } from '../types';

interface Props {
  subsidy: Subsidy;
}

export function SubsidyBadge({ subsidy: s }: Props) {
  const usedPct = s.totalAmount > 0
    ? Math.round(((s.totalAmount - s.remainingAmount) / s.totalAmount) * 100)
    : 0;

  return (
    <View style={styles.card}>
      <Text style={styles.name} numberOfLines={1}>{s.name}</Text>
      <Text style={styles.remaining}>{s.remainingAmount.toLocaleString()}원</Text>
      <View style={styles.barBg}>
        <View style={[styles.barFill, { width: `${usedPct}%` as any }]} />
      </View>
      <Text style={styles.pct}>{usedPct}% 사용</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    width: 140, marginRight: 10,
    backgroundColor: '#EDE9FE', borderRadius: 12, padding: 12,
  },
  name: { fontSize: 13, fontWeight: '600', color: '#5B21B6', marginBottom: 4 },
  remaining: { fontSize: 16, fontWeight: '700', color: '#3730A3', marginBottom: 8 },
  barBg: { height: 4, backgroundColor: '#C4B5FD', borderRadius: 2, marginBottom: 4 },
  barFill: { height: 4, backgroundColor: '#7C3AED', borderRadius: 2 },
  pct: { fontSize: 11, color: '#7C3AED' },
});
