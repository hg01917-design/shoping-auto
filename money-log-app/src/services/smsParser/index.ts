import {
  CARD_PATTERNS, BANK_PATTERNS, KAKAOPAY_PATTERNS,
  SUBSIDY_KEYWORDS, CATEGORY_KEYWORDS, parseAmount,
} from './patterns';
import { ParsedPayment } from '../../types';

export function parsePaymentText(text: string): ParsedPayment | null {
  const normalized = text.trim().replace(/\n/g, ' ');

  // 지원금 키워드 감지
  const subsidyKeyword = SUBSIDY_KEYWORDS.find((kw) =>
    normalized.includes(kw)
  ) ?? null;

  // 카카오페이 파싱
  const kakaoParsed = parseKakaoPay(normalized, subsidyKeyword);
  if (kakaoParsed) return kakaoParsed;

  // 카드사 패턴 파싱
  for (const pattern of CARD_PATTERNS) {
    const match = normalized.match(pattern.amountRegex);
    if (!match) continue;

    const amount = parseInt(match[1].replace(/,/g, ''), 10);
    const merchantMatch = pattern.merchantRegex
      ? normalized.match(pattern.merchantRegex)
      : null;
    const balanceMatch = pattern.balanceRegex
      ? normalized.match(pattern.balanceRegex)
      : null;

    return {
      amount,
      type: pattern.isExpense(normalized) ? 'expense' : 'income',
      merchant: cleanMerchant(merchantMatch?.[1] ?? ''),
      cardName: pattern.name,
      remainingBalance: balanceMatch
        ? parseInt(balanceMatch[1].replace(/,/g, ''), 10)
        : null,
      isSubsidy: subsidyKeyword !== null,
      subsidyKeyword,
      date: new Date(),
      rawText: text,
    };
  }

  // 은행 패턴 파싱
  for (const bp of BANK_PATTERNS) {
    const match = normalized.match(bp.pattern);
    if (!match) continue;
    const amountStr = match[2] ?? match[1];
    const amount = parseInt(amountStr.replace(/,/g, ''), 10);

    const balanceMatch = normalized.match(/잔[액여]\s*[\s:：]?\s*([\d,]+)원/);
    return {
      amount,
      type: bp.isIncome ? 'income' : 'expense',
      merchant: '',
      cardName: match[1] ?? '',
      remainingBalance: balanceMatch
        ? parseInt(balanceMatch[1].replace(/,/g, ''), 10)
        : null,
      isSubsidy: subsidyKeyword !== null,
      subsidyKeyword,
      date: new Date(),
      rawText: text,
    };
  }

  // 지원금 텍스트에서 금액만 추출 (바우처 등 특수 포맷)
  if (subsidyKeyword) {
    const amount = parseAmount(normalized);
    if (amount) {
      const balanceMatch = normalized.match(/잔[액여]\s*[\s:：]?\s*([\d,]+)원/);
      return {
        amount,
        type: 'expense',
        merchant: '',
        cardName: '',
        remainingBalance: balanceMatch
          ? parseInt(balanceMatch[1].replace(/,/g, ''), 10)
          : null,
        isSubsidy: true,
        subsidyKeyword,
        date: new Date(),
        rawText: text,
      };
    }
  }

  return null;
}

function parseKakaoPay(text: string, subsidyKeyword: string | null): ParsedPayment | null {
  // 결제완료 패턴
  const completeMatch = text.match(/카카오페이\s*결제완료?\s*([\d,]+)원\s*(.+?)(?:\s+잔|$)/);
  if (completeMatch) {
    return {
      amount: parseInt(completeMatch[1].replace(/,/g, ''), 10),
      type: 'expense',
      merchant: cleanMerchant(completeMatch[2] ?? ''),
      cardName: '카카오페이',
      remainingBalance: null,
      isSubsidy: subsidyKeyword !== null,
      subsidyKeyword,
      date: new Date(),
      rawText: text,
    };
  }

  // 오늘의 결제내역 요약 – 금액만 기록 (건수 표시)
  const summaryMatch = text.match(/오늘의?\s*결제내역\s*(\d+)건[·\s]*총?\s*([\d,]+)원/);
  if (summaryMatch) {
    return {
      amount: parseInt(summaryMatch[2].replace(/,/g, ''), 10),
      type: 'expense',
      merchant: `카카오페이 결제 ${summaryMatch[1]}건`,
      cardName: '카카오페이',
      remainingBalance: null,
      isSubsidy: false,
      subsidyKeyword: null,
      date: new Date(),
      rawText: text,
    };
  }

  // 카카오뱅크 이체
  const bankMatch = text.match(/카카오뱅크\s+([\d,]+)원\s*(입금|출금|이체)/);
  if (bankMatch) {
    return {
      amount: parseInt(bankMatch[1].replace(/,/g, ''), 10),
      type: bankMatch[2] === '입금' ? 'income' : 'expense',
      merchant: '',
      cardName: '카카오뱅크',
      remainingBalance: null,
      isSubsidy: false,
      subsidyKeyword: null,
      date: new Date(),
      rawText: text,
    };
  }

  return null;
}

export function guessCategory(merchant: string): string {
  const lower = merchant.toLowerCase();
  for (const [category, keywords] of Object.entries(CATEGORY_KEYWORDS)) {
    if (keywords.some((kw) => lower.includes(kw))) return category;
  }
  return '기타';
}

function cleanMerchant(raw: string): string {
  return raw
    .replace(/\s+/g, ' ')
    .replace(/[^\w가-힣\s]/g, '')
    .trim()
    .slice(0, 30);
}
