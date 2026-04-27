# Synthetic / training data

- `seed_agent_examples.jsonl`: вручную подготовленные ground-truth примеры (Cursor agent), подходят как цели для QLoRA.
- `generated.jsonl`: генерируется скриптом `scripts/generate_synthetic_dataset.py`; внутри только детерминированные вариации проверенных шаблонов (без LLM-разметки).

Не используйте ответы локальной `Ollama` как training labels.
