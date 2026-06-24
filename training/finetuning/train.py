"""
Module 4: QLoRA Fine-Tuning — Llama 3 8B
Usage: python train.py --config configs/qlora_llama3_8b.yaml
"""
import os
import sys
import yaml
import torch
from dataclasses import dataclass
from pathlib import Path
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    BitsAndBytesConfig,
)
from peft import LoraConfig, get_peft_model, TaskType, prepare_model_for_kbit_training
from trl import SFTTrainer


@dataclass
class TrainConfig:
    model_name: str = "meta-llama/Meta-Llama-3-8B-Instruct"
    train_file: str = "data/splits/train.jsonl"
    val_file: str = "data/splits/validation.jsonl"
    output_dir: str = "checkpoints/llama3-8b-ekllm"
    # LoRA
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    target_modules: list = None
    # Training
    num_epochs: int = 3
    per_device_train_batch_size: int = 2
    gradient_accumulation_steps: int = 8
    learning_rate: float = 2e-4
    warmup_ratio: float = 0.05
    max_seq_length: int = 2048
    # QLoRA / quantization
    use_4bit: bool = True
    bnb_4bit_compute_dtype: str = "bfloat16"
    bnb_4bit_quant_type: str = "nf4"
    use_nested_quant: bool = True
    # HuggingFace
    hf_token: str = ""

    def __post_init__(self):
        if self.target_modules is None:
            self.target_modules = ["q_proj", "k_proj", "v_proj", "o_proj",
                                    "gate_proj", "up_proj", "down_proj"]


def format_prompt(example: dict) -> str:
    return (
        f"<|begin_of_text|><|start_header_id|>user<|end_header_id|>\n"
        f"{example['instruction']}\n{example.get('input', '')}"
        f"<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n"
        f"{example['output']}<|eot_id|>"
    )


def load_model_and_tokenizer(cfg: TrainConfig):
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=cfg.use_4bit,
        bnb_4bit_quant_type=cfg.bnb_4bit_quant_type,
        bnb_4bit_compute_dtype=getattr(torch, cfg.bnb_4bit_compute_dtype),
        bnb_4bit_use_double_quant=cfg.use_nested_quant,
    )
    model = AutoModelForCausalLM.from_pretrained(
        cfg.model_name,
        quantization_config=bnb_config,
        device_map="auto",
        token=cfg.hf_token or None,
        torch_dtype=torch.bfloat16,
        attn_implementation="flash_attention_2",
    )
    model = prepare_model_for_kbit_training(model)
    tokenizer = AutoTokenizer.from_pretrained(cfg.model_name, token=cfg.hf_token or None)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"
    return model, tokenizer


def apply_lora(model, cfg: TrainConfig):
    lora_config = LoraConfig(
        r=cfg.lora_r,
        lora_alpha=cfg.lora_alpha,
        target_modules=cfg.target_modules,
        lora_dropout=cfg.lora_dropout,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
    )
    return get_peft_model(model, lora_config)


def main(config_path: str | None = None):
    cfg = TrainConfig()
    if config_path:
        with open(config_path) as f:
            overrides = yaml.safe_load(f)
        for k, v in overrides.items():
            setattr(cfg, k, v)

    model, tokenizer = load_model_and_tokenizer(cfg)
    model = apply_lora(model, cfg)
    model.print_trainable_parameters()

    dataset = load_dataset("json", data_files={
        "train": cfg.train_file,
        "validation": cfg.val_file,
    })

    training_args = TrainingArguments(
        output_dir=cfg.output_dir,
        num_train_epochs=cfg.num_epochs,
        per_device_train_batch_size=cfg.per_device_train_batch_size,
        per_device_eval_batch_size=2,
        gradient_accumulation_steps=cfg.gradient_accumulation_steps,
        learning_rate=cfg.learning_rate,
        warmup_ratio=cfg.warmup_ratio,
        bf16=True,
        logging_steps=10,
        eval_strategy="steps",
        eval_steps=100,
        save_strategy="steps",
        save_steps=200,
        load_best_model_at_end=True,
        report_to="none",
        gradient_checkpointing=True,
        optim="paged_adamw_32bit",
    )

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset["train"],
        eval_dataset=dataset["validation"],
        formatting_func=format_prompt,
        max_seq_length=cfg.max_seq_length,
        args=training_args,
    )

    trainer.train()
    trainer.save_model(cfg.output_dir)
    tokenizer.save_pretrained(cfg.output_dir)
    print(f"Model saved to {cfg.output_dir}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
