from typing import List, Tuple

import torch
from loguru import logger
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
import os
import requests
        
from .external_parser import *


class HFTacticGenerator(Generator, Transformer):
    def __init__(self, **args) -> None:
        self.name = args["model"]
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.name, trust_remote_code=True
        )
        device = args["device"]
        if device == "auto":
            device = get_cuda_if_available()
        else:
            device = torch.device(device)
        logger.info(f"Loading {self.name} on {device}")
        self.model = AutoModelForCausalLM.from_pretrained(
            self.name,
            trust_remote_code=True,
            quantization_config=BitsAndBytesConfig(load_in_4bit=True),
        ).to(device)

        self.generation_args: dict[str | str] = {
            "do_sample": args["do_sample"],
            "temperature": args["temperature"],  # chat default is 0.8.
            "max_new_tokens": args["max_new_tokens"],
            "top_p": args["top_p"],  # chat default is 0.8.
            "num_return_sequences": args["num_return_sequences"],
            "output_scores": args["output_scores"],
            "output_logits": args["output_logits"],
            "return_dict_in_generate": args["return_dict_in_generate"],
        }

    def generate(self, input: str, target_prefix: str = "") -> List[Tuple[str, float]]:
        prompt = input + target_prefix
        '''prompt= 'Here is a theorom you need to prove in Lean:\n'+prompt+'\nNow you should suggest one line tactic in lean code:'
        prompt = f"""<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n"""
        '''
        prompt = pre_process_input(self.name, prompt)

        self.model = self.model.eval()
        API_URL = "https://router.huggingface.co/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {os.environ['HF_TOKEN']}",
        }
        
        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "model": "deepseek-ai/DeepSeek-Prover-V2-671B:novita",
            "temperature": self.generation_args.get("temperature", 0.6),
            "max_tokens": self.generation_args.get("max_new_tokens", 256),
            "top_p": self.generation_args.get("top_p", 0.9),
            "n": self.generation_args.get("num_return_sequences", 4),
        }
        
        try:
            response_data = requests.post(API_URL, headers=headers, json=payload).json()
            response = [choice["message"]["content"] for choice in response_data.get("choices", [])]
        except Exception as e:
            print(f"API call failed: {e}")
            return [("error", 0.0)]

        result = []
        for out in response:
            out = post_process_output(self.name, out)
            result.append((out, 1.0))  # Use default score of 1.0 since API doesn't provide scores
        result = choices_dedup(result)
        print("result", result)
        return result


if __name__ == "__main__":
    generation_kwargs = {
        "model": "deepseek-ai/DeepSeek-Prover-V2-7B",
        "temperature": 0.9,
        "max_new_tokens": 1024,
        "top_p": 0.9,
        "length_penalty": 0,
        "num_return_sequences": 64,
        "do_sample": True,
        "output_scores": True,
        "output_logits": False,
        "return_dict_in_generate": True,
        "device": "auto",
    }
    model = HFTacticGenerator(**generation_kwargs)
    model.cuda()
    print(model.generate("n : ℕ\n⊢ gcd n n = n"))
