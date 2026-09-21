# 가계부 앱 (Money Log App)

SMS · 카드알림 · 카카오페이를 자동 수집하는 스마트 가계부. **지원금 잔액 구분 기능** 탑재.

## 주요 기능

### 기본 가계부
- 카드/은행 SMS 자동 파싱 및 기록
- 수동 거래 입력
- 월별 수입/지출 통계
- 카테고리별 분류

### 자동 수집 (Android)
| 채널 | 방식 |
|------|------|
| SMS | READ_SMS 권한으로 카드/은행 문자 파싱 |
| 카드사 앱 알림 | NotificationListenerService (신한SOL, KB국민앱, 삼성Pay 등) |
| 카카오페이 | 카카오페이/카카오뱅크 알림 자동 파싱 |

### iOS
- SMS 붙여넣기 파싱: 카드/은행 문자를 복사 → 앱에 붙여넣기 → 자동 분류

### 지원금 구분 기능 (차별화)
- 에너지바우처, 지역사랑상품권, 복지포인트, 재난지원금 등 별도 관리
- 지원금별 잔액 / 사용금액 / 진행률 시각화
- SMS 키워드 기반 자동 분류 (예: "에너지바우처", "지역사랑" 등)
- 만료일 D-7 경고
- 지원금 사용 내역 vs 일반 지출 분리 조회

## 기술 스택

- React Native (Expo bare workflow) + TypeScript
- SQLite (expo-sqlite) - 로컬 데이터 저장
- Zustand - 상태 관리
- React Navigation v6

## 시작하기

```bash
cd money-log-app
npm install

# Android
npm run android

# iOS
npm run ios
```

### Android 권한 설정

앱 첫 실행 시:
1. SMS 읽기 권한 허용
2. 설정 → 알림 접근 → 가계부 허용 (카드사 앱/카카오페이 자동 수집용)

## 지원 카드/은행

KB국민카드, 신한카드, 삼성카드, 현대카드, 롯데카드, 하나카드, BC카드, NH농협카드, 우리카드, 카카오페이, 카카오뱅크, 토스, 국민/신한/하나/우리/농협/기업은행

## 프로젝트 구조

```
src/
├── screens/
│   ├── Dashboard/       홈 (요약 + 지원금 배지 + 빠른 입력)
│   ├── Transactions/    거래 내역 (탭: 전체/지출/수입/지원금)
│   ├── Subsidy/         지원금 관리 (핵심 차별화 기능)
│   ├── Statistics/      통계 (월별 바차트 + 카테고리 파이)
│   └── Settings/        설정
├── services/
│   ├── smsParser/       한국 카드/은행/카카오페이 SMS 파싱
│   ├── database/        SQLite CRUD
│   └── notificationListener/  Android 알림 리스너
└── store/               Zustand 스토어
```
