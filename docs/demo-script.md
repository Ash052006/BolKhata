# BolKhata 90-Second Live Demonstration Script

> **Objective:** Deliver a crisp, reproducible 90-second end-to-end demonstration of BolKhata's core loop, voice correction, offline fallback, and privacy controls.
> **Target Audience:** Hackathon Judges, Kirana Retailers, and Technical Reviewers.
> **Prerequisites:** Run `./scripts/demo_reset.sh` before presenting to ensure deterministic seed state.

---

## Demo Flow Overview (Timeline: 90 Seconds)

```
00:00 - 00:20: Step 1 — Standard Transaction with Spoken Read-Back & Verbal Confirmation
00:20 - 00:40: Step 2 — Misheard Entry Caught by Read-Back & Corrected by Voice
00:40 - 00:55: Step 3 — Network Disconnection & Graceful Offline Mode Fallback
00:55 - 01:10: Step 4 — Spoken Balance Query & Counter Privacy Quiet Mode
01:10 - 01:25: Step 5 — Closing Daily Summary ("Aaj Ka Hisaab")
01:25 - 01:30: Step 6 — One-Tap Data Ownership & DPDP Privacy Statement
```

---

## Detailed Step-by-Step Script

### Step 1: Standard Credit Sale (00:00 – 00:20)
- **Presenter Action:** Hold the large green Push-to-Talk button.
- **Presenter Speaks:**
  > *"Sharma ji ko dhai sau rupaye udhaar, aur do kilo chawal."*
- **App Processing:**
  - Fast ASR converts speech tokens.
  - S2 number parser evaluates *"dhai sau"* deterministically to **₹250.00**.
  - High-contrast confirmation card appears on screen.
- **App Speaks:**
  > *"Sharma ji, do sau pachaas rupaye udhaar, do kilo chawal. Sahi hai?"*
- **Presenter Action:** Hold Push-to-Talk button (or tap green checkmark).
- **Presenter Speaks:**
  > *"Haan, likh lo."*
- **App Result:**
  - Audible confirmation chime.
  - Entry committed to append-only ledger with SHA-256 idempotency key.
  - Sharma ji's balance instantly updates on screen.

---

### Step 2: Voice Correction Flow (00:20 – 00:40)
- **Context:** Simulate an acoustic misunderstanding or customer changing their mind.
- **Presenter Action:** Hold Push-to-Talk button.
- **Presenter Speaks:**
  > *"Verma ji ko teen sau udhaar."*
- **App Speaks:**
  > *"Verma ji, teen sau rupaye udhaar. Sahi hai?"*
- **Presenter Action:** Hold Push-to-Talk button to correct immediately.
- **Presenter Speaks:**
  > *"Nahi, teen sau nahi, teen sau pachaas likho."*
- **App Processing:**
  - Confirmation grammar detects negative refusal (*"Nahi"*).
  - Voice correction engine applies delta patch: updates amount from ₹300 $\rightarrow$ **₹350.00**.
- **App Speaks:**
  > *"Verma ji, teen sau pachaas rupaye udhaar. Sahi hai?"*
- **Presenter Speaks:**
  > *"Theek hai."*
- **App Result:**
  - Corrected entry saved. Demonstrates that shopkeepers never need to touch the keyboard.

---

### Step 3: Induced Failure Recovery: Offline Circuit Breaker (00:40 – 00:55)
- **Presenter Action:** Turn off Wi-Fi on the laptop (or unplug ethernet cable).
- **Presenter Speaks to Judges:**
  > *"In a crowded Indian bazaar, 4G networks drop constantly. Watch what happens when connectivity is severed."*
- **Presenter Action:** Hold Push-to-Talk button.
- **Presenter Speaks:**
  > *"Gupta ji se ek sau rupaye jama."*
- **App Behavior:**
  - App displays accessible yellow **"Offline Mode"** indicator banner.
  - Circuit breaker skips cloud LLM and routes immediately to local rules parser.
  - Spoken & on-screen read-back functions 100% locally.
- **Presenter Speaks:**
  > *"Haan."*
- **App Result:** Transaction saved safely in local SQLite WAL without crashing or spinning spinners.

---

### Step 4: Spoken Balance Query & Quiet Mode (00:55 – 01:10)
- **Presenter Action:** Re-enable Wi-Fi. Hold Push-to-Talk button.
- **Presenter Speaks:**
  > *"Sharma ji ka kitna baaki hai?"*
- **App Speaks:**
  > *"Sharma ji ka do sau pachaas rupaye baaki hai."*
- **Presenter Action:** Toggle the **Quiet Mode** switch on screen.
- **Presenter Speaks to Judges:**
  > *"If a customer is standing at the counter and privacy is needed, Quiet Mode displays the answer on screen while keeping the speaker silent."*
- **Presenter Speaks:**
  > *"Verma ji ka kitna baaki hai?"*
- **App Result:** Zero audio output. High-contrast screen card displays: `Verma ji: ₹350.00 udhaar baaki hai.`

---

### Step 5: Daily Digest — "Aaj Ka Hisaab" (01:10 – 01:25)
- **Presenter Action:** Hold Push-to-Talk button.
- **Presenter Speaks:**
  > *"Aaj kitna udhaar diya?"*
- **App Speaks:**
  > *"Aaj kul chhe sau rupaye ka udhaar diya gaya."*
- **Presenter Speaks:**
  > *"Aaj kitna jama hua?"*
- **App Speaks:**
  > *"Aaj kul ek sau rupaye jama huye."*

---

### Step 6: Data Ownership & DPDP Compliance (01:25 – 01:30)
- **Presenter Action:** Tap **"Export CSV"** $\rightarrow$ Instant download of standard ledger file.
- **Presenter Action:** Tap **"Statement"** $\rightarrow$ Formatted printable customer account history.
- **Presenter Concludes:**
  > *"BolKhata gives Indian shopkeepers the speed of voice, the precision of deterministic mathematics, and 100% data ownership. No cloud lock-in, zero synthetic numbers, money-safe by design."*
