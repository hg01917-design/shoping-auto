# 코스트코 → 네이버 스마트스토어 자동 등록

코스트코에서 소싱한 상품을 네이버 스마트스토어에 자동으로 등록하는 AI 에이전트용 플레이북 + 스크립트 모음.
Claude Code와 Codex CLI 양쪽에서 동일하게 동작한다 (지침 본체: `.claude/skills/smartstore-listing/SKILL.md`, Codex 진입점: `AGENTS.md`).

## 동작 방식

```
products/<상품폴더>/input/ 에 원본 정보 + 사진을 넣고
"이 폴더 상품 올려줘" 라고 지시하면
  → 키워드/상품명/설명 자동 생성 (네이버 SEO 가이드 준수)
  → 판매가 자동 계산 (역마진 방지)
  → 이미지 규격 가공 (1000x1000 정사각형)
  → 커머스API로 실제 등록까지 자동 실행
  → 완료 후 결과 일괄 보고
```

**⚠️ 주의**: 작업 시작 지시 = 등록 승인이다. 상품별 재확인 없이 실제 스토어에 게시된다.
멈추려면 "멈춰"라고 말하면 된다. 역마진·필수값 누락 상품은 자동으로 스킵된다.

## 최초 설정

### 1. 네이버 커머스API 앱 발급
1. [네이버 커머스API센터](https://apicenter.commerce.naver.com) 접속 → 판매자 계정 로그인
2. 애플리케이션 등록 → **애플리케이션 ID / 시크릿** 발급
3. **호출 IP 등록**: API를 실행할 PC의 공인 IP를 앱 설정에 등록 (미등록 IP는 호출 차단됨)

### 2. 자격증명 설정
```bash
cp config/credentials.example.json config/credentials.json
# credentials.json 열어서 NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 채우기
```
`config/credentials.json`은 `.gitignore` 처리되어 커밋되지 않는다. **절대 커밋하지 말 것.**

### 3. 의존성 설치
```bash
pip install -r requirements.txt
```

### 4. 스토어 설정 확인
- `config/store.json`: A/S 전화번호, 반품/교환 배송비, 원산지 코드 등 → 본인 스토어 값으로 수정
- `config/pricing.json`: 수수료율(기본: 매출연동 2.73% + 결제 3.63%, VAT 별도), 배송비 1,800원, 박스비 300원, 목표 마진율 10% → 등급에 맞게 조정

## 상품 폴더 만들기

```
products/<상품이름-slug>/
└── input/
    ├── source.md      # 코스트코 상품 정보 (아래 형식)
    └── images/        # 원본 사진들 (첫 사진이 대표 이미지)
```

`source.md` 형식 (`products/_sample-product/input/source.md` 참고):

```markdown
# 상품명: 커클랜드 시그니처 구운아몬드 1.13kg
- 원가: 18900
- 브랜드: 커클랜드
- 원본URL: https://www.costco.co.kr/...
- 옵션: 무염 / 가염
- 특징:
  - 대용량 1.13kg
  - 무염 로스팅
```

## 실행

Claude Code / Codex CLI에서:
```
products/kirkland-almond 상품 올려줘
```
또는 여러 폴더를 한 번에:
```
products 안에 있는 신규 상품 전부 올려줘
```

### 스크립트 단독 실행 (디버깅)
```bash
python3 scripts/pricing.py --cost 18900                  # 가격 계산 (API 키 불필요)
python3 scripts/process_images.py <입력폴더> <출력폴더>    # 이미지 가공 (API 키 불필요)
python3 scripts/naver_auth.py                            # 토큰 발급 테스트
python3 scripts/search_category.py "견과류"               # 카테고리 검색
python3 scripts/register_product.py products/<slug>      # 등록 실행
```

## 파일 구조

| 경로 | 역할 |
|---|---|
| `.claude/skills/smartstore-listing/SKILL.md` | 전체 워크플로우 지침 (단일 소스) |
| `AGENTS.md` | Codex CLI 진입점 (SKILL.md로 안내) |
| `config/` | 자격증명·가격·스토어·카테고리 캐시 설정 |
| `scripts/` | 인증/가격/이미지/카테고리/등록 스크립트 |
| `products/<slug>/input/` | 사용자가 넣는 원본 정보+사진 |
| `products/<slug>/output/` | AI가 생성한 listing.json + 가공 이미지 |
| `products/<slug>/status.json` | 등록 상태 (registered/error, productNo) |

## 최초 1건 테스트 권장 절차

1. `products/_sample-product`를 복사해 실제 상품 1개로 폴더 구성
2. 등록 실행 후 스마트스토어 판매자센터에서 노출 상태/상품정보 확인
3. 문제 없으면 이후부터 여러 건 일괄 처리

API 스키마 변경으로 등록이 실패하면 [커머스API센터](https://apicenter.commerce.naver.com)와
[commerce-api GitHub](https://github.com/commerce-api-naver/commerce-api)에서 최신 스펙 확인.

---

## 별도 도구: 상세페이지 크롤러 / Gemini 이미지 생성기

이 저장소에는 자동 등록과 독립적인 로컬 PC용 도구도 있다 (Whale/Chrome CDP 필요):
- `crawler.py`, `extract_from_cdp.py`: 경쟁사 스마트스토어 상세페이지 크롤링
- `gemini_analyzer.py`, `detail_page_generator.py`: Gemini 웹 UI로 상세페이지 6슬롯 이미지 생성
