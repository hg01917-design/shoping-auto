# Output Validation Rules

상품 등록 API 호출 직전에 아래 검증을 수행한다. 수치·허용 범위·가격결정의 원본 규칙은 [pricing.md](pricing.md), 이미지 규칙은 [image-processing.md](image-processing.md), 속성·SEO 규칙은 [attributes-seo.md](attributes-seo.md), 상세 규칙은 [detail-page.md](detail-page.md)를 기준으로 한다. 이 파일에는 원본 기준을 반복해 적지 않는다.

## 검증 항목

- 상품명, 브랜드, 용량, 수량, 구성·옵션, 원산지가 실제 상품과 일치하는지
- 원가 근거의 우선순위와 최종 채택 원가가 기록됐는지
- 스마트스토어 경쟁가의 판매자명, 직접 URL, 상품가, 고객 배송비, 총 결제금액, 확인 시각이 기록됐는지
- `scripts/pricing.py` 계산 결과가 `listing.json`의 판매가·배송비와 일치하고 역마진이 아닌지
- 배송비가 `UNIT_QUANTITY_PAID`, `repeatQuantity: 1`, `deliveryBundleGroupUsable: false`로 반영됐는지와 수량 2개 주문 시 고객 결제 예상값이 `2 × (상품가 + 상품별 배송비)`인지
- Listing별 키워드와 가격·배송비·구성 전략이 실제로 구분되는지
- 이미지 가공 이력, 최종 대표이미지, 상품 포장·라벨·구성 일치 여부
- 검증 가능한 속성이 API 카테고리 허용값과 일치하고 추측값이 없는지
- 상세페이지가 모바일에서 읽기 쉽고, 실제 상품 정보만 사용하며, 과장 표현과 반복 문단이 없고, 정보표와 상세이미지가 정상 표시되는지

검증 실패 시 해당 항목을 수정하고 다시 검사한다. 사용자에게 상품별 재확인을 요청하지 않는다.
