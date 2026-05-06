"""
Google Drive용 OAuth를 로컬에서 다시 받아 token.pickle을 만듭니다.

- api.uploads 패키지 __init__ (Flask 라우트 로드)를 피하려고 oauth_drive.py만 직접 로드합니다.
- 이후: python extract_oauth_token.py → 출력 JSON을 Vercel GOOGLE_OAUTH_TOKEN_JSON에 붙여넣기.

사전 조건: 프로젝트 루트에 credentials.json (Vercel의 GOOGLE_OAUTH_CREDENTIALS_JSON과 동일 클라이언트 권장)
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys


def main() -> None:
    root = pathlib.Path(__file__).resolve().parent
    mod_path = root / 'api' / 'uploads' / 'oauth_drive.py'
    if not mod_path.is_file():
        print(f'❌ 파일 없음: {mod_path}')
        sys.exit(1)

    spec = importlib.util.spec_from_file_location('oauth_drive_renew', mod_path)
    if spec is None or spec.loader is None:
        print('❌ 모듈 로드 실패')
        sys.exit(1)

    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.run_local_oauth_interactive_and_pickle()
    print('\n다음: python extract_oauth_token.py 실행 후 JSON을 Vercel에 반영하세요.')


if __name__ == '__main__':
    main()
