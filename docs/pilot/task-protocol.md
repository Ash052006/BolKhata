# BolKhata Field Pilot: 10-Transaction Comparative Protocol

> **Purpose:** Measure task completion time and error rates: **BolKhata Voice** vs **Merchant's Baseline Method** (Paper Notebook or Manual App).
> **Methodology Invariant:** Stopwatch timed side-by-side. Zero synthetic measurements.

---

## The 10 Standard Test Utterances

These 10 representative transactions mirror typical Indian retail shop traffic:

| # | Spoken Utterance | Category | Ground Truth Extraction |
|---|---|---|---|
| **1** | *"Sharma ji ko dhai sau udhaar, do kilo chawal."* | Colloquial fraction (`dhai sau` = 250) + Commodity | Customer: Sharma, Amount: ₹250.00, Type: credit_sale, Items: [chawal 2kg] |
| **2** | *"Verma ji se paanch sau rupaye jama."* | Payment received | Customer: Verma, Amount: ₹500.00, Type: payment_received |
| **3** | *"Gupta ji ko dedh hazaar ka saaman udhaar."* | Colloquial multiplier (`dedh hazaar` = 1500) | Customer: Gupta, Amount: ₹1500.00, Type: credit_sale |
| **4** | *"Doo packet namak aur ek kilo cheeni, assi rupaye nagad."* | Immediate cash sale | Amount: ₹80.00, Type: cash_sale, Items: [namak 2pkt, cheeni 1kg] |
| **5** | *"Ramesh bhai ko sawa sau rupaye udhaar."* | Colloquial quarter (`sawa sau` = 125) | Customer: Ramesh, Amount: ₹125.00, Type: credit_sale |
| **6** | *"Dukaan ka bijli bill teen sau rupaye kharcha."* | Store expense | Amount: ₹300.00, Type: expense, Items: [bijli bill] |
| **7** | *"Chaudhary Sahab ko paune do sau udhaar."* | Subtractive fraction (`paune do sau` = 175) | Customer: Chaudhary, Amount: ₹175.00, Type: credit_sale |
| **8** | *"Nahi ruko, Chaudhary Sahab ko do sau pachaas likho."* | Voice correction / modification | Customer: Chaudhary, Amount: ₹250.00 (corrected) |
| **9** | *"Sharma ji ka kitna baaki hai?"* | Verbal balance inquiry | Query: customer_balance (Sharma) |
| **10** | *"Aaj kitna udhaar diya?"* | Daily summary inquiry | Query: today_udhaar |

---

## Experimental Protocol & Measurements

### Step 1: Baseline Run (Notebook or Khatabook Typing)
1. Present the transaction prompt to the merchant.
2. Start stopwatch when merchant touches pen/phone.
3. Stop stopwatch when entry is fully written or tapped save.
4. Record time in seconds ($T_{\text{manual}}$). Inspect written entry for errors.

### Step 2: BolKhata Voice Run
1. Hand the device to the merchant with BolKhata open.
2. Start stopwatch when merchant presses the Push-to-Talk button.
3. Merchant speaks the utterance and says *"Haan"* to confirm read-back.
4. Stop stopwatch when confirmation chime sounds.
5. Record time in seconds ($T_{\text{voice}}$), verbal correction count, and ASR status.

### Calculated Field Metrics
- **Speedup Factor:** $\frac{\text{Median}(T_{\text{manual}})}{\text{Median}(T_{\text{voice}})}$
- **Input Error Rate:** $\frac{\text{Uncorrected Errors}}{\text{Total Transactions}}$
- **Voice Correction Rate:** $\frac{\text{Verbal Corrections Applied}}{\text{Total Voice Turns}}$
