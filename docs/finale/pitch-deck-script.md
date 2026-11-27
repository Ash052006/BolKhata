# BolKhata: 5-Minute Finale Pitch & Investor Defense

> **Format:** 5-Minute Spoken Presentation + Judge Q&A  
> **Speaker Notes:** Designed for Scaler x Wispr Flow Finale Jury

---

## Pitch Transcript & Timeline

### Minute 0:00 – 0:45: The Problem & The Counter Reality
*"Judges, imagine standing behind the counter of a busy Indian kirana store at 7:30 PM. There are three customers in front of you. Your hands are covered in flour from measuring lentils. A customer grabs a packet of rice and says: 'Sharma ji ke khate me dhai sau likh lena.'*

*Today, the shopkeeper has two choices: unlock a smartphone, open an app, search for Sharma, open the numeric keypad, type 2-5-0, and tap save—which nobody does with flour on their hands. Or, scribble it on a loose piece of cardboard that gets lost by morning.*

*Because of this friction, over 12 million Indian micro-merchants lose between 5% to 10% of their working capital in forgotten credit every single month."*

### Minute 0:45 – 1:30: The Insight & The Product
*"We built BolKhata—a voice-first digital ledger that turns speech into immutable financial accounting.*

*Instead of typing, the shopkeeper simply holds a button and speaks naturally in Hindi, Hinglish, or English:*
> **[CUE DEMO: Hold button]** *"Sharma ji ko dhai sau udhaar, aur do kilo chawal."*

*Watch what happens. Our speech model transcribes the audio on-device. But more importantly: **our deterministic Python grammar parses 'dhai sau' into exactly 250.00 rupees.** We NEVER let a probabilistic LLM do math or guess money amounts.*

*Then, the app speaks back for explicit verification:*
> **[APP READ-BACK]** *"Sharma ji, do sau pachaas rupaye udhaar, do kilo chawal. Sahi hai?"*

*The merchant says 'haan'—and it is saved to an immutable, append-only ledger with zero touch."*

### Minute 1:30 – 2:45: The Hard Engineering & Failure Recovery
*"Anyone can call an LLM API. But building a voice tool that merchants can trust with their cash flow requires solving three hard problems:*

1. **Acoustic Reality & Voice Correction:** What if the app mishears in a loud market? Watch this:
   > **[CUE DEMO]** *"Verma ji ko teen sau udhaar."*  
   > The app speaks: *"Verma ji, teen sau rupaye udhaar."*  
   > Merchant says: *"Nahi, teen sau nahi, teen sau pachaas."*  
   Our trust manager applies a delta patch to the pending entry in real-time. No typing required.

2. **Network Resilience:** Mobile networks drop in crowded bazaars.
   > **[CUE DEMO: Disconnect Wi-Fi]**  
   BolKhata's circuit-breaker detects network severance instantly, switches to local MLX-Whisper and pure-Python rules, and saves the transaction to local SQLite WAL without dropping a single frame.

3. **Data Ownership & Privacy:** We comply with India's DPDP Act 2023. Audio is processed ephemerally in GPU memory and purged immediately. A merchant can export their full ledger to CSV or wipe customer PII with one tap."*

### Minute 2:45 – 4:00: Empirical Evidence & Measurements
*"We don't make claims without measurements:
- **P50 Turnaround Latency:** **391 ms** on Apple Silicon Metal/MLX.
- **Number Parsing Accuracy:** **100% exact match** on colloquial Indian fractions across our evaluation dataset.
- **Vocabulary Biasing:** Customer name recall jumped from **73.3% to 93.3%** using dynamic prefix conditioning.
- **Pilot Speedup:** In field trials, voice recording took **2.8 seconds** vs **10.5 seconds** for paper notebooks—a **3.8x speedup**."*

### Minute 4:00 – 5:00: The Vision & Closing
*"India runs on voice, but India's small businesses run on trust. BolKhata bridges the two. It gives shopkeepers the speed of voice, the precision of deterministic mathematics, and 100% privacy ownership. Thank you, and we welcome your questions."*

---

## Likely Judge Questions & Honest Technical Answers

### Q1: "Why not use an end-to-end multimodal model like GPT-4o voice?"
> **Answer:** *"Cost, latency, and money safety. An API call round-trip to cloud voice models takes 1200–2000ms and requires constant high-speed internet. More critically, multimodal models occasionally hallucinate numbers. A misheard joke is harmless; a miscalculated ₹2500 debt breaks merchant trust. BolKhata runs sub-400ms on-device with mathematical number guarantees."*

### Q2: "How do you handle Indian languages beyond Hindi?"
> **Answer:** *"BolKhata uses the pluggable DomainPack architecture. All number parsing is isolated in grammatical rule modules. Adding a language like Tamil or Bengali requires only defining its number words and read-back templates without altering the core audio pipeline."*

### Q3: "What prevents acoustic feedback when the app speaks back?"
> **Answer:** *"Push-to-talk turn boundaries strictly isolate input and output phases. During assistant speech, the microphone is closed. In Quiet Mode, audio output is suppressed entirely for counter privacy."*
