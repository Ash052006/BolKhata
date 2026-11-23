# BolKhata Evaluation Dataset: Recording & Annotation Guide

## 1. Purpose

This guide defines the specifications and protocol for recording and annotating audio evaluation data for BolKhata.
**No synthetic audio or fabricated transcripts are allowed** in this benchmark dataset. Real speech recorded by native speakers in authentic acoustic conditions provides the ground truth for measuring Word Error Rate (WER), Character Error Rate (CER), Real-Time Factor (RTF), and money parsing accuracy.

---

## 2. Audio Capture Specifications

Every audio file must conform to the standard BolKhata uncompressed PCM contract:
- **Container Format**: WAV (`.wav`)
- **Sampling Rate**: `16000` Hz (16 kHz)
- **Bit Depth**: `16`-bit signed integer (s16le)
- **Channels**: `1` (Mono)
- **Audio Directory**: `tests/data/eval/audio/`

### Recording Tools:
You can record directly using `sox`, `ffmpeg`, Audacity, or macOS Voice Memos / QuickTime (exported as 16kHz WAV):
```bash
# Example recording with sox
rec -r 16000 -c 1 -b 16 audio/utt_001.wav trim 0 5
```

---

## 3. Categories & Coverage Requirements

Collect a minimum of 5 distinct speakers across these 6 required categories:

### 1. `plain_hindi`
Pure Hindi spoken naturally by shopkeepers or customers.
- Examples:
  - "रमेश जी को पचास रुपये उधार दिए"
  - "सुरेश का खाता खोलो"
  - "आज का कुल कितना हिसाब हुआ"

### 2. `plain_english`
Standard Indian English commerce phrasing.
- Examples:
  - "Add twenty five rupees credit for Sharma"
  - "Payment received two hundred rupees cash"
  - "What is the balance for Verma"

### 3. `hinglish`
Everyday code-switched Hindi-English phrasing used in Indian retail.
- Examples:
  - "Gupta ji ke account me do sau rupaye add kar do"
  - "Ramesh ka balance kitna bacha hai"
  - "Cash payment aayi hai paanch sau rupaye ki"

### 4. `number_heavy`
Stress testing the deterministic spoken number parser with Indian idioms and multipliers.
- Must include:
  - `dhai sau` (250)
  - `derh hazaar` (1500)
  - `sawa sau` (125)
  - `sadhe teen sau` (350)
  - `paune do sau` (175)
  - `pachees sau` (2500)
  - `teen hazaar paanch sau` (3500)
  - Compound rupees and paise: `das rupaye pachaas paise`

### 5. `noisy_shop`
Utterances recorded in realistic shop environments with background chatter, traffic horns, ceiling fans, or refrigerator hum.
- Tagged with `noise_level: "high"` or `"medium"`.

### 6. `correction`
Voice correction dialogues modifying a previous utterance or amount.
- Examples:
  - "Nahi teen sau nahi teen sau pachaas rupaye"
  - "Verma nahi Sharma ji ke khate me likho"
  - "Ruko kal ka nahi aaj ka likho"

---

## 4. Metadata Schema

All metadata is stored in `tests/data/eval/metadata.json` (or `metadata.jsonl`). Each entry conforms to the following JSON schema:

```json
[
  {
    "id": "utt_0001",
    "audio_file": "audio/utt_0001.wav",
    "reference": "dhai sau rupaye udhaar likho",
    "language": "hinglish",
    "speaker_id": "spk_01",
    "noise_level": "low",
    "category": "number_heavy",
    "duration_seconds": 2.45
  }
]
```

### Allowed Values:
- `language`: `"hindi"`, `"english"`, `"hinglish"`
- `noise_level`: `"low"`, `"medium"`, `"high"`
- `category`: `"plain_hindi"`, `"plain_english"`, `"hinglish"`, `"number_heavy"`, `"noisy_shop"`, `"correction"`

---

## 5. Dataset Validation

Before running benchmarks, run the automated dataset validator:
```bash
python scripts/validate_eval_dataset.py --metadata tests/data/eval/metadata.json
```
The validator verifies file presence, sample rate (16kHz), mono channels, 16-bit depth, duration consistency, and schema validity.
