from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Any
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
os.environ.setdefault('HF_ENDPOINT', 'https://hf-mirror.com')
DEFAULT_CUDA_MODEL = 'unsloth/Qwen3-0.6B-unsloth-bnb-4bit'
DEFAULT_CPU_MODEL = 'Qwen/Qwen3-0.6B'

@dataclass
class ProbeOutput:
    poem_id: str
    text: str
    input_ids: torch.Tensor
    tokens: list[str]
    attentions: tuple[torch.Tensor, ...]
    hidden_states: tuple[torch.Tensor, ...]
    model_name: str
    device: str
    n_layers: int
    n_heads: int

@dataclass
class ProbeModel:
    tokenizer: Any
    model: Any
    model_name: str
    device: str

    @property
    def n_layers(self) -> int:
        cfg = self.model.config
        return int(getattr(cfg, 'num_hidden_layers', getattr(cfg, 'n_layer', 0)))

    @property
    def n_heads(self) -> int:
        cfg = self.model.config
        return int(getattr(cfg, 'num_attention_heads', getattr(cfg, 'n_head', 0)))

def resolve_model_name(model_name: str | None=None) -> tuple[str, bool]:
    if model_name:
        use_4bit = 'bnb-4bit' in model_name.lower() or 'unsloth' in model_name.lower()
        if use_4bit and (not torch.cuda.is_available()):
            print(f'[probe] CUDA unavailable; ignoring 4bit model {model_name!r}, falling back to {DEFAULT_CPU_MODEL}')
            return (DEFAULT_CPU_MODEL, False)
        return (model_name, use_4bit and torch.cuda.is_available())
    if torch.cuda.is_available():
        return (DEFAULT_CUDA_MODEL, True)
    print(f'[probe] CUDA unavailable; using CPU model {DEFAULT_CPU_MODEL}')
    return (DEFAULT_CPU_MODEL, False)

def load_probe_model(model_name: str | None=None) -> ProbeModel:
    resolved, use_4bit = resolve_model_name(model_name)
    print(f'[probe] Loading {resolved} (4bit={use_4bit})...')
    tokenizer = AutoTokenizer.from_pretrained(resolved, trust_remote_code=True)
    load_kwargs: dict[str, Any] = {'trust_remote_code': True, 'attn_implementation': 'eager'}
    if use_4bit:
        load_kwargs['device_map'] = 'auto'
        try:
            from transformers import BitsAndBytesConfig
            load_kwargs['quantization_config'] = BitsAndBytesConfig(load_in_4bit=True)
        except Exception:
            pass
    elif torch.cuda.is_available():
        load_kwargs['dtype'] = torch.float16
        load_kwargs['device_map'] = 'auto'
    else:
        load_kwargs['dtype'] = torch.float32
        load_kwargs['device_map'] = 'cpu'
    model = AutoModelForCausalLM.from_pretrained(resolved, **load_kwargs)
    model.config.output_attentions = True
    model.config.output_hidden_states = True
    model.eval()
    try:
        device = str(next(model.parameters()).device)
    except StopIteration:
        device = 'cpu'
    print(f'[probe] Ready on {device}; layers={model.config.num_hidden_layers}')
    return ProbeModel(tokenizer=tokenizer, model=model, model_name=resolved, device=device)

@torch.inference_mode()
def run_probe(probe: ProbeModel, poem_id: str, text: str) -> ProbeOutput:
    text = text.replace('\r\n', '\n').rstrip() + '\n'
    encoded = probe.tokenizer(text, return_tensors='pt', add_special_tokens=True)
    encoded = {k: v.to(probe.device) for k, v in encoded.items()}
    outputs = probe.model(**encoded, output_attentions=True, output_hidden_states=True)
    input_ids = encoded['input_ids'][0].detach().cpu()
    tokens = probe.tokenizer.convert_ids_to_tokens(input_ids.tolist())
    attentions = tuple((a[0].detach().float().cpu() for a in outputs.attentions))
    hidden_states = tuple((h[0].detach().float().cpu() for h in outputs.hidden_states))
    return ProbeOutput(poem_id=poem_id, text=text, input_ids=input_ids, tokens=tokens, attentions=attentions, hidden_states=hidden_states, model_name=probe.model_name, device=probe.device, n_layers=len(attentions), n_heads=int(attentions[0].shape[0]) if attentions else probe.n_heads)
