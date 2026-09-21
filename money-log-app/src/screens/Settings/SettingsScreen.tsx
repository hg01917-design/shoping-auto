import React, { useEffect, useState } from 'react';
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity,
  Switch, Alert, Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import {
  isNotificationServiceEnabled,
  openNotificationSettings,
} from '../../services/notificationListener';

export default function SettingsScreen() {
  const [notifEnabled, setNotifEnabled] = useState(false);

  useEffect(() => {
    if (Platform.OS === 'android') {
      setNotifEnabled(isNotificationServiceEnabled());
    }
  }, []);

  function handleNotifToggle() {
    if (!notifEnabled) {
      Alert.alert(
        '알림 접근 권한',
        '카드사 앱과 카카오페이 알림을 자동으로 수집하려면\n"알림 접근 허용" 설정이 필요합니다.\n\n설정 화면으로 이동할까요?',
        [
          { text: '취소', style: 'cancel' },
          { text: '설정으로 이동', onPress: openNotificationSettings },
        ]
      );
    }
  }

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView>
        <Text style={styles.pageTitle}>설정</Text>

        {/* 알림 수집 */}
        {Platform.OS === 'android' && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>자동 수집</Text>
            <View style={styles.row}>
              <View style={styles.rowInfo}>
                <Text style={styles.rowTitle}>카드/카카오페이 알림 수집</Text>
                <Text style={styles.rowDesc}>
                  카드사 앱, 카카오페이, 카카오뱅크 알림을{'\n'}
                  자동으로 가계부에 기록합니다
                </Text>
              </View>
              <Switch
                value={notifEnabled}
                onValueChange={handleNotifToggle}
                trackColor={{ true: '#2563EB' }}
              />
            </View>

            <View style={styles.infoBox}>
              <Text style={styles.infoText}>
                📌 지원되는 앱{'\n'}
                KB국민카드 · 신한SOL · 삼성Pay · 현대카드{'\n'}
                롯데카드 · 하나은행 · 우리WON · 토스{'\n'}
                카카오페이 · 카카오뱅크
              </Text>
            </View>
          </View>
        )}

        {/* iOS 안내 */}
        {Platform.OS === 'ios' && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>iOS 수집 방법</Text>
            <View style={styles.infoBox}>
              <Text style={styles.infoText}>
                📱 iOS는 보안 정책상 다른 앱의 SMS를 직접 읽을 수 없습니다.{'\n\n'}
                대신 카드/은행 문자를 복사한 후{'\n'}
                홈 화면 하단 [+] 버튼 → "결제 내역 입력"에서{'\n'}
                붙여넣기 파싱 기능을 사용하세요.
              </Text>
            </View>
          </View>
        )}

        {/* 앱 정보 */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>앱 정보</Text>
          <View style={styles.infoBox}>
            <Text style={styles.infoText}>
              가계부 v1.0.0{'\n\n'}
              지원하는 SMS/알림 형식:{'\n'}
              · 국민/신한/삼성/현대/롯데/하나/BC/농협/우리 카드{'\n'}
              · 국민/신한/하나/우리/농협/기업 은행{'\n'}
              · 카카오페이 / 카카오뱅크{'\n'}
              · 지원금 (에너지바우처, 지역화폐 등){'\n\n'}
              데이터는 기기 내부에만 저장됩니다.
            </Text>
          </View>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F9FAFB' },
  pageTitle: { fontSize: 24, fontWeight: '700', color: '#111827', margin: 20 },
  section: { marginBottom: 24, paddingHorizontal: 16 },
  sectionTitle: { fontSize: 14, fontWeight: '600', color: '#9CA3AF', marginBottom: 12, textTransform: 'uppercase' },
  row: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    backgroundColor: '#fff', padding: 16, borderRadius: 12,
    marginBottom: 8, elevation: 1,
    shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.05, shadowRadius: 2,
  },
  rowInfo: { flex: 1, marginRight: 12 },
  rowTitle: { fontSize: 15, fontWeight: '600', color: '#111827' },
  rowDesc: { fontSize: 12, color: '#9CA3AF', marginTop: 4, lineHeight: 18 },
  infoBox: {
    backgroundColor: '#EFF6FF', borderRadius: 12, padding: 16,
    borderLeftWidth: 3, borderLeftColor: '#2563EB',
  },
  infoText: { fontSize: 13, color: '#1E40AF', lineHeight: 22 },
});
