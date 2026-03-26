from openai import AzureOpenAI


class AzureGPTClient:
    def __init__(self):
        self.client = AzureOpenAI(
            api_key="",
            api_version="",
            azure_endpoint=""
        )

    def get_response(self, chat_history):
        completion = self.client.chat.completions.create(
            model="",
            messages=chat_history,
            # temperature=0.1,
            # top_p=0.9,
            # max_tokens=1000,
            # stream=False
        )
        raw_response = completion.choices[0].message.content
        return raw_response


if __name__ == "__main__":
    import time

    client = AzureGPTClient()
    time_start = time.time()
    a = client.get_response([{"role": "user", "content": "你好"}])
    print(a)
    time_end = time.time()
    print(f"Time taken: {(time_end - time_start)} seconds")

