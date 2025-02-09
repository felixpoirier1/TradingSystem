import aiohttp

async def fetch_from_ollama(prompt: str, model: str = "deepseek-r1", api_url: str = "http://localhost:11434/api/generate", headers: dict = None) -> str:
    """
    Send a prompt to the Ollama model and return the response.
    """
    headers = headers or {"Content-Type": "application/json"}
    payload = {"model": model, "prompt": prompt}

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(api_url, headers=headers, json=payload) as response:
                if response.status == 200:
                    result = []
                    # Process the NDJSON response stream
                    async for line in response.content:
                        print(line)
                        if line:
                            try:
                                json_line = line.decode("utf-8").strip()
                                result.append(json_line)
                            except Exception as e:
                                raise RuntimeError(f"Error decoding line: {line}, {e}")
                    return "\n".join(result)
                else:
                    error = await response.text()
                    raise RuntimeError(f"Ollama API Error: {response.status} - {error}")
        except Exception as e:
            raise RuntimeError(f"Error in fetch_from_ollama: {e}")


import asyncio

async def execute_tasks(tasks: list):
    """
    Execute multiple asynchronous tasks concurrently.
    """
    try:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results
    except Exception as e:
        raise RuntimeError(f"Error executing tasks: {e}")


import base64

def encrypt_string(string: str, key: bytes) -> str:
    return base64.b64encode(string.encode('utf-8') + key).decode('utf-8')

def decrypt_string(encrypted: str, key: bytes) -> str:
    decoded = base64.b64decode(encrypted.encode('utf-8'))
    return decoded.decode('utf-8').replace(key.decode('utf-8'), "")


from functools import wraps

def handle_error(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            print(f"Error in {func.__name__}: {e}")
            raise
    return wrapper


async def start_ollama_chat():
    """
    Start a chat loop with Ollama.
    """
    while True:
        user_input = input("Type your question (or 'exit' to quit): ")
        if user_input.lower() == "exit":
            print("Exiting chat...")
            break

        try:
            response = await fetch_from_ollama(prompt=user_input)
            # print("Ollama Response:", response)
        except Exception as e:
            print(f"Error during communication: {e}")

        await asyncio.sleep(1)

async def process_response(data: dict):
    """
    Process the response from Ollama and return it.
    """
    try:
        response = await fetch_from_ollama(prompt=data["prompt"], model=data.get("model", "deepseek-r1"))
        return response
    except Exception as e:
        raise RuntimeError(f"Error processing response: {e}")

from datetime import datetime

def log_operation(operation_name: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] Operation '{operation_name}' started.")

def log_completion(operation_name: str, status: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] Operation '{operation_name}' completed with status: {status}.")


if __name__ == "__main__":
    asyncio.run(start_ollama_chat())
