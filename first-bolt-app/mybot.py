import os
import boto3
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from tabulate import tabulate

# Slack Bolt 앱 초기화
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

# "alb 라우팅 [프로파일명] [ALB 이름]" 명령어를 처리하는 함수
@app.message(r"^alb 라우팅\s*(\S+)?\s*(\S+)?")
def handle_alb_routing(message, say, context):
    profile = context["matches"][0]  # 프로파일명 추출
    alb_name = context["matches"][1]  # ALB 이름 추출

    if profile is None or alb_name is None:
        say("Please provide a profile name and ALB name. Usage: `alb 라우팅 [profile] [ALB Name]`")
        return

    try:
        # AWS 세션 생성
        session = boto3.Session(profile_name=profile)
        elbv2_client = session.client('elbv2')

        # ALB의 ARN 조회
        load_balancers = elbv2_client.describe_load_balancers(Names=[alb_name])
        alb_arn = load_balancers['LoadBalancers'][0]['LoadBalancerArn']

        # ALB의 리스너 목록 조회
        listeners = elbv2_client.describe_listeners(LoadBalancerArn=alb_arn)
        routing_info = []

        # 공통 ARN 부분 (중복 제거용)
        listener_arn_prefix = "arn:aws:elasticloadbalancing:ap-northeast-2:543945541886:listener/app/"
        target_group_arn_prefix = "arn:aws:elasticloadbalancing:ap-northeast-2:543945541886:targetgroup/"

        # 각 리스너에 대해 규칙과 라우팅 액션 조회
        for listener in listeners['Listeners']:
            listener_arn = listener['ListenerArn'].replace(listener_arn_prefix, "")
            protocol_port = f"{listener['Protocol']}:{listener['Port']}"

            rules = elbv2_client.describe_rules(ListenerArn=listener['ListenerArn'])

            for rule in rules['Rules']:
                rule_priority = rule['Priority']
                rule_arn = rule['RuleArn']

                # 규칙의 태그 조회 및 'Name' 태그 값 가져오기
                rule_tags = elbv2_client.describe_tags(ResourceArns=[rule_arn])
                rule_name = "No Name"
                for tag_description in rule_tags['TagDescriptions']:
                    for tag in tag_description['Tags']:
                        if tag['Key'] == 'Name':
                            rule_name = tag['Value']
                            break

                for action in rule['Actions']:
                    if action['Type'] == 'forward':
                        target_groups = action.get('ForwardConfig', {}).get('TargetGroups', [])
                        for tg in target_groups:
                            target_group_arn = tg['TargetGroupArn'].replace(target_group_arn_prefix, "")
                            weight = tg['Weight']
                            routing_info.append([protocol_port, listener_arn, rule_name, rule_priority, target_group_arn, weight])

        # 테이블 형식으로 정보 출력
        if routing_info:
            headers = ["Protocol:Port", "Listener ARN", "Rule Name", "Rule Priority", "Target Group ARN", "Weight"]
            table = tabulate(routing_info, headers, tablefmt="pretty")
            response = f"Routing information for ALB: {alb_name}\n\n{table}"
        else:
            response = f"No routing information found for ALB: {alb_name}"

        # 메시지 채널로 결과 전송
        say(response)

    except Exception as e:
        # 에러 발생 시 에러 메시지 전송
        say(f"Error: {str(e)}")

# Slack Socket Mode 핸들러 시작
if __name__ == "__main__":
    handler = SocketModeHandler(app, os.environ.get("SLACK_APP_TOKEN"))
    handler.start()