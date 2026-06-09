import sys
sys.stdout.reconfigure(encoding="utf-8")

from evening_recap import evening_check_message
from line_sender import send_broadcast


def main():
    msg = evening_check_message()
    send_broadcast(msg)
    print("夜の振り返りメッセージを送信しました")


if __name__ == "__main__":
    main()
