import sys
sys.stdout.reconfigure(encoding="utf-8")

from morning_check import morning_check_message
from line_sender import send_broadcast


def main():
    msg = morning_check_message()
    send_broadcast(msg)
    print("朝のチェックメッセージを送信しました")


if __name__ == "__main__":
    main()
