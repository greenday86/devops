from datetime import datetime
import json
import pytz
import threading


def delete_message(client, channel_id, message_ts):
    try:
        client.chat_delete(channel=channel_id, ts=message_ts)
    except Exception as e:
        print(f"메시지 삭제 실패: {e}")

def register_menu_handlers(app):
    @app.message("menu")
    def show_button(message, say, client):
        print("show_button")
        # print(f"message[{message}]\n\n\n----")
        channel_id = message["channel"]
        print(f"channel_id[{channel_id}]")

        # Get current date and time in KST
        tz_kst = pytz.timezone('Asia/Seoul')
        now = datetime.now(tz_kst)
        current_date = now.strftime("%Y-%m-%d %H:%M:%S %Z")

        greeting_msg = say(
            channel=channel_id,
            text=f":wave: 안녕하세요! *메뉴*를 선택 해 주세요!\n(💡 Menu 유효 시간 : 1분)"
        )
        
        buttons_msg = say(
            channel=channel_id,
            blocks=[
                {
                    "type": "actions",
                    "block_id": "button_block",
                    "elements": [
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "ALB 거래 조정"
                            },
                            "style": "primary",  # Blue background with white text
                            "action_id": "open_modal_button"
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "상태 보기"
                            },
                            # "style": "primary",  # Blue background with white text
                            "action_id": "open_modal_button2"
                        },
                        {
                            "type": "button",
                            "text": {
                                "type": "plain_text",
                                "text": "Cluster, Pod 복제 갯수 조정"
                            },
                            # "style": "primary",  # Blue background with white text
                            "action_id": "open_modal_button3"
                        }
                    ]
                }
            ]
        )

        # Schedule the deletion of messages after 1 minute (60 seconds)
        threading.Timer(60, delete_message, [client, channel_id, greeting_msg["ts"]]).start()
        threading.Timer(60, delete_message, [client, channel_id, buttons_msg["ts"]]).start()
