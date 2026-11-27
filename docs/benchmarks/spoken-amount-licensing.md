# Open Spoken-Amount Benchmark: Licensing Analysis & Legal Review Register

> **Benchmark:** BolKhata Spoken Indian Amounts Benchmark (`BSIAB-v0`)
> **Status:** Legal Evaluation & Pre-Publication Review
> **Repository:** BolKhata (बोलखाता)

---

## 1. Dual-Licensing Architecture Analysis

Voice benchmark datasets comprise two distinct legal asset classes:
1. **Metadata & Text Annotations:** Ground-truth amounts, transcripts, token alignments, and phonetic labels.
2. **Audio Acoustic Waveforms:** Voice recordings containing inherent human biometric properties.

### Recommended Dual-License Structure:

| Asset Layer | Recommended License | Rationale | Permitted Uses |
|---|---|---|---|
| **Annotations, Transcripts & Manifests** | **Creative Commons Attribution 4.0 International (CC-BY 4.0)** | Maximizes scientific utility. Allows researchers and industry labs to benchmark models, cite the dataset, and build derivative test suites. | Commercial & non-commercial use with attribution. |
| **Raw Voice Audio Waveforms** | **Creative Commons Attribution-NonCommercial-NoDerivatives 4.0 (CC-BY-NC-ND 4.0)** OR **OpenRAIL-M (Responsible AI License)** | Protects kirana shopkeepers from voice cloning, deepfake generation, or commercial voice advertisement harvesting, while enabling non-commercial academic speech research. | Non-commercial research evaluation only; no voice-synthesis derivatives permitted. |

---

## 2. Risk Matrix & Ethical Safeguards

1. **Voice Synthesis Abuse Risk:**
   - *Risk:* Third parties using shopkeeper voice samples to train automated voice-cloning models or financial fraud bots.
   - *Mitigation:* Audio clips are segmented strictly to brief monetary utterances ($< 4$ seconds). Utterances lack continuous phonetic variation required for text-to-speech speaker cloning.
2. **PII Infiltration Risk:**
   - *Risk:* Spoken shopkeeper audio containing customer names (*"Sharma ji"*) or phone numbers accidentally leaking into open datasets.
   - *Mitigation:* `scripts/package_benchmark.py` executes automated regex and named-entity scanning. Any utterance matching an entity pattern is automatically quarantined and omitted from packaging.

---

## 3. Checklist for Independent Legal Counsel Review

Prior to making the benchmark publicly accessible on GitHub or Hugging Face, the repository owner must review the following questions with legal counsel:
- [ ] Does audio collection from sole proprietorship kirana stores comply with DPDP Act 2023 exemptions for research and statistical analysis?
- [ ] Is verbal consent recorded at 16 kHz audio acceptable as verifiable consent under Indian law?
- [ ] Does releasing audio under CC-BY-NC-ND offer enforceable remedies against unauthorized voice scraping in cross-border jurisdictions?
