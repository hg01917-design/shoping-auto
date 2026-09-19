---
name: smartstore-listing
description: 사용자 이미지 또는 코스트코 공식몰 근거로 네이버 스마트스토어 상품을 식별·가격조사·이미지가공·상세페이지·속성·등록·사후 최적화한다. 상품 등록, 스마트스토어 상품 수정, 가격 조사 요청에 사용한다.
---

# SmartStore Listing Master Skill

스마트스토어 상품 등록 작업의 진입점이다. 상품 등록, 가격 계산, 이미지 가공, 상품명 생성, 속성 입력, 상세페이지 작성, 다중 Listing 생성, 등록 후 최적화 작업을 시작하기 전에 이 파일을 읽는다.

이 파일은 작업 경로만 안내한다. 세부 규칙은 아래 파일을 읽고 그 파일에서만 해석한다. 같은 규칙을 이 파일에 반복하지 않는다.

| 작업 | 반드시 읽을 파일 |
| --- | --- |
| 사용자 이미지 분석, 상품 식별, 동일상품 판단 | [product-identification.md](product-identification.md) |
| 경쟁가 조사, 판매가·배송비·마진 결정 | [pricing.md](pricing.md) |
| 대표·상세 이미지 가공과 Listing별 이미지 생성 | [image-processing.md](image-processing.md) |
| 다중 Listing, 키워드별 상품명·가격·구성 전략 | [listing-strategy.md](listing-strategy.md) |
| 카테고리, 속성, 태그, 상품명 SEO | [attributes-seo.md](attributes-seo.md) |
| 상세페이지 HTML, 설명, 정보표, 모바일 가독성 | [detail-page.md](detail-page.md) |
| 등록 후 순위·키워드·이미지 최적화 | [post-optimization.md](post-optimization.md) |
| 등록 API 직전 최종 검증 | [output-validation.md](output-validation.md) |

## 실행 원칙

사용자가 상품 또는 상품 폴더를 지정하고 등록 시작을 지시하면 등록 승인으로 본다. 승인 후에는 상품별 재확인을 묻지 않는다.

작업은 상품 식별 → 가격 조사 → 카테고리 및 속성 확인 → 다중 Listing 전략 → 이미지 가공 → 상세페이지 생성 → 최종 검증 → 스마트스토어 등록 → 결과 기록 순서로 진행한다.

여러 기능이 필요하면 관련 규칙 파일을 모두 읽는다. 규칙과 임의 판단이 충돌하면 규칙을 우선한다. 가격 계산, 이미지 출력, 파일 저장, API 호출, 등록 반영은 가능한 경우 `scripts/`의 파이썬 스크립트를 사용한다.
