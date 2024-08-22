from datetime import datetime
import json
import pytz
import boto3
from botocore.exceptions import ClientError
import traceback

def register_scale_in_out_handlers(app):
    @app.action("open_modal_button3")
    def open_modal(ack, body, client):
        ack()
        channel_id = body["channel"]["id"]

        client.views_open(
            trigger_id=body["trigger_id"],
            view={
                "type": "modal",
                "callback_id": "modal_view3",
                "title": {"type": "plain_text", "text": "Scale-In/Scale-Out"},
                "blocks": [
                    {
                        "type": "input",
                        "block_id": "cluster_block",
                        "element": {
                            "type": "static_select",
                            "action_id": "cluster_select",
                            "placeholder": {"type": "plain_text", "text": "Cluster 명을 선택하세요"},
                            "options": [
                                {"text": {"type": "plain_text", "text": "skcc-07456-p-is-tf-01"}, "value": "skcc-07456-p-is-tf-01"},
                                {"text": {"type": "plain_text", "text": "skcc-07456-p-is-tf-02"}, "value": "skcc-07456-p-is-tf-02"},
                            ],
                        },
                        "label": {"type": "plain_text", "text": "Cluster 선택"},
                    },
                    {
                        "type": "input",
                        "block_id": "action_block",
                        "element": {
                            "type": "static_select",
                            "action_id": "action_select",
                            "placeholder": {"type": "plain_text", "text": "동작을 선택하세요"},
                            "options": [
                                {"text": {"type": "plain_text", "text": "scale-out"}, "value": "scale-out"},
                                {"text": {"type": "plain_text", "text": "scale-in"}, "value": "scale-in"},
                            ],
                        },
                        "label": {"type": "plain_text", "text": "동작 선택"},
                    },
                    {
                        "type": "input",
                        "block_id": "target_block",
                        "element": {
                            "type": "static_select",
                            "action_id": "target_select",
                            "placeholder": {"type": "plain_text", "text": "대상을 선택하세요"},
                            "options": [
                                {"text": {"type": "plain_text", "text": "nodegroup"}, "value": "nodegroup"},
                                {"text": {"type": "plain_text", "text": "deployment"}, "value": "deployment"},
                            ],
                        },
                        "label": {"type": "plain_text", "text": "대상 선택"},
                    },
                ],
                "submit": {"type": "plain_text", "text": "Submit"},
                "close": {"type": "plain_text", "text": "취소"},
                "private_metadata": channel_id,
            }
        )

    @app.view("modal_view3")
    def handle_modal_submission(ack, body, view, client):
        ack()

        channel_id      = view["private_metadata"]
        cluster_name    = view["state"]["values"]["cluster_block"]["cluster_select"]["selected_option"]["value"]
        action_name     = view["state"]["values"]["action_block"]["action_select"]["selected_option"]["value"]
        target_resource = view["state"]["values"]["target_block"]["target_select"]["selected_option"]["value"]

        print(f"cluster_name[{cluster_name}] action_name[{action_name}] target_resource[{target_resource}]")

        tz_kst       = pytz.timezone('Asia/Seoul')
        now          = datetime.now(tz_kst)
        current_date = now.strftime("%Y-%m-%d %H:%M:%S %Z")

        client.chat_postMessage(channel=channel_id, text=f"💡 *{action_name}::{cluster_name}.{target_resource}* : *선택*\n\n현재 시간: {current_date}")

        try:
            lambda_client = boto3.client('lambda', region_name='ap-northeast-2')
            lambda_name   = 'ClusterScaleInOut'
            target = {
                    "action": action_name,
                    "cluster_name": cluster_name,
                    "target_resource": target_resource
            }
            response = lambda_client.invoke(
                FunctionName   = lambda_name,
                InvocationType = 'RequestResponse',
                Payload=json.dumps(target))

            response_payload = json.loads(response['Payload'].read())

            client.chat_postMessage(channel=channel_id, text=f"💡 *{cluster_name}* Cluster의 *{action_name}* : *요청 성공*\n\n현재 시간: {current_date}\n\nLambda 응답: {response_payload}")

        except ClientError as e:
            client.chat_postMessage(channel=channel_id, text=f"⚠️ Lambda 호출 실패: {str(e)}")
            print(f"Error invoking Lambda function: {str(e)}")
        except Exception as e:
            client.chat_postMessage(channel=channel_id, text=f"⚠️ 오류 발생: {str(e)}")
            print(str(e))
            print(traceback.format_exc())

