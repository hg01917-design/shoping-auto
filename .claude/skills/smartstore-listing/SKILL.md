---
name: smartstore-listing
description: 코스트코 소싱 상품을 네이버 스마트스토어에 자동 등록한다. 상품 폴더(products/<slug>/input/)의 원본 정보와 사진을 가공해 상품명/키워드/설명 생성, 가격 계산, 이미지 규격화, 커머스API 등록까지 전 과정을 수행. "상품 올려줘", "등록해줘", "스마트스토어" 관련 요청 시 사용.
---

# 코스트코 → 스마트스토어 자동 등록 스킬

## 운영 원칙 (반드시 준수)

1. **연속 자동 처리**: 사용자가 상품 폴더를 지정하고 작업 시작을 지시하면, **그 지시가 곧 등록 승인이다.** 상품별로 "등록할까요?"를 다시 묻지 않는다. 대상 상품 전부를 등록 완료까지 자동으로 진행하고, 마지막에 결과를 한 번에 보고한다. 사용자가 "멈춰"라고 하면 즉시 중단한다.
2. **역마진 절대 금지**: 판매가는 반드시 `scripts/pricing.py`로 계산한다. 수수료·배송비 1,800원·박스비 300원을 차감하고 **매출의 10% 마진**이 남아야 한다. pricing.py가 `ok: false`를 반환하면 그 상품은 등록하지 않는다.
3. **사람 확인 대신 sanity check**: 필수값 누락, 역마진, 카테고리 매칭 실패 상품은 등록을 시도하지 말고 `status.json`에 사유를 기록한 뒤 다음 상품으로 넘어간다. `register_product.py`가 등록 직전에 같은 검증을 한 번 더 강제한다.
4. **중복 등록 금지**: `status.json`의 `status`가 `registered`인 상품은 건드리지 않는다.

## 워크플로우

### 1. 대상 감지
`products/*/input/source.md`가 존재하고 `status.json`이 없거나 `status != "registered"`인 폴더를 모두 찾는다. 사용자가 특정 폴더를 지정했으면 그것만 처리한다.

### 2. 원본 파싱
`input/source.md`에서 코스트코 상품명, 원가(매입가), 브랜드, 옵션, 특징, 원본 URL을 읽는다. 원가가 없으면 해당 상품은 스킵하고 사유를 기록한다 (가격 계산 불가).

### 3. 키워드 발굴 + 상품명 조합 (AI 작업)

네이버쇼핑 공식 가이드("네이버쇼핑 상품정보 제공 가이드", naver.marketinsite.co.kr) 기준:

**키워드 발굴**: 상품 특성에서 구매자가 실제 검색할 핵심 키워드 2~3개를 도출한다. (예: 커클랜드 아몬드 → "아몬드", "구운아몬드", "대용량 견과류")

**상품명 조합 공식**: `브랜드/제조사 + 시리즈/모델 + 상품형태 + 속성(용량·수량·색상·사이즈)` 순서, **50자 내외** (최대 100자, 50자 초과 시 노출 불리).

**금지 규칙** (위반 시 검색 노출 페널티):
- 조사·수식어·홍보문구 금지: "최고의", "무료배송", "핫딜", "정품", "~를 위한"
- 특수문자·기호 남용 금지 (`[]`, `()`, `~`, `!`, `★` 등)
- 셀러명/쇼핑몰명 포함 금지
- 동일 키워드 반복 금지 ("아몬드 아몬드")
- 숫자는 아라비아 숫자로 ("일 키로" ❌ → "1kg" ⭕)
- 한글 우선, 필요한 경우만 영문

### 4. 카테고리 매칭
1. `config/categories.json` 캐시에서 후보 검색.
2. 없으면 `python3 scripts/search_category.py "<키워드>"` 실행 → 리프 카테고리 ID 획득 (자동으로 캐시에 추가됨).
3. 매칭 실패 시 그 상품은 스킵 + 사유 기록.

