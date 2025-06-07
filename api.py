from openai import OpenAI

client = OpenAI(
    api_key="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",
    base_url="https://api.groq.com/openai/v1"
)

def conversar_com_assistente(prompt_usuario):
    try:
        resposta = client.chat.completions.create(
            model="meta-llama/llama-4-maverick-17b-128e-instruct",
            messages=[
                {"role": "system", "content": "Você é um assistente útil e inteligente."},
                {"role": "user", "content": prompt_usuario}
            ],
            temperature=0.7
        )
        return resposta.choices[0].message.content.strip()

    except Exception as e:
        return f"Erro: {e}"