import { NativeModules, NativeEventEmitter, Platform } from 'react-native';
import { parsePaymentText } from '../smsParser';
import { ParsedPayment } from '../../types';

// Android NotificationListenerService 브리지
// 실제 네이티브 모듈은 android/ 디렉터리에 구현
const { MoneyLogNotificationModule } = NativeModules;

const KAKAOPAY_PKG = 'com.kakao.talk';
const CARD_APP_PKGS = [
  'com.shinhan.sbanking',     // 신한SOL
  'com.kbcard.kbkookmincard', // KB국민카드
  'com.samsung.android.spay', // 삼성페이
  'com.hyundaicard.appcard',  // 현대카드
  'com.lottemembers.android', // 롯데카드
  'com.hanabank.ebk.channel.android.hananbank', // 하나은행
  'kr.co.citibank.citimobile', // 씨티
  'com.wooribank.smart.pib',  // 우리WON뱅킹
  'com.kftc.kjb',             // 카카오뱅크
  'viva.republica.toss',      // 토스
];

export type NotificationPayload = {
  packageName: string;
  title: string;
  text: string;
  timestamp: number;
};

let emitter: NativeEventEmitter | null = null;

export function startNotificationListener(
  onPayment: (parsed: ParsedPayment) => void
): () => void {
  if (Platform.OS !== 'android' || !MoneyLogNotificationModule) {
    return () => {};
  }

  if (!emitter) {
    emitter = new NativeEventEmitter(MoneyLogNotificationModule);
  }

  const subscription = emitter.addListener(
    'onNotificationReceived',
    (payload: NotificationPayload) => {
      const isRelevant =
        payload.packageName === KAKAOPAY_PKG ||
        CARD_APP_PKGS.includes(payload.packageName);

      if (!isRelevant) return;

      const text = `${payload.title ?? ''} ${payload.text ?? ''}`.trim();
      const parsed = parsePaymentText(text);
      if (parsed) {
        parsed.date = new Date(payload.timestamp);
        onPayment(parsed);
      }
    }
  );

  MoneyLogNotificationModule.startListening?.();

  return () => {
    subscription.remove();
    MoneyLogNotificationModule.stopListening?.();
  };
}

export function isNotificationServiceEnabled(): boolean {
  if (Platform.OS !== 'android' || !MoneyLogNotificationModule) return false;
  return MoneyLogNotificationModule.isServiceEnabled?.() ?? false;
}

export function openNotificationSettings(): void {
  MoneyLogNotificationModule?.openNotificationSettings?.();
}
