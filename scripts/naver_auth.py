# 네이버 커머스API 전자서명 생성 + OAuth2 토큰 발급/캐싱
#
# 인증 방식 (커머스API 공식):
#   password  = f"{client_id}_{timestamp_ms}"
#   signature = base64( bcrypt.hashpw(password, salt=client_secret) )
#   POST /external/v1/oauth2/token (form-urlencoded)
#     client_id, timestamp, client_secret_sign, grant_type=client_credentials, type=SELF
#
# 사용법:
#   python3 scripts/naver_auth.py            # 토큰 발급 테스트 (디버깅용)
#   from naver_auth import get_access_token  # 다른 스크립트에서 임포트

import base64
import json
import sys
import time
from pathlib import Path

import bcrypt
import requests

ROOT = Path(__file__).resolve().parent.parent
CREDENTIALS_PATH = ROOT / "config" / "credentials.json"
TOKEN_CACHE_PATH = ROOT / "config" / ".token_cache.json"

API_BASE = "https://api.commerce.naver.com/external"
TOKEN_URL = f"{API_BASE}/v1/oauth2/token"

# 만료 임박 여유 시간 (초) — 이 시간 이내로 남으면 재발급
EXPIRY_MARGIN_SEC = 600


def load_credentials() -> dict:
    if not CREDENTIALS_PATH.exists():
        raise FileNotFoundError(
            f"{CREDENTIALS_PATH} 가 없습니다.\n"
            "config/credentials.example.json 을 config/credentials.json 으로 복사한 뒤 "
            "네이버 커머스API센터(https://apicenter.commerce.naver.com)에서 발급받은 "
            "애플리케이션 ID/시크릿을 채워 넣으세요. (README.md 참고)"
        )
    with open(CREDENTIALS_PATH, encoding="utf-8") as f:
        creds = json.load(f)
    for key in ("NAVER_CLIENT_ID", "NAVER_CLIENT_SECRET"):
        if not creds.get(key) or creds[key].startswith("여기에"):
            raise ValueError(f"config/credentials.json 의 {key} 값이 비어 있습니다.")
    return creds


def make_signature(client_id: str, client_secret: str, timestamp_ms: int) -> str:
    password = f"{client_id}_{timestamp_ms}"
    hashed = bcrypt.hashpw(password.encode("utf-8"), client_secret.encode("utf-8"))
    return base64.b64encode(hashed).decode("utf-8")


def _load_cached_token() -> str | None:
    if not TOKEN_CACHE_PATH.exists():
        return None
    try:
        with open(TOKEN_CACHE_PATH, encoding="utf-8") as f:
            cache = json.load(f)
        if cache.get("expires_at", 0) - time.time() > EXPIRY_MARGIN_SEC:
            return cache["access_token"]
    except Exception:
        pass
    return None


def _save_token_cache(access_token: str, expires_in: int):
    TOKEN_CACHE_PATH.write_text(
        json.dumps(
            {"access_token": access_token, "expires_at": time.time() + expires_in},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def get_access_token(force_refresh: bool = False) -> str:
    """캐시된 토큰을 반환하거나, 만료 임박 시 새로 발급한다."""
    if not force_refresh:
        cached = _load_cached_token()
        if cached:
            return cached

    creds = load_credentials()
    timestamp_ms = int(time.time() * 1000)
    signature = make_signature(
        creds["NAVER_CLIENT_ID"], creds["NAVER_CLIENT_SECRET"], timestamp_ms
    )

    resp = requests.post(
        TOKEN_URL,
        data={
            "client_id": creds["NAVER_CLIENT_ID"],
            "timestamp": timestamp_ms,
            "client_secret_sign": signature,
            "grant_type": "client_credentials",
            "type": creds.get("account_type", "SELF"),
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    if resp.status_code != 200:
        raise RuntimeError(
            f"토큰 발급 실패 (HTTP {resp.status_code}): {resp.text}\n"
            "- client_id/secret 확인\n"
            "- 커머스API센터 앱 설정에 현재 PC의 공인 IP가 등록되어 있는지 확인"
        )

    data = resp.json()
    _save_token_cache(data["access_token"], data.get("expires_in", 10800))
    return data["access_token"]


def auth_headers(token: str | None = None) -> dict:
    return {"Authorization": f"Bearer {token or get_access_token()}"}


if __name__ == "__main__":
    try:
        token = get_access_token(force_refresh="--force" in sys.argv)
        print(f"[+] 토큰 발급 성공 (앞 20자): {token[:20]}...")
    except Exception as e:
        print(f"[!] {e}")
        sys.exit(1)