### 5. 가격 계산
```bash
python3 scripts/pricing.py --cost <원가>
```
- 출력 JSON의 `ok`가 `false`면 등록 불가 — 스킵 + 사유 기록.
- `ok: true`면 `sale_price`를 판매가로 쓰고, **출력 JSON 전체를 listing.json의 `pricing` 블록에 그대로 저장**한다 (register_product.py가 재검증에 사용).

### 6. 이미지 가공
```bash
python3 scripts/process_images.py products/<slug>/input/images products/<slug>/output/images
```
- 정사각형 1000x1000 JPEG로 변환, EXIF 제거.
- 첫 번째 이미지가 대표 이미지가 되므로, 제품 전체가 잘 보이는 사진을 파일명 순서상 앞에 오도록 한다 (필요 시 파일명 변경).
- 대표 이미지에 과도한 텍스트/테두리/워터마크가 있으면 다른 사진으로 교체.

### 7. 상세설명(detailContent) 작성 (AI 작업)
HTML 문자열로 작성. 구성 순서:
1. 핵심 소구점 헤드라인 (구매 이유 1줄)
2. 상품 기본 정보 (용량/수량/원산지/보관법)
3. 특징 3~5개 (bullet)
4. 코스트코 정품 소싱 안내
5. 배송/교환/반품 안내

`<script>`, `<iframe>` 등은 API에서 필터링되므로 사용 금지. `<p>`, `<h2>`, `<ul>`, `<strong>`, `<img>` 위주로.

### 8. listing.json 조립
`products/<slug>/output/listing.json`에 저장:

```json
{
  "name": "커클랜드 구운아몬드 1.13kg 무염 대용량",
  "leafCategoryId": "50002138",
  "salePrice": 32000,
  "stockQuantity": 20,
  "detailContent": "<h2>...</h2>...",
  "images": ["output/images/main.jpg", "output/images/sub1.jpg"],
  "brandName": "커클랜드",
  "manufacturerName": "Kirkland Signature",
  "modelName": "구운아몬드 1.13kg",
  "sellerTags": ["구운아몬드", "무염아몬드", "대용량견과", "코스트코견과", "아몬드1kg"],
  "pricing": { "...pricing.py 출력 JSON 전체..." : "" },
  "simpleOptions": []
}
```

**검색 노출 필드는 필수처럼 채운다** (네이버쇼핑 적합도 랭킹 = 상품명 + 카테고리 + 브랜드 + 속성/태그):
- `brandName`/`manufacturerName`/`modelName`: 반드시 입력
- `sellerTags`: 최대 10개. 상품명에 넣지 못한 연관 검색어 위주로 (상품명과 중복 최소화)
- `stockQuantity`: source.md에 재고 명시 없으면 기본 10

### 9. 등록 실행
```bash
python3 scripts/register_product.py products/<slug>
```
- 내부적으로: sanity check → 이미지 업로드 API → 상품 등록 API → `status.json`에 `productNo` 기록.
- 성공: `status=registered`. 실패: `status=error` + 사유 (재실행 시 재시도 가능).
- 여러 상품 처리 시 **순차 실행** (이미지 업로드 API는 계정당 동시 1건 제한).
- 인증 실패(토큰/IP) 시: README의 "API 앱 설정" 안내를 사용자에게 전달하고 나머지 상품 처리를 중단한다 (전부 같은 이유로 실패할 것이므로).

### 10. 결과 보고 (마지막에 한 번)
```
✅ 등록 완료 3건
  - 커클랜드 구운아몬드 1.13kg (productNo 12345678, 판매가 32,000원, 마진 10.2%)
  - ...
⏭️ 스킵 1건
  - products/xxx: 역마진 (원가 45,000원 → 필요 판매가 54,200원이 시세 대비 과도)
```

## 상태 관리 (status.json)

```json
{ "status": "registered | error", "productNo": "...", "errors": [], "updated_at": "..." }
```

## 참고
- API 스키마가 바뀌어 등록이 실패하면 https://apicenter.commerce.naver.com 과 https://github.com/commerce-api-naver/commerce-api 의 최신 스펙을 확인해 `scripts/register_product.py`의 페이로드를 수정한다.
- 스토어 공통값(A/S 연락처, 반품비, 원산지 코드)은 `config/store.json`에서 관리.
