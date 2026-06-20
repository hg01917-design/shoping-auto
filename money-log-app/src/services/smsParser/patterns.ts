export interface CardPattern {
  name: string;
  amountRegex: RegExp;
  merchantRegex?: RegExp;
  balanceRegex?: RegExp;
  isExpense: (text: string) => boolean;
}

// 금액 추출 공통 (쉼표 포함 숫자 + 원)
const AMOUNT_RE = /([\d,]+)원/;

// 잔액 추출 공통
const BALANCE_RE = /잔[액여]\s*[\s:：]?\s*([\d,]+)원/;

export const CARD_PATTERNS: CardPattern[] = [
  {
    name: 'KB국민카드',
    amountRegex: /([\d,]+)원\s*(사용|승인)/,
    merchantRegex: /(?:사용|승인)\s+(.+?)(?:\s+잔|$)/,
    balanceRegex: BALANCE_RE,
    isExpense: (t) => /사용|승인/.test(t),
  },
  {
    name: '신한카드',
    amountRegex: /신한\S*카드\s+([\d,]+)원\s*(?:승인|결제)/,
    merchantRegex: /(?:승인|결제)\s+(.+?)(?:\s+(?:잔|이용)|$)/,
    balanceRegex: /이용가능금액\s*([\d,]+)원/,
    isExpense: (t) => /승인|결제/.test(t),
  },
  {
    name: '삼성카드',
    amountRegex: /삼성카드\s+([\d,]+)원\s*(?:사용|승인)/,
    merchantRegex: /(?:사용|승인)\s+(.+?)(?:\s+포인트|$)/,
    balanceRegex: /포인트잔액[:\s]+([\d,]+)/,
    isExpense: () => true,
  },
  {
    name: '현대카드',
    amountRegex: /현대카드\s+([\d,]+)원\s*(?:사용|승인)/,
    merchantRegex: /(?:사용|승인)\s+(.+?)(?:\s+잔|$)/,
    balanceRegex: BALANCE_RE,
    isExpense: () => true,
  },
  {
    name: '롯데카드',
    amountRegex: /롯데카드\s+([\d,]+)원\s*(?:사용|승인)/,
    merchantRegex: /(?:사용|승인)\s+(.+?)(?:\s+잔|$)/,
    balanceRegex: BALANCE_RE,
    isExpense: () => true,
  },
  {
    name: '하나카드',
    amountRegex: /하나카드\s+([\d,]+)원\s*(?:사용|승인)/,
    merchantRegex: /(?:사용|승인)\s+(.+?)(?:\s+잔|$)/,
    balanceRegex: BALANCE_RE,
    isExpense: () => true,
  },
  {
    name: 'BC카드',
    amountRegex: /BC카드\s+([\d,]+)원\s*(?:사용|승인)/,
    merchantRegex: /(?:사용|승인)\s+(.+?)(?:\s+잔|$)/,
    balanceRegex: BALANCE_RE,
    isExpense: () => true,
  },
  {
    name: '농협카드',
    amountRegex: /NH농협\S*\s+([\d,]+)원\s*(?:사용|승인)/,
    merchantRegex: /(?:사용|승인)\s+(.+?)(?:\s+잔|$)/,
    balanceRegex: BALANCE_RE,
    isExpense: () => true,
  },
  {
    name: '우리카드',
    amountRegex: /우리카드\s+([\d,]+)원\s*(?:사용|승인)/,
    merchantRegex: /(?:사용|승인)\s+(.+?)(?:\s+잔|$)/,
    balanceRegex: BALANCE_RE,
    isExpense: () => true,
  },
];

export const BANK_PATTERNS = [
  // 입금
  { pattern: /([국민신한하나우리농협기업카카오토스]+은행|카카오뱅크|토스뱅크)\s+([\d,]+)원\s*입금/, isIncome: true },
  // 출금
  { pattern: /([국민신한하나우리농협기업카카오토스]+은행|카카오뱅크|토스뱅크)\s+([\d,]+)원\s*출금/, isIncome: false },
  // 이체
  { pattern: /([\d,]+)원\s*(?:이체|출금)\s/, isIncome: false },
  { pattern: /([\d,]+)원\s*입금/, isIncome: true },
];

export const KAKAOPAY_PATTERNS = [
  // 카카오페이 결제완료
  /카카오페이\s*결제완료?\s*([\d,]+)원\s+(.+)/,
  // 카카오페이 결제
  /카카오페이\s+([\d,]+)원\s*(?:결제|사용)/,
  // 오늘의 결제내역 요약
  /오늘의?\s*결제내역\s*(\d+)건\s*[·\s]*총?\s*([\d,]+)원/,
  // 카카오뱅크 이체
  /카카오뱅크\s+([\d,]+)원\s*(입금|출금|이체)/,
];

export const SUBSIDY_KEYWORDS = [
  '지원금', '바우처', '복지포인트', '복지카드', '에너지바우처',
  '재난지원', '지역사랑', '지역화폐', '행복카드', '국민행복',
  '사회서비스', '의료급여', '장애인', '청년지원', '출산장려',
  '양육수당', '아동수당', '교육지원', '취업지원',
];

export const CATEGORY_KEYWORDS: Record<string, string[]> = {
  '식비': ['식당', '음식', '치킨', '피자', '중식', '한식', '일식', '분식', '김밥', '도시락', '배달'],
  '카페': ['카페', '스타벅스', '투썸', '이디야', '빽다방', '메가커피', '파스쿠찌', '커피'],
  '마트/편의점': ['gs25', 'cu편의점', '세븐일레븐', '미니스톱', '이마트', '홈플러스', '롯데마트', '코스트코', '마트'],
  '교통': ['택시', '버스', '지하철', '카카오택시', '우티', 'kt m모바일', '교통카드', 'korail', '기차'],
  '쇼핑': ['쿠팡', '11번가', '지마켓', '옥션', '위메프', '티몬', '무신사', '올리브영'],
  '의료': ['병원', '의원', '약국', '의료', '치과', '한의원', '의학'],
  '문화/여가': ['cgv', '메가박스', '롯데시네마', '영화', '공연', '게임', '여행'],
  '공과금': ['한전', '도시가스', '수도', '관리비', 'kt', 'sk텔레콤', 'lg유플러스'],
};

export function parseAmount(text: string): number | null {
  const match = text.match(AMOUNT_RE);
  if (!match) return null;
  return parseInt(match[1].replace(/,/g, ''), 10);
}
