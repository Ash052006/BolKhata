# BolKhata ASR Text Normalization Policy

## 1. Overview and Objective

In voice-first applications for Indian commerce (Kirana stores), Automatic Speech Recognition (ASR) outputs must be evaluated fairly against ground-truth human annotations. Indian speech frequently mixes Hindi, English, and local dialects (Hinglish), featuring:
1. Multiple valid Latin-script transliterations for the same word (e.g. `paanch` vs `panch`, `hazaar` vs `hazar`).
2. Dual script usage (Devanagari script vs Roman script).
3. Punctuation variations and Indic dandas (`।`, `॥`).
4. Numeral variations (digits like `250` vs words like `dhai sau`).

To guarantee scientific reproducibility and fair error measurement without masking actual acoustic or semantic transcription failures, BolKhata defines a formal text normalization policy with two explicit modes:
- **Strict Mode**: Standard baseline for lexical exactness.
- **Transliteration-Tolerant Mode**: Phonetically regularized mode for evaluating colloquial Hinglish without penalizing valid transliteration variations.

Both reference transcripts and ASR hypothesis outputs pass through the identical normalization function prior to computing Word Error Rate (WER) or Character Error Rate (CER).

---

## 2. Normalization Transformations

### 2.1 Unicode Normalization
All text is first normalized to Unicode Canonical Decomposition followed by Canonical Composition (**NFC** via `unicodedata.normalize('NFC', text)`). This prevents code-point mismatches caused by combining diacritics.

### 2.2 Casing
All Latin characters are converted to lowercase (`text.lower()`). Devanagari script is unaffected by casing operations.

### 2.3 Punctuation and Sentence Boundaries
All punctuation marks are stripped and replaced with whitespace:
- ASCII punctuation: `.,;:!?-/"'()[]{}`
- Unicode typography: `« » “ ” ‘ ’ \` ~ @ # $ % ^ & * + = | < > \`
- Indic dandas: Purna viram `।` (U+0964) and Deergh viram `॥` (U+0965).

### 2.4 Whitespace
All consecutive whitespaces, tabs (`\t`), and newlines (`\n`, `\r`) are collapsed into a single ASCII space (`\x20`). Leading and trailing spaces are trimmed.

---

## 3. Strict Mode vs Tolerant Mode

| Dimension | Strict Mode | Transliteration-Tolerant Mode |
| :--- | :--- | :--- |
| **Casing** | Lowercase | Lowercase |
| **Punctuation & Danda** | Stripped | Stripped |
| **Whitespace** | Collapsed and trimmed | Collapsed and trimmed |
| **Devanagari Numerals** | Preserved (e.g. `१२५`) | Converted to ASCII digits (`125`) |
| **Devanagari Nuktas** | Preserved (e.g. `ज़`, `फ़`) | Normalized to base glyphs (e.g. `ज`, `फ`) |
| **Hinglish Spelling** | Preserved (exact word forms) | Mapped via canonical phonetic dictionary |
| **Currency Words** | Preserved | Mapped to canonical `rupaye` |
| **Unit Abbreviations** | Preserved | Mapped to canonical base unit (e.g. `kgs` $\to$ `kg`) |

### 3.1 Tolerant Mode Phonetic Equivalence Table
Tolerant mode canonicalizes common phonetic variants:
- Numbers: `paanch` / `paan` $\to$ `panch`, `chaar` $\to$ `char`, `saat` $\to$ `sat`, `aath` $\to$ `ath`, `chhe` / `chheh` $\to$ `che`, `das` / `duss` $\to$ `dus`, `hazaar` $\to$ `hazar`, `dhaai` $\to$ `dhai`, `derh` / `deedh` $\to$ `dedh`, `saadhe` $\to$ `sadhe`, `pachees` / `pachhees` $\to$ `pachis`, `pachaas` $\to$ `pachas`.
- Currency: `rupee`, `rupees`, `rupaya`, `rupay`, `rs`, `₹`, `inr` $\to$ `rupaye`.
- Units: `kilos`, `kilogram`, `kilograms` $\to$ `kg`, `gm`, `gms`, `grams` $\to$ `gram`, `liter`, `litres` $\to$ `litre`, `packets`, `pkts` $\to$ `packet`.

---

## 4. Evaluation Application

In all evaluation pipelines:
$$\text{Ref}_{\text{norm}} = \text{normalize\_text}(\text{Ref}, \text{mode})$$
$$\text{Hyp}_{\text{norm}} = \text{normalize\_text}(\text{Hyp}, \text{mode})$$
$$\text{WER} = \frac{S + D + I}{N(\text{Ref}_{\text{norm}})}$$

Where $S$ is substitutions, $D$ is deletions, $I$ is insertions, and $N$ is total word count of $\text{Ref}_{\text{norm}}$.
All benchmark reports declare which mode was utilized when citing WER and CER.
