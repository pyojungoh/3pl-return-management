"""
PC의 IP 주소를 확인하는 스크립트
"""
import socket

def get_local_ip():
    """로컬 네트워크 IP 주소 가져오기"""
    try:
        # 외부 서버에 연결하여 로컬 IP 주소 확인
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception as e:
        print(f"IP 주소를 가져올 수 없습니다: {e}")
        return None

if __name__ == "__main__":
    ip = get_local_ip()
    if ip:
        print(f"\n✅ PC의 IP 주소: {ip}")
        print(f"\n📱 핸드폰에서 접속할 주소:")
        print(f"   http://{ip}:5000/admin")
        print(f"\n⚠️  주의사항:")
        print(f"   1. PC와 핸드폰이 같은 Wi-Fi에 연결되어 있어야 합니다")
        print(f"   2. 서버가 실행 중이어야 합니다 (python app.py)")
        print(f"   3. 방화벽에서 포트 5000을 허용해야 합니다")
    else:
        print("❌ IP 주소를 가져올 수 없습니다.")
        print("다음 명령어로 확인하세요:")
        print("  Windows: ipconfig")
        print("  Mac/Linux: ifconfig")



