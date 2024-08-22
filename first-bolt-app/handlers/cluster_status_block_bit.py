from datetime import datetime
import json
import pytz
import requests
import traceback

def register_cluster_status_handlers(app):
    @app.action("open_modal_button2")
    def open_modal(ack, body, client):
        ack()
        channel_id = body["channel"]["id"]

        client.views_open(
            trigger_id=body["trigger_id"],
            view={
                "type": "modal",
                "callback_id": "modal_view2",
                "title": {"type": "plain_text", "text": "Cluster 거래 상황 보기"},
                "blocks": [
                    {
                        "type": "actions",
                        "block_id": "status_block",
                        "elements": [
                            {
                                "type": "static_select",
                                "placeholder": {"type": "plain_text", "text": "어떤 자원의 상태를 보고싶나요?"},
                                "action_id": "status_select",
                                "options": [
                                    {"text": {"type": "plain_text", "text": "ALB TargetGroup 가중치 보기"}, "value": "alb/view_info"},
                                    {"text": {"type": "plain_text", "text": "CLUSTER-1"}, "value": "CLUSTER-1"},
                                    {"text": {"type": "plain_text", "text": "CLUSTER-2"}, "value": "CLUSTER-2"},
                                    {"text": {"type": "plain_text", "text": "Pods"}, "value": "Pods"},
                                ],
                            },
                        ],
                    },
                    {"type": "divider"}
                ],
                "submit": {"type": "plain_text", "text": "Submit"},
                "close": {"type": "plain_text", "text": "취소"},
                "private_metadata": channel_id
            }
        )

    @app.view("modal_view2")
    def handle_modal_submission(ack, body, view, client):
        ack()
        channel_id = view["private_metadata"]
        selected_option = view["state"]["values"]["status_block"]["status_select"]["selected_option"]["value"]

        tz_kst = pytz.timezone('Asia/Seoul')
        now = datetime.now(tz_kst)
        current_date = now.strftime("%Y-%m-%d %H:%M:%S %Z")

        client.chat_postMessage(channel=channel_id, text=f"💡 *{selected_option}* : *선택*\n\n현재 시간: {current_date}")

        try:
            service_host = 'apiserver-flask-svc.default.svc.cluster.local'
            service_port = '5005'
            url = f'http://{service_host}:{service_port}/{selected_option}'

            event_ = {
                "aws_region": "ap-northeast-2",
                "slack_secret_name": "ViewResourceInformation-is07456-01",
                "alb_name": "skcc-tf-p-eks-front-alb-pri",
                "s3_lambda": "s3-skcc-prd-is07456-lambda",
                "slack_channel": "lcl14"
            }

            response = requests.post(url, json=event_, timeout=120)
            if response.status_code == 200:
                response_payload = response.json()
                client.chat_postMessage(channel=channel_id, text=f"💡 *{selected_option}* : *Kubernetes Service [`{service_host}`]* 호출 성공: {response_payload}")
            else:
                client.chat_postMessage(channel=channel_id, text=f"💡 *{selected_option}* : *Kubernetes Service [`{service_host}`]* 호출 실패: {response.status_code} - {response.reason}\n{response.text}")

        except requests.exceptions.RequestException as e:
            client.chat_postMessage(channel=channel_id, text=f"💡 *{selected_option}* : *Kubernetes Service [`{service_host}`]* 호출 중 오류 발생: {str(e)}")
        except Exception as e:
            print(str(e))
            print(traceback.format_exc())
            client.chat_postMessage(channel=channel_id, text=f"⚠️ Kubernetes Service 호출 실패: {str(e)}")