import requests
import json
import time


def call_agent_chat(history, character, lang="中文", server_url=""):
    payload = {
        "history": history,
        "lang": lang,
        "character": character
    }
    headers = {
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(server_url, data=json.dumps(payload), headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"调用接口失败: {e}")
        return None


def call_test_latency(server_url=""):
    try:
        response = requests.post(server_url, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"调用接口失败: {e}")
        return None


if __name__ == "__main__":
    for i in range(100):
        start_time = time.time()
        history = [{"role": "user", "content": f"第{i}次调用接口"}]
        character = "你是一个智能客服机器人，请根据用户的问题给出回答"
        result = call_agent_chat(history, character, lang="")
        end_time = time.time()
        if end_time - start_time > 0:
            print(f"第{i}次调用接口，耗时：{end_time - start_time}秒，超时")
            print("接口返回结果：")
            print(json.dumps(result, ensure_ascii=False, indent=2))
        time.sleep(2)

