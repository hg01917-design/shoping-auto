import React, { useEffect, useRef } from 'react';
import { Platform, Alert, AppState } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { StatusBar } from 'expo-status-bar';

import DashboardScreen from './src/screens/Dashboard/DashboardScreen';
import TransactionListScreen from './src/screens/Transactions/TransactionListScreen';
import AddTransactionScreen from './src/screens/Transactions/AddTransactionScreen';
import SubsidyScreen from './src/screens/Subsidy/SubsidyScreen';
import AddSubsidyScreen from './src/screens/Subsidy/AddSubsidyScreen';
import SubsidyDetailScreen from './src/screens/Subsidy/SubsidyDetailScreen';
import StatisticsScreen from './src/screens/Statistics/StatisticsScreen';
import SettingsScreen from './src/screens/Settings/SettingsScreen';

import { useTransactionStore } from './src/store/useTransactionStore';
import { useSubsidyStore } from './src/store/useSubsidyStore';
import { startNotificationListener } from './src/services/notificationListener';
import { ParsedPayment } from './src/types';
import { getDb } from './src/services/database';

const Tab = createBottomTabNavigator();
const Stack = createNativeStackNavigator();

const TAB_ICONS: Record<string, string> = {
  홈: '🏠',
  거래내역: '📋',
  지원금: '🎁',
  통계: '📊',
  설정: '⚙️',
};

function TransactionStack() {
  return (
    <Stack.Navigator>
      <Stack.Screen name="TransactionList" component={TransactionListScreen} options={{ title: '거래 내역' }} />
      <Stack.Screen name="AddTransaction" component={AddTransactionScreen} options={{ title: '직접 입력' }} />
    </Stack.Navigator>
  );
}

function SubsidyStack() {
  return (
    <Stack.Navigator>
      <Stack.Screen name="SubsidyList" component={SubsidyScreen} options={{ headerShown: false }} />
      <Stack.Screen name="AddSubsidy" component={AddSubsidyScreen} options={{ title: '지원금 등록' }} />
      <Stack.Screen name="SubsidyDetail" component={SubsidyDetailScreen} options={{ title: '지원금 상세' }} />
    </Stack.Navigator>
  );
}

export default function App() {
  const { addFromParsed } = useTransactionStore();
  const { load: loadSubsidies, findMatchingSubsidy, deduct } = useSubsidyStore();

  // DB 초기화 및 지원금 로드
  useEffect(() => {
    getDb().then(() => loadSubsidies());
  }, []);

  // Android 알림 리스너 시작
  useEffect(() => {
    if (Platform.OS !== 'android') return;

    async function handlePayment(parsed: ParsedPayment) {
      let subsidyId: number | undefined;
      if (parsed.isSubsidy && parsed.subsidyKeyword) {
        const matched = findMatchingSubsidy(parsed.subsidyKeyword, parsed.cardName);
        if (matched) {
          subsidyId = matched.id;
          await deduct(matched.id, parsed.amount);
        }
      }
      await addFromParsed(parsed, subsidyId);
    }

    const stop = startNotificationListener(handlePayment);
    return stop;
  }, []);

  return (
    <SafeAreaProvider>
      <StatusBar style="auto" />
      <NavigationContainer>
        <Tab.Navigator
          screenOptions={({ route }) => ({
            tabBarIcon: ({ focused }) => {
              const icon = TAB_ICONS[route.name] ?? '•';
              return (
                // emoji icon 표시
                React.createElement('Text' as any, {
                  style: { fontSize: focused ? 24 : 20 },
                }, icon)
              );
            },
            tabBarActiveTintColor: '#2563EB',
            tabBarInactiveTintColor: '#9CA3AF',
            headerShown: false,
          })}
        >
          <Tab.Screen name="홈" component={DashboardScreen} />
          <Tab.Screen name="거래내역" component={TransactionStack} />
          <Tab.Screen name="지원금" component={SubsidyStack} />
          <Tab.Screen name="통계" component={StatisticsScreen} />
          <Tab.Screen name="설정" component={SettingsScreen} />
        </Tab.Navigator>
      </NavigationContainer>
    </SafeAreaProvider>
  );
}
