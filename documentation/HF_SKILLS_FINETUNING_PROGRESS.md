# HF Skills Fine-Tuning Progress

**Purpose**: Track progress on fine-tuning domain-specific models for NSW planning compliance using Hugging Face Skills.

**Reference**: https://huggingface.co/blog/hf-skills-training

---

## Overview

Fine-tuning small open-source models (1-7B parameters) on our provision data to:
1. Reduce inference costs by 100x ($0.01/query → $0.0001/query)
2. Improve domain-specific accuracy (generic LLM ~70% → fine-tuned ~95%)
3. Enable edge deployment (GGUF for on-device inference)

---

## Phase 1: Training Data Generation ✅ COMPLETE

**Date**: 2025-12-13

### Script Created
`export_provisions_for_hf_training.py`

### Training Data Generated

| Metric | Value |
|--------|-------|
| Source provisions | 2,000 |
| Total training pairs | 13,599 |
| Training set | 12,239 pairs (90%) |
| Validation set | 1,360 pairs (10%) |

### Task Distribution

| Task Type | Count | Purpose |
|-----------|-------|---------|
| Q&A | 10,000 | Answer questions about provisions |
| Classification | 3,393 | Categorize by topic/provision type |
| Value Extraction | 206 | Extract numeric measurements |
| Compliance Check | 0 | Needs setback-specific training data |

### Output Files
```
training_data/
├── train_20251213_035220.jsonl
├── val_20251213_035220.jsonl
└── metadata_20251213_035220.json
```

### Training Data Format
```json
{
  "instruction": "What are the setback requirements for dwelling house in R2 zone?",
  "input": "",
  "output": "The minimum front setback is 5.5 metres...",
  "source_id": 12345,
  "task_type": "qa"
}
```

---

## Phase 2: Upload to Hugging Face ⏳ PENDING

### Steps
```bash
# 1. Login to Hugging Face
huggingface-cli login

# 2. Create dataset repository
huggingface-cli repo create compliance-provisions-train --type dataset

# 3. Upload training files
cd training_data
huggingface-cli upload YOUR_USERNAME/compliance-provisions-train .
```

### Status
- [ ] HF account configured
- [ ] Dataset repo created
- [ ] Training files uploaded
- [ ] Dataset card written

---

## Phase 3: Fine-Tune Model ⏳ PENDING

### Target Models (in priority order)

| Model | Size | Est. Cost | Use Case |
|-------|------|-----------|----------|
| Qwen3-1.7B | 1.7B | ~$15 | Primary: provision Q&A |
| Qwen3-0.6B | 0.6B | ~$5 | Test run, edge deployment |
| Qwen3-VL-2B | 2B | ~$40 | Vision: aerial imagery analysis |

### HF Skills Commands

**Test run (cheap):**
```
Fine-tune Qwen3-0.6B on YOUR_USERNAME/compliance-provisions-train
with SFT, 1 epoch, cosine learning rate
```

**Production run:**
```
Fine-tune Qwen3-1.7B on YOUR_USERNAME/compliance-provisions-train
with SFT, 3 epochs, cosine learning rate, batch size 8
```

### Status
- [ ] HF Skills MCP installed in Claude Code
- [ ] Test run completed (0.6B model)
- [ ] Production run completed (1.7B model)
- [ ] Model evaluation metrics recorded

---

## Phase 4: Deploy Model ⏳ PENDING

### Deployment Options

| Option | Cost | Latency | Best For |
|--------|------|---------|----------|
| HF Inference Endpoints | $0.001/query | 200-500ms | Production API |
| GGUF + Local | $0 | 50-100ms | Edge/offline |
| Replicate | $0.0005/query | 300-800ms | Burst traffic |

### Commands

**Deploy to HF Inference:**
```
Deploy my fine-tuned model to HF Inference with auto-scaling
```

**Convert to GGUF:**
```
Convert my fine-tuned model to GGUF with Q4_K_M quantization
```

### Status
- [ ] Model deployed to HF Inference
- [ ] GGUF version created
- [ ] API integration tested
- [ ] Latency benchmarks recorded

---

## Phase 5: Integration ⏳ PENDING

### Integration Points

1. **Compliance Engine API**
   - Replace Claude API calls with fine-tuned model for provision lookups
   - Keep Claude for complex reasoning, edge cases

2. **Frontend**
   - Real-time provision search
   - Classification suggestions

3. **Vision Agents (future)**
   - On-device compliance checking with GGUF model

### Status
- [ ] API endpoint created for fine-tuned model
- [ ] Fallback to Claude for low-confidence responses
- [ ] A/B test framework set up
- [ ] Production deployment

---

## Cost Tracking

| Phase | Estimated | Actual | Notes |
|-------|-----------|--------|-------|
| Training data gen | $0 | $0 | Local compute |
| Test fine-tune (0.6B) | $5 | - | |
| Production fine-tune (1.7B) | $15-25 | - | |
| HF Inference (monthly) | $50-100 | - | 10K queries/month |
| **Total setup** | **$70-130** | - | |

---

## Performance Metrics (to be filled)

### Accuracy

| Task | Generic LLM | Fine-tuned | Improvement |
|------|-------------|------------|-------------|
| Provision Q&A | ~70% | - | - |
| Classification | ~60% | - | - |
| Value Extraction | ~50% | - | - |

### Latency

| Deployment | p50 | p95 | p99 |
|------------|-----|-----|-----|
| Claude API | 1.5s | 3s | 5s |
| HF Inference | - | - | - |
| GGUF Local | - | - | - |

---

## Notes & Learnings

### 2025-12-13
- Created training data export script
- Generated 13,599 training pairs from 2,000 provisions
- Q&A pairs dominate (10K) - good for primary use case
- Compliance check pairs = 0 - need to enhance with setback-specific data
- Value extraction pairs = 206 - limited by provisions with clear numeric values

### Next Session
1. Upload training data to Hugging Face
2. Run test fine-tune with Qwen3-0.6B
3. Evaluate results before full training run

---

*Last updated: 2025-12-13*
