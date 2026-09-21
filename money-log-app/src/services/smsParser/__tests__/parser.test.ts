import { parsePaymentText } from '../index';

describe('parsePaymentText', () => {
  test('KB국민카드 지출 파싱', () => {
    const result = parsePaymentText('[KB국민카드] 5,000원 사용 스타벅스 잔액 100,000원');
    expect(result).not.toBeNull();
    expect(result!.amount).toBe(5000);
    expect(result!.type).toBe('expense');
    expect(result!.isSubsidy).toBe(false);
    expect(result!.remainingBalance).toBe(100000);
  });

  test('에너지바우처 지원금 감지', () => {
    const result = parsePaymentText('에너지바우처 5,000원 사용 잔액 45,000원');
    expect(result).not.toBeNull();
    expect(result!.isSubsidy).toBe(true);
    expect(result!.subsidyKeyword).toBe('에너지바우처');
    expect(result!.amount).toBe(5000);
    expect(result!.remainingBalance).toBe(45000);
  });

  test('카카오페이 결제완료 파싱', () => {
    const result = parsePaymentText('카카오페이 결제완료 15,000원 쿠팡');
    expect(result).not.toBeNull();
    expect(result!.amount).toBe(15000);
    expect(result!.cardName).toBe('카카오페이');
    expect(result!.merchant).toContain('쿠팡');
  });

  test('카카오페이 일일 요약 파싱', () => {
    const result = parsePaymentText('오늘의 결제내역 3건 · 총 25,000원');
    expect(result).not.toBeNull();
    expect(result!.amount).toBe(25000);
    expect(result!.type).toBe('expense');
  });

  test('은행 입금 파싱', () => {
    const result = parsePaymentText('[국민은행] 50,000원 입금 잔액 1,500,000원');
    expect(result).not.toBeNull();
    expect(result!.type).toBe('income');
    expect(result!.amount).toBe(50000);
  });

  test('지역사랑상품권 지원금 감지', () => {
    const result = parsePaymentText('지역사랑상품권 10,000원 결제 잔액 40,000원');
    expect(result).not.toBeNull();
    expect(result!.isSubsidy).toBe(true);
    expect(result!.subsidyKeyword).toBe('지역사랑');
  });

  test('인식 불가 텍스트 → null 반환', () => {
    const result = parsePaymentText('안녕하세요 오늘 날씨 좋네요');
    expect(result).toBeNull();
  });
});
