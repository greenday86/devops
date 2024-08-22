from datetime import datetime
import json
import pytz
import os
import traceback

import boto3
from botocore.exceptions import ClientError

def register_alb_targetgroup_handlers(app):
    @app.action("open_modal_button")
    def open_modal(ack, body, client):
        ack()
        client.views_open(
            trigger_id=body["trigger_id"],
            view={
                "type": "modal",
                "callback_id": "modal_view1",
                "title": {"type": "plain_text", "text": "ALB 가중치를 선택하세요"},
                "blocks": [
                    {
                        "type": "actions",
                        "block_id": "weight_block",
                        "elements": [
                            {
                                "type": "static_select",
                                "placeholder": {"type": "plain_text", "text": "ALB 가중치를 어떻게 줄까요?"},
                                "action_id": "weight_select",
                                "options": [
                                    {"text": {"type": "plain_text", "text": "Blue CLUSTER 로만 거래 넣기"}, "value": "Blue CLUSTER 로만 거래 넣기"},
                                    {"text": {"type": "plain_text", "text": "Green CLUSTER 로만 거래 넣기"}, "value": "Green CLUSTER 로만 거래 넣기"},
                                    {"text": {"type": "plain_text", "text": "운영 모드(Blue(50):Green(50)) 로 전환"}, "value": "운영 모드(Blue(50):Green(50)) 로 전환"}
                                ],
                            },
                        ],
                    },
                ],
                "submit": {"type": "plain_text", "text": "Submit"},
                "close": {"type": "plain_text", "text": "취소"},
                "private_metadata": body["channel"]["id"]
            }
        )

    @app.view("modal_view1")
    def handle_modal_submission(ack, body, view, client):
        ack()
        channel_id      = view["private_metadata"]
        selected_option = view["state"]["values"]["weight_block"]["weight_select"]["selected_option"]["value"]
        user_id         = body['user']['id']

        if selected_option == "Blue CLUSTER 로만 거래 넣기":
            weight = {"targetGroup1": 1, "targetGroup2": 0}
        elif selected_option == "Green CLUSTER 로만 거래 넣기":
            weight = {"targetGroup1": 0, "targetGroup2": 1}
        elif selected_option == "운영 모드(Blue(50):Green(50)) 로 전환":
            weight = {"targetGroup1": 1, "targetGroup2": 1}

        tz_kst      = pytz.timezone('Asia/Seoul')
        now          = datetime.now(tz_kst)
        current_date = now.strftime("%Y-%m-%d %H:%M:%S %Z")

        client.chat_postMessage(channel=channel_id, text=f"💡 *{selected_option}* : *선택*\n\n현재 시간: {current_date}")        

        try:
            aws_region    = os.environ.get('AWS_REGION')
            print(f"aws_region[{aws_region}]")
            lambda_client = boto3.client('lambda', region_name=aws_region)
            response      = lambda_client.invoke(
                FunctionName='ChangeTargetGroupWeight',
                InvocationType='RequestResponse',
                Payload=json.dumps(weight))
            response_payload = json.loads(response['Payload'].read())
            client.chat_postMessage(channel=channel_id, text=f"💡 *{selected_option}* : *선택*\n\n현재 시간: {current_date}\n\nLambda 응답: {response_payload}")
        except ClientError as e:
            client.chat_postMessage(channel=channel_id, text=f"⚠️ Lambda 호출 실패: {str(e)}")
            print(f"Error invoking Lambda function: {str(e)}")
