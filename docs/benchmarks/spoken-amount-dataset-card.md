# Dataset Card: BolKhata Spoken Indian Amounts Benchmark (BSIAB-v0)

- **Dataset Identifier:** `BSIAB-v0.1.0`
- **Domain:** Spoken Indian Monetary Amounts & Kirana Transaction Speech
- **Languages:** Hindi, Indian English, Hinglish, Bengali (বাংলা)
- **Status:** Research Benchmark Specification (Prepared, Not Distributed)

---

## 1. Dataset Purpose & Motivation

Spoken numbers in India present unique acoustic and linguistic challenges for global Automatic Speech Recognition (ASR) foundation models:
1. **Colloquial Fractional Bases:** Colloquial prefixes alter base numbers by multipliers (`dhai sau` = 250, `derh hajaar` = 1500, `sawa do sau` = 225, `sadhe teen sau` = 350, `paune do sau` = 175).
2. **Indian Numbering Scale:** Grouping by hundreds (`sau`), thousands (`hazaar`), hundred thousands (`lakh`), and ten millions (`crore`) rather than Western millions and billions.
3. **High Ambient Acoustic Noise:** Kirana shops operate on busy Indian commercial streets with continuous traffic horns, ceiling fans, ambient customer bargaining, and counter reverberation.
4. **Code-Switching:** Rapid inter-sentential and intra-sentential transitions between Indic dialects and English numerals (*"Verma ji ko five hundred cash diya"*).

`BSIAB-v0` provides an evaluation benchmark to systematically test whether speech models preserve financial accuracy.

---

## 2. Dataset Schema

Each utterance entry in `manifest.json` conforms to the following schema:

```json
{
  "utterance_id": "UTT_HI_SPK01_0042",
  "speaker_id": "SPK_01",
  "language": "hi",
  "audio_filepath": "audio/UTT_HI_SPK01_0042.wav",
  "duration_seconds": 3.42,
  "sampling_rate_hz": 16000,
  "channels": 1,
  "noise_condition": "busy_kirana_market",
  "snr_estimate_db": 14.2,
  "raw_transcript": "dhai sau rupaye udhaar",
  "normalized_transcript": "250 rupaye udhaar",
  "ground_truth_amount": 250.0,
  "currency": "INR",
  "number_words_canonical": "do sau pachaas",
  "contains_colloquial_fraction": true,
  "fraction_type": "dhai"
}
```

---

## 3. Data Collection & Speaker Coding

- **Speaker Anonymization:** Speakers are strictly assigned non-identifying pseudonym codes (`SPK_01`, `SPK_02`, ..., `SPK_10`). Zero biometric or demographic identifiers (names, addresses, phone numbers, exact store locations) are stored.
- **Recording Protocol:** Push-to-talk capture at 16 kHz, 16-bit signed PCM mono, using standard mobile devices (Android and iOS).
- **Acoustic Environments:**
  1. `quiet_counter`: Background noise $\le 45\text{ dBA}$, minimal ambient interference.
  2. `busy_kirana_market`: Background street noise $65\text{--}78\text{ dBA}$ (traffic horns, shop chatter, metal shutters).

---

## 4. Anonymization & Zero-PII Policy

Before packaging, every utterance transcript is passed through the automated BolKhata sanitization gate:
1. **Name Scrubbing:** Utterances containing customer names (*"Sharma ji"*, *"Verma"*, etc.) are filtered out or sanitized to neutral placeholders (*"Customer A"*).
2. **Phone Number Scrubbing:** Any sequence matching Indian 10-digit mobile patterns (`\b[6-9]\d{9}\b`) is rejected from the benchmark.
3. **Audio Verification:** PII phrases are audited by manual listen-through prior to split assignment.

---

## 5. Limitations & Threats to Validity

1. **Sample Size:** v0 release contains limited speaker diversity (target 5–10 speakers).
2. **Regional Accent Representation:** Primary dialects reflect Delhi/NCR, Uttar Pradesh, and West Bengal. South Indian Indic languages (Tamil, Telugu, Kannada) are planned for future iterations.
3. **Microphone Variability:** Built-in mobile microphones exhibit varied automatic gain control (AGC) characteristics.
