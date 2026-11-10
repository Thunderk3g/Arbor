# Model selection, local-vs-hosted tradeoffs, privacy gateways, and cost/hardware budgets for a solo self-hosted security agent

> **Retrieval date for everything below: 2026-11-10** (Anthropic price table: bundled reference cached 2026-11-03).
>
> **Read this before using any number.** In this session page fetches were blocked by the network allowlist (openai.com, ai.google.dev and aisi.gov.uk all failed to resolve), and the web-search budget ran out before the last batch of queries. Every web-sourced figure below therefore comes from **search-result summaries, not from pages I opened**. Where the search summary did not say which of several returned pages held a number, I say "attribution not confirmed". Treat prices as indicative and re-check the linked official page before budgeting.
>
> Labels: **PROVEN** = measured in a primary paper, official page or official evaluation. **PROMISING** = measured but narrow, self-reported, or from one source. **HYPE** = claimed without a checkable measurement, or contradicted by measurements.

---

## 1. Frontier vs small models on security tasks: how big is the gap, and what routes where?

### Takeaway
The gap is small on single-step knowledge and classification tasks (an 8B security-tuned model lands within a few points of a 70B general model on CTI multiple-choice and CVE-to-CWE mapping) and very large on multi-step agentic work (small models score roughly a quarter to a third of the best model on incident investigation, and exploit development separates even adjacent frontier generations by two orders of magnitude). Route by "how many dependent steps", not by "is it security".

### Routing table (synthesis; evidence rows are cited in the findings below)

| Task | Volume | Recommended tier | Why | Label |
|---|---|---|---|---|
| Log dedupe, templating, baseline diffs, threshold checks | Very high | No LLM (Drain3-style templating, deterministic rules) | Nothing to reason about; LLM cost should not scale with log volume | PROVEN as practice; no measured LLM-savings study found (see §8) |
| Single-event alert triage, severity classification, short summaries | High | Small model: hosted small tier, or local 8-14B with schema-constrained output | Single-step; small models do well on tool selection and CTI multiple choice | PROMISING |
| ATT&CK / CWE mapping, IOC and entity extraction | Medium | 8B security-tuned model or a hosted small/mid model with retrieval | 8B security models match 70B general models on CTIBench mapping tasks | PROMISING |
| Multi-step incident investigation (query, pivot, correlate) | Low | Hosted mid tier; frontier for hard cases | Small models are "nearly unusable" on ExCyTIn-Bench | PROVEN |
| Detection-rule authoring (Sigma etc.) | Low | Hosted mid tier plus a test harness against replayed telemetry | Larger models were measurably better at rule-to-technique mapping | PROMISING |
| Root-cause analysis, patch writing | Low | Frontier | AIxCC-class systems rely on frontier models; even they are "far from reliable" on CVE patching | PROVEN |
| Exploit development, self-pentest / red-team runs | Very low | Frontier, under a vendor cyber-verification programme; large open-weight model via API as fallback | Largest measured gap of any task; hosted models gate this work behind classifiers | PROVEN (gap); local 8-32B for this is HYPE |

### Cited Findings

**Agentic exploit and CTF work**
- Cybench (40 professional CTF tasks): in the original 2024 paper the best models solved 17.5% (Claude 3.5 Sonnet) and 12.5% (GPT-4o) unguided. PROVEN — [Stanford CRFM](https://crfm.stanford.edu/2024/08/19/cybench.html)
- By 2026 a third-party guide to the official leaderboard lists Claude Mythos Preview at 100% (on a 35-of-40-task subset) and Claude Opus 4.7 at 96%; it says the leaderboard has no current open-weight entries and that 2026 open-model Cybench numbers circulating on aggregator sites are vendor self-reports with no stated task subset. PROMISING (secondary source) — [ertas.ai Cybench guide](https://www.ertas.ai/benchmarks/cybench); leaderboard at [cybench.github.io](https://cybench.github.io)
- A secondary blog reports the Stanford AI Index figure that Cybench unguided solve rate went from 15% (2024) to 93% (2026). Unverified against the Index itself — [agentmarketcap.ai](https://agentmarketcap.ai/blog/2026/04/17/stanford-ai-index-terminal-bench-cybersecurity-agent-three-axis-capability-cliff)
- UK AISI measured two leading open-weight models (GLM-5.2 and DeepSeek V4-Pro) and found they lag frontier closed models on narrow cyber tasks by 4 to 7 months, narrower than the 6 to 10 months it measured through most of 2025; on longer-horizon cyber ranges the gap is about 7 months (weaker evidence, fewer scenarios). AISI says this does not predict whether open-weight models will replicate the more recent jumps from Mythos Preview and other closed models. PROVEN — [AISI](https://www.aisi.gov.uk/work/how-far-behind-the-frontier-are-leading-open-weight-models-on-cyber); summary at [The Decoder](https://the-decoder.com/open-weight-models-now-match-frontier-cyber-performance-from-just-four-months-ago-at-a-fraction-of-the-cost/)
- A Cloud Security Alliance note says AISI measured DeepSeek V4-Pro completing cyber tasks at roughly $0.28 each against about $12.50 to $15 for the closed models. Not confirmed on AISI's own page. PROMISING — [CSA research note](https://labs.cloudsecurityalliance.org/research/csa-research-note-open-weight-cyber-capability-gap-20260731/)
- Anthropic's red-team material, as summarised by secondary coverage: re-running an earlier Firefox exercise, Claude Opus 4.6 produced a working exploit twice in several hundred attempts while Mythos Preview produced 181; Opus 4.6 was described as having "almost zero success rate in autonomous exploit development". PROVEN in substance, exact figures secondary — [Dark Reading](https://www.darkreading.com/application-security/anthropic-exploit-writing-mythos-ai-safe%250A); [Axios](https://www.axios.com/2026/04/07/anthropic-mythos-preview-cybersecurity-risks)
- CyberGym (1,507 real-vulnerability reproduction tasks): the original paper found software-engineering-specialised models generalised poorly, at 2.0% success or less. PROVEN — [arXiv 2506.02548](https://arxiv.org/html/2506.02548v2)
- An October 2026 blog claims GLM-5.3 and Kimi K3 are level with the best closed models on CyberGym (95.6% and 93.5% in a "rescored" third-party run). Unverified, and the rows are described elsewhere as not directly comparable. HYPE until a primary source confirms — [ertas.ai blog](https://www.ertas.ai/blog/glm-kimi-cybersecurity-benchmarks-october-2026)
- CVE-Bench: state-of-the-art agents exploited up to 13% of tasks in the original study, and a later patching study concluded frontier models are "still far from reliable autonomous security patching". PROVEN — [summary of the CVE-Bench study](https://news.lavx.hu/article/ai-still-struggles-to-patch-real-vulnerabilities-insights-from-the-cve-bench-study)

**Multi-step investigation (the defender's hard task)**
- ExCyTIn-Bench (LLM agents investigating incidents over Microsoft Sentinel-style logs): average reward across models 0.249; best was o4-mini at 0.368. PROVEN — [arXiv 2507.14201](https://arxiv.org/abs/2507.14201)
- On the same benchmark Phi-4-14B scored 0.085 and GPT-4.1-nano 0.136; a paper summary concludes small models are nearly unusable on this task. Smaller models also submit answers more eagerly. PROVEN (numbers via a summary page) — [ICML 2026 paper notes](https://en.papernotes.org/ICML2026/llm_agent/excytin-bench_evaluating_llm_agents_on_cyber_threat_investigation/)
- A fine-tuned GPT-4o variant in the same paper dropped in performance on held-out incidents. PROVEN — [arXiv 2507.14201](https://arxiv.org/abs/2507.14201)

**Knowledge, classification and mapping (the defender's bulk task)**
- Foundation-sec-8B-Instruct scored 0.692 on CTIBench root-cause mapping against 0.558 for Llama 3.1-8B-Instruct, and 0.644 vs 0.617 on CTIBench multiple choice; it trailed the base Llama on CyberMetric-500, SecBench and SecEval. PROVEN (vendor technical report) — [arXiv 2508.01059](https://arxiv.org/pdf/2508.01059)
- Foundation-sec-8B-Reasoning (January 2026) performs on par with Llama-3.3-70B-Instruct on both CTIBench tasks; a third-party review gives 75.3% vs 68.4% (root-cause mapping) and 69.1% vs 69.2% (multiple choice). PROVEN on parity, exact figures secondary — [arXiv 2601.21051](https://arxiv.org/html/2601.21051v1); [review](https://www.themoonlight.io/review/llama-31-foundationai-securityllm-reasoning-8b-technical-report)
- Meta's CyberSOCEval (malware analysis and threat-intel reasoning): larger, more modern models do better, reasoning modes gave no large boost, and models are "far from saturating" it. PROVEN — [arXiv 2509.20166](https://arxiv.org/html/2509.20166v2)
- Mapping SIEM rules to ATT&CK: GPT-4-Turbo was most accurate among hosted and local models and larger models generally beat smaller ones. PROVEN (2025 paper, older models) — [arXiv 2502.02337](https://arxiv.org/pdf/2502.02337)
- Tool selection: Docker's evaluation (21 models, 3,570 test cases) put Qwen3 14B at tool-selection F1 0.971 against 0.974 for GPT-4, and Qwen3 8B ahead of every other local model, at the cost of reasoning-mode latency. PROVEN for tool selection only; post undated — [Docker blog](https://www.docker.com/blog/local-llm-tool-calling-a-practical-evaluation/)

**Access restrictions and refusals on offensive prompts (2026)**
- OpenAI launched Trusted Access for Cyber in February 2026 and expanded it on 14 April 2026 alongside GPT-5.4-Cyber, a fine-tune with lower refusal thresholds; individuals verify with government ID and know-your-customer checks. PROVEN — [Axios](https://axios.com/2026/04/14/openai-model-cyber-program-release); [CyberScoop](https://cyberscoop.com/openai-expands-trusted-access-for-cyber-to-thousands-for-cybersecurity/)
- OpenAI lists a GPT-5.6 Cyber model at $12.50 input / $75 output per 1M tokens, restricted to "Daybreak Red" customers. PROVEN — [OpenAI model page](https://developers.openai.com/api/docs/models/gpt-5.6-cyber)
- Anthropic restructured its Cyber Verification Program on 6 October 2026 into three tiers (Defense Access, Red Team Access, Specialized Access), folding in Project Glasswing. Every tier includes Claude Opus 5.5, Sonnet 5.5 and Mythos 5.1; tiers differ in which cyber tasks classifiers block. New tiers allow authorised penetration testing and red-teaming. Enrolled organisations must accept data retention so Anthropic can monitor for misuse. PROVEN (news coverage) — [The New Stack](https://thenewstack.io/anthropic-cyber-access-tiers/); [CSO Online](https://www.csoonline.com/article/4231812/anthropic-widens-access-to-ai-cyber-capabilities-for-vetted-security-teams.html)
- One report says the entry tier explicitly opens to universities, individual researchers and open-source maintainers. Single source — [search results for the CVP coverage; see The New Stack](https://thenewstack.io/anthropic-cyber-access-tiers/)
- Anthropic states that outside the programme, classifiers may interrupt work such as malware analysis or exploit validation. PROVEN — [CSO Online](https://www.csoonline.com/article/4231812/anthropic-widens-access-to-ai-cyber-capabilities-for-vetted-security-teams.html)
- In the API, current Claude models return HTTP 200 with `stop_reason: "refusal"` and a `stop_details.category` such as `cyber`; Sonnet 5.5 declines in five categories including `cyber`; some refusals are billed; Claude Fable 5.2 is not available under zero data retention (30-day retention required). PROVEN — [Anthropic pricing/model docs, via bundled API reference cached 2026-11-03](https://platform.claude.com/docs/en/about-claude/models/overview.md)
- Google announced a "Gemini 3.5 Flash Cyber" model alongside Gemini 3.6 Flash. Details not retrieved — [Google blog](https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-3-6-flash-3-5-flash-lite-3-5-flash-cyber/)

### Inferences
- The ratio "small model score / best model score" is about 0.9-1.0 on CTIBench-style single-step tasks and about 0.23-0.37 on ExCyTIn-style multi-step investigation (0.085 and 0.136 against 0.368). That is the quantitative basis for the routing table.
- A weekly self-pentest run will hit cyber classifiers on all three major vendors unless the owner enrols in a verification programme. Enrolment brings mandatory data retention, which collides with the owner's privacy rule. The agent needs a refusal handler and a fallback path (a large open-weight model through an API, or a degraded "scan and report only" mode).
- A 4-to-7-month open-weight lag means a hosted open-weight model in late 2026 is roughly as capable at cyber tasks as a closed frontier model from spring 2026. That is good enough for investigation and rule authoring. It does not cover the Mythos-class exploit jump.
- Nothing found supports running exploit development on a local 8-32B model. Claims of that kind (for example DeepHat 32B "matching models 10x its size on Cybench") were not backed by a leaderboard entry.

### Gaps
- No verified 2026 scores for specific open-weight models (Qwen, DeepSeek, Kimi, GLM, gpt-oss, Llama 4, Gemma) on Cybench, CyberGym, BountyBench, AutoPenBench, the XBOW validation benchmark, NYU CTF Bench, SEC-bench or CyberSecEval 3/4. Searches returned vendor self-reports or nothing; the last search batch was cut off by the budget limit.
- No primary-source OpenAI or Google DeepMind preparedness-evaluation numbers retrieved.
- Whether an individual testing only their own VMs qualifies for Anthropic's entry tier or OpenAI's individual verification, and on what retention terms, was not confirmed on a vendor page.
- CSA mentions a government-directed restriction on a GPT-5.6 model and a June 2026 suspension of Anthropic models; no second source confirmed either.

---

## 2. Security-specialised open models: are they worth using?

### Takeaway
Security-tuned 8B models give a real but narrow gain: clearly better than their own base model on CTI mapping tasks, roughly equal to a general 70B model there, and no better (sometimes worse) on general security question sets and general reasoning. They are a reasonable local choice for ATT&CK/CWE mapping and triage labels; they are not a substitute for a mid or frontier model on investigation.

### Cited Findings
- **Cisco Foundation-sec-8B** is derived from Llama-3.1-8B-Base with continued pre-training on proprietary security data; the Reasoning variant has its own post-training pipeline. PROVEN — [arXiv 2504.21039](https://arxiv.org/html/2504.21039v1); [arXiv 2601.21051](https://arxiv.org/html/2601.21051v1)
- The Instruct variant is within 3 points of Llama 3.1-8B-Instruct on maths, reasoning and coding, and trails on MMLU and BigBenchHard. PROVEN — [arXiv 2508.01059](https://arxiv.org/pdf/2508.01059)
- Licence: a third-party derivative model card lists Apache 2.0 for Foundation-sec-8B. Secondary; the official card was not opened — [Hugging Face derivative card](https://huggingface.co/e12ex2/foundation-sec-8b-heretic)
- **Trend Micro Llama-Primus**: authors state MIT licence; the base variant gained about 15.88% on aggregated security benchmarks over Llama-3.1-8B-Instruct; the "merged" variant keeps instruction-following. PROVEN (authors' own evaluation) — [arXiv 2502.11191](https://arxiv.org/html/2502.11191v2)
- On CTI-Bench CVE-to-CWE mapping a later paper reports Foundation-Sec-8B 72.0%, WhiteRabbitNeo-V2-70B 71.1%, Llama-Primus-Base 67.8%, Llama3-70B 65.9%. PROMISING (attribution to this exact paper not confirmed) — [arXiv 2605.28146 (CAI dataset paper)](https://arxiv.org/pdf/2605.28146)
- **CyberPal 2.0** (4B to 20B models): authors report the 20B model ranks first on CTIBench root-cause mapping ahead of Google's Sec-Gemini v1, and the 20B and 14B models rank second and third on multiple choice behind Sec-Gemini v1 and ahead of OpenAI o1. PROMISING (self-reported) — [arXiv 2510.14113](https://arxiv.org/pdf/2510.14113)
- **SecureBERT 2.0** (Cisco) is an encoder built on ModernBERT, pre-trained on over 13 billion text tokens and 53 million code tokens; README reports security named-entity recognition F1 of 0.945 against 0.734 for the original SecureBERT. PROMISING (README figures) — [GitHub](https://github.com/cisco-ai-defense/securebert2)
- **Lily-Cybersecurity-7B-v0.2** is a Mistral-7B fine-tune on a curated security Q&A mix; **DeepHat V1** is built on Qwen2.5-Coder-7B with a 131K context, with a claim that its 32B version "reportedly matches models 10x its size on Cybench". The Cybench claim is HYPE (no leaderboard entry found) — [arXiv 2605.28146](https://arxiv.org/pdf/2605.28146)

### Inferences
- For log triage and ATT&CK mapping an 8B security model at Q4 (about 5 GB of RAM) is "good enough" in the sense that it matches a 70B general model on the closest public benchmark. Whether it is good enough on the owner's own logs has to be measured on a small labelled sample; public CTI benchmarks are report-style text, not raw syslog.
- A SecureBERT-class encoder is the cheapest option for pure classification and entity tagging: it runs on CPU in milliseconds and needs no generation. It cannot summarise or explain.
- Decensored derivatives of these models exist on Hugging Face. They are untrusted third-party weights and should not be loaded on a security agent's host without a reason.

### Gaps
- Licences for WhiteRabbitNeo, DeepHat, Lily-Cybersecurity and SecureBERT 2.0 not found. Official Foundation-sec licence not confirmed on the vendor card.
- Google Sec-Gemini availability and pricing in late 2026, Microsoft security small models, and any 2026 releases beyond Foundation-sec-8B-Reasoning and CyberPal 2.0 were not retrieved.
- No measured comparison of security-tuned 8B models against current general small models (Qwen3 8B/14B, Gemma 4, gpt-oss-20b) of the same size. All published baselines are Llama 3.x.

---

## 3. Local inference realities: speed, RAM, serving stack, reliability

### Takeaway
A 4-vCPU cloud VM runs an 8B model at Q4 at roughly 3-4 tokens/second and about 5 GB of RAM. That supports a low-volume background triage queue and nothing interactive or agentic. 20B+ models need about 14 GB or more and a GPU or Apple Silicon to be usable. The local serving stack is itself an attack surface and must stay on localhost.

### Cited Findings (all speed figures are community-reported, snippet-level)

| Hardware | Model / quant | Reported speed | RAM | Source |
|---|---|---|---|---|
| 4-core Xeon / 4-vCPU VPS, 8 GB | Llama 3.1 8B Q4_K_M | 3-4 tok/s (table: 3.2) | ~5.2 GB | [DEV post](https://dev.to/manoir_yantai_f22f01340f0/-running-llms-on-cpu-in-2026-real-benchmarks-from-a-4-core-xeon-server-a-4-1438) |
| Shared-vCPU VPS | 8B Q4_K_M | "low single digits" | - | [SSD Nodes guide](https://www.ssdnodes.com/learn/lang/pcm/ollama-vs-llama-cpp) |
| 8 vCPU / 32 GB VPS | 7B-13B | 5-15 tok/s (hosting-vendor claim) | - | [Valebyte](https://valebyte.com/en/blog/tu-propia-llm-en-un-vps-con-cpu-ollama-llama_cpp-con-modelos-7b-13b/) |
| Ryzen 7 5800X, 4 threads | 8B Q4 | 7-11 tok/s | - | [SpecPicks](https://specpicks.com/blog/local-llm-cpu-only-ryzen-7-5800x-2026) |
| AMD EPYC 9334, 24 threads | gpt-oss-20b Q4 | 18.3 tok/s | ~14 GB at Q4 (separate guide) | [Leaseweb on DEV](https://dev.to/leaseweb/cpu-inference-on-amd-epyc-9334-real-numbers-for-llm-and-tts-workloads-54e7) |
| AMD EPYC 9334, 24 threads | DeepSeek-R1 8B Q4_K_M | 27.8 tok/s | - | [Leaseweb on DEV](https://dev.to/leaseweb/cpu-inference-on-amd-epyc-9334-real-numbers-for-llm-and-tts-workloads-54e7) |
| RTX 3060 12 GB | Llama 3.1 8B Q4_K_M / Qwen 2.5 14B Q4_K_M | ~38 / ~18 tok/s (llama.cpp) | fits in 12 GB | attribution not confirmed; candidates: [hardware-corner](https://www.hardware-corner.net/guides/gpu-benchmark-large-language-models/), [mustafa.net](https://mustafa.net/llm-tokens-per-second-benchmarks/) |
| RTX 4090 24 GB | 7B / 27-32B | ~135 tok/s / 55-60 tok/s | fits in 24 GB | same candidates as above |
| Mac mini M4 Pro 48 GB | 8B / 32B | 40-60 / 15-25 tok/s (guide estimate) | unified memory | [DEV guide](https://dev.to/jovan_chan_9500711396d4e6/mac-mini-m4-pro-for-local-ai-in-2026-what-1399-actually-buys-you-121k) |

- Current local-size open models named across 2026 guides: Qwen3 8B/14B, Qwen3.5/3.6 27B (fits one 24 GB GPU), gpt-oss-20b (runs on 16 GB devices) and gpt-oss-120b (one 80 GB GPU), Gemma 4 in tiers of roughly 3 GB / 7 GB / 14 GB / 18 GB at 4-bit, Llama 4. DeepSeek V4 Pro leads open-weight coding scores but is far beyond local hardware. PROMISING (blog rankings, approximate sizes) — [Yotta Labs](https://www.yottalabs.ai/post/best-open-source-llms-2026); [local model ranking](https://localairun.pages.dev/best-local-llm); [Faros](https://www.faros.ai/blog/open-weight-models)
- Sources conflict on Gemma 4's licence: one guide says it moved to Apache 2.0, another ranking flags Gemma and Llama for restrictive licences. Unresolved — [Yotta Labs](https://www.yottalabs.ai/post/best-open-source-llms-2026); [Gumloop](https://www.gumloop.com/blog/open-weight-ai-models)

**Rented GPU by the hour (third-party trackers, September-October 2026)**
- RTX 4090: about $0.34/h on RunPod Community and $0.74/h on RunPod Secure (another article says $0.89/h); about $0.14/h on Vast.ai per one table. RTX A6000: about $0.28/h Vast.ai, $0.53/h RunPod, $1.09/h Lambda. L4: about $0.44-0.49/h RunPod, $0.80/h AWS us-east-1, $0.71/h GCP. Vast.ai prices are host-set marketplace medians and move daily. PROMISING — [gpu-cost tracker](https://gpu-cost.pages.dev/); [Hostinger comparison](https://www.hostinger.com/tutorials/?p=158956)

**Serving-stack security**
- Ollama CVE-2026-7482 ("Bleeding Llama"), an unauthenticated memory leak disclosed 5 May 2026 and fixed in 0.17.1, with about 300,000 internet-facing instances estimated at disclosure; CVSS reported between 9.1 and 9.3. PROVEN — [SecurityWeek](https://www.securityweek.com/critical-bug-could-expose-300000-ollama-deployments-to-information-theft/); [CSA note](https://labs.cloudsecurityalliance.org/research/csa-research-note-ollama-bleeding-llama-cve-2026-7482-ai-inf)
- A February 2026 LeakIX scan counted 12,269 Ollama instances with no authentication and cited the older CVE-2024-37032 path traversal as a route to unauthenticated code execution. PROVEN — [LeakIX](https://blog.leakix.net/2026/02/ollama-exposed/)
- Recommended handling: upgrade, bind to localhost or a closed network, put an authenticating proxy in front, and treat any instance that was internet-reachable before patching as compromised. PROVEN — [CSA note](https://labs.cloudsecurityalliance.org/research/csa-research-note-ollama-bleeding-llama-cve-2026-7482-ai-inf)

**Structured output and tool-calling reliability**
- Three 7-9B models reached up to 85% task accuracy on GSM8K with naive prompting but 0% "output accuracy" (correct and valid JSON); a minimal hand-written format prompt still gave 0% for two of four models. Constrained decoding enforced validity but cost 3.6x to 8.2x latency and in several settings degraded task performance. PROVEN (maths testbed, not security) — [arXiv 2605.02363](https://arxiv.org/abs/2605.02363)
- With sub-2B models, hard schema decoding raised schema validity from 61.5% to 100% but lowered answer accuracy from 19.7% to 11.0%. PROVEN — [arXiv 2605.26128 "The Constraint Tax"](https://www.alphaxiv.org/abs/2605.26128)
- A third paper finds constrained decoding eliminates structural failures in small models but leaves a scale-dependent semantic gap. PROVEN — [arXiv 2609.23742](https://arxiv.org/pdf/2609.23742)

### Inferences
- **What a CPU-only small VM can actually run:** at about 3.5 tok/s, a 150-token triage verdict takes about 43 seconds of generation, before prompt processing. That caps a 4-vCPU box below roughly 2,000 events/day at 100% CPU, and realistically at a few hundred per day if the VM also runs the workload it is protecting. An 8B model plus context takes 5-6 GB, so an 8 GB VM has no headroom; 16 GB is the practical floor for co-hosting. (My arithmetic from the cited speeds; prompt-evaluation speed on CPU was not sourced.)
- A 20B model on a small VM is ruled out by memory (about 14 GB at Q4) before speed is even considered.
- Constrained decoding (GBNF / JSON schema / Outlines) fixes "is it parseable", which is the failure that breaks an agent loop. It does not fix "is it right", and can make it worse on very small models. Use it for the output envelope, keep the schema small (a label, a confidence, a short reason field placed before the label), and measure accuracy with and without it.
- An always-on rented GPU is outside the budget: $0.34/h is about $245/month. Hourly rental only makes sense for bursts (a fine-tuning run, a monthly batch job).
- For a solo operator who already owns an Apple Silicon machine or a 12-24 GB GPU at home, a 14B-27B model becomes practical for triage and some investigation. Buying one for this purpose does not pay back against hosted small-tier prices (see §4).
- llama.cpp bound to 127.0.0.1 is the smallest attack surface of the listed stacks. Ollama is more convenient and has the worse 2026 exposure record. vLLM is a GPU server and irrelevant to a CPU VM; MLX applies only to Apple hardware.

### Gaps
- No clean llama.cpp measurement of Qwen3 8B/14B, Gemma 4 or gpt-oss-20b on a 4-8 vCPU cloud VM was found; the 3-4 tok/s figure is for Llama 3.1 8B from one community post.
- CPU prompt-evaluation speeds, and the effect of llama.cpp prefix caching on a repeated system prompt, were not sourced.
- No measured tool-calling reliability for 2026 small models under constrained decoding (the Berkeley function-calling leaderboard was not retrieved). The claim that Gemma 4 27B reaches about 95% on MCP workflows has no documented method.
- Hetzner GPU server pricing not found. vLLM and MLX security advisories not searched.

---

## 4. Hosted pricing (late 2026) and a worked monthly cost model

### Takeaway
High-volume triage on a hosted small model costs single-digit dollars per month even at thousands of events per day; it is not the cost driver. The budget is decided almost entirely by how often the agent runs frontier-model red-team and patch tasks. A realistic configuration lands at roughly $10-22/month of API spend plus about €6-9 for the VM; weekly frontier runs push it past $100.

### Cited Findings

**Prices per 1M tokens (input / output), standard tier**

| Tier | Anthropic | OpenAI | Google |
|---|---|---|---|
| Small / fast | Claude Haiku 5.5: $0.10 / $0.50 (prompts up to 100K tokens; $0.50 / $2.50 beyond) | GPT-5.6 Luna: $0.20 / $1.20 (cached input $0.02) | Gemini 2.5 Flash-Lite $0.10 / $0.40; Gemini 3.1 Flash-Lite $0.25 / $1.50; Gemini 3.5 Flash-Lite $0.30 / $2.50 |
| Mid | Claude Sonnet 5.5: $2 / $10 (cache read $0.10) | GPT-5.6 Terra: $2 / $12 (cached $0.20) | Gemini 3.6 Flash $1.50 / $7.50; Gemini 3.1 Pro (preview) $2 / $12 up to 200K, $4 / $18 above |
| Frontier | Claude Opus 5.5: $4 / $20 (cache read $0.20); Claude Fable 5.2: $8 / $40 (cache read $0.20) | GPT-5.6 Sol: $4 / $20 promotional (launch price $5 / $30) | no verified price above Gemini 3.1 Pro found |
| Gated cyber | Claude Mythos 5.2: $8 / $40, verified organisations only | GPT-5.6 Cyber: $12.50 / $75, Daybreak Red customers only | Gemini 3.5 Flash Cyber: price not retrieved |

- Anthropic figures — [Anthropic pricing page](https://platform.claude.com/docs/en/about-claude/pricing.md), values taken from the bundled Claude API reference cached 2026-11-03; live page not fetched. PROVEN
- OpenAI figures — [OpenAI pricing page](https://developers.openai.com/api/docs/pricing?latest-pricing=batch); [Sol](https://developers.openai.com/api/docs/models/gpt-5.6-sol), [Terra](https://developers.openai.com/api/docs/models/gpt-5.6-terra), [Luna](https://developers.openai.com/api/docs/models/gpt-5.6-luna) model pages. PROVEN (via search summary of official pages)
- Sol's promotional price ends on a disputed date: the model page says 30 November 2026, the enterprise rate card says "at least through" 21 November 2026 — [Sol model page](https://developers.openai.com/api/docs/models/gpt-5.6-sol); [rate card](https://help.openai.com/en/articles/20001415-chatgpt-rate-card-enterprise-token-based-pricing)
- Google figures — [Gemini API pricing page](https://ai.google.dev/gemini-api/docs/pricing); [Gemini 3.6 Flash launch post](https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-3-6-flash-3-5-flash-lite-3-5-flash-cyber/). PROVEN for the rows shown; **conflict:** third-party blogs variously list Gemini 3.6 Flash at $0.75 / $3.75 and mention a "Gemini 3.8 Flash" and "Gemini 4 Argon", none of which I could confirm on a Google page — [morphllm](https://www.morphllm.com/gemini-api-pricing)

**Discounts and modifiers**
- Batch: 50% off on Anthropic (asynchronous Message Batches) and on OpenAI (batch rates listed at half standard); Gemini Flash-Lite batch is half the standard rate. PROVEN — [Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing.md); [OpenAI pricing](https://developers.openai.com/api/docs/pricing?latest-pricing=batch); [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing)
- Prompt caching: Anthropic cache writes cost about 1.25x input and reads are the per-model rates in the table; minimum cacheable prefix is model-dependent (512-4,096 tokens), so short triage prompts may not cache at all. PROVEN — [Anthropic prompt caching docs](https://platform.claude.com/docs/en/build-with-claude/prompt-caching.md)
- OpenAI, GPT-5.6 onward: cache writes billed at 1.25x uncached input, cache reads keep the 90% discount; prompts above 272K input tokens are billed at 2x input and 1.5x output for the whole request. Forum users report implicit caching can raise effective input cost above the headline price. PROVEN / anecdotal for the last point — [OpenAI pricing](https://developers.openai.com/api/docs/pricing?latest-pricing=batch); [developer forum thread](https://community.openai.com/t/question-about-gpt-5-6-api-cache-read-write-token-billing/1386256)
- Anthropic US-only inference (`inference_geo: "us"`) costs 1.1x; default is global. PROVEN — [Anthropic docs via bundled reference](https://platform.claude.com/docs/en/about-claude/pricing.md)

**Data terms**
- OpenAI: API data is excluded from training by default; zero data retention requires prior approval. PROMISING (secondary) — [ZDR comparison](https://guptadeepak.com/zero-data-retention-ai-providers/)
- Anthropic: Claude Fable 5.2 requires 30-day retention and is not available under zero data retention unless expressly authorised. PROVEN — [Anthropic docs via bundled reference](https://platform.claude.com/docs/en/about-claude/models/overview.md). Secondary sources disagree on whether a 30-day window now applies to all "Covered Models" even with a ZDR agreement — [ZDR comparison](https://guptadeepak.com/zero-data-retention-ai-providers/); [developersdigest](https://www.developersdigest.tech/models/data-retention)
- Google: terms depend on the surface; the free AI Studio tier has different terms from paid and Vertex usage. PROMISING (secondary) — [ZDR comparison](https://guptadeepak.com/zero-data-retention-ai-providers/)
- Claude on Bedrock and Vertex is partner-operated with separate pricing; Claude on Google Cloud use is governed by Anthropic's commercial terms. PROVEN — [Anthropic docs via bundled reference](https://platform.claude.com/docs/en/about-claude/pricing.md); [ZDR comparison](https://guptadeepak.com/zero-data-retention-ai-providers/)

**Published per-task cost anchors**
- DARPA AIxCC final (August 2025): average cost of $152 per task to find and patch a vulnerability; teams found 54 unique vulnerabilities and patched 43 (the official site lists 43 found and 31 patched for the scored round). PROVEN — [Team Atlanta news page reproducing DARPA](https://team-atlanta.github.io/news/); [aicyberchallenge.com](https://aicyberchallenge.com/)
- Team Atlanta's winning system reported 61% vulnerability coverage and 72.1% patch success. PROVEN — [arXiv 2509.14589](https://arxiv.org/abs/2509.14589v1)
- Shannon (Keygraph open-source pentest agent): about $50 per test, mostly Claude Sonnet cost. PROMISING (news-summary estimate) — [gentic.news](https://www.gentic.news/article/keygraph-s-shannon-ai-pentester)
- XBOW sells per test, not per finding: $4,000 (Plus) and $8,000 (Premium) per test on its pricing page; other sources say tiers changed in mid-2026 and start at $6,000. PROVEN for the per-test model; prices conflict — [XBOW pricing](https://xbow.com/pricing)
- AISI-derived figure: about $0.28 per cyber task on DeepSeek V4-Pro against $12.50-15 on closed models. PROMISING (CSA note) — [CSA](https://labs.cloudsecurityalliance.org/research/csa-research-note-open-weight-cyber-capability-gap-20260731/)

**VM for the agent itself**
- Hetzner raised cloud prices twice in 2026 (1 April, up to 37%; 15 June, CX and CAX about 1.3-1.4x, dedicated-vCPU CPX and CCX up to 176%). Examples after June, Germany/Finland, excluding IPv4: CX33 €8.49/month (was €6.49), CAX11 €5.99 (was €4.49), CPX22 €19.49 (was €7.99). PROMISING (third-party reports) — [Tom's Hardware](https://www.tomshardware.com/tech-industry/hetzner-to-raise-prices-by-up-to-37-percent-from-april-1); [WZ-IT](https://wz-it.com/en/blog/hetzner-price-increase-june-2026-cpx-ccx-alternatives/)
- October 2026 reports say Hetzner's cost-optimised CX and CAX plans showed "currently not available" while CPX and CCX could be ordered. Unconfirmed — [Vincent Schmalbach](https://www.vincentschmalbach.com/hetzner-cheap-cloud-unavailable-price-increases/)

### Worked cost model (my arithmetic on the prices above)

Assumptions. A triage call is 1,500 input tokens (1,000 static instructions + 500 for the event) and 150 output tokens. An investigation is an agent loop totalling 300K input and 15K output tokens. A red-team run is 3M input and 100K output. A patch task is 5M input and 200K output. "Cached" means 80% of input billed as cache reads and 20% as cache writes.

Unit costs:

| Unit | Model | Uncached | Cached |
|---|---|---|---|
| 1,000 triage calls | Haiku 5.5 | $0.225 | (prefix too short to rely on) |
| 1,000 triage calls | GPT-5.6 Luna | $0.48 | - |
| 1,000 triage calls | Gemini 2.5 Flash-Lite | $0.21 | - |
| 1 investigation | Sonnet 5.5 | $0.75 | $0.32 |
| 1 red-team run | Opus 5.5 | $14.00 | $5.48 |
| 1 patch task | Opus 5.5 | $24.00 | $9.80 |
| 1 red-team run (10M in / 300K out) | Fable 5.2 | $92.00 | $33.60 |

Scenarios:

| | Low | Medium | High |
|---|---|---|---|
| Triage events/day after pre-filter | 200 | 2,000 | 10,000 |
| Triage, Haiku 5.5 | $1.35 | $13.50 ($6.75 batched) | $67.50 ($33.75 batched) |
| Investigations/month, Sonnet 5.5 | 9: $3-7 | 22: $7-17 | 30 deep (1M in / 40K out): $29-72 |
| Frontier work/month | 1 Opus 5.5 run: $5.50-14 | 4.3 Opus 5.5 runs + 2 patch tasks: $43-108 | 4.3 Fable 5.2 runs ($144-396) + 4 patch tasks at the $152 AIxCC anchor ($608) |
| **API total/month** | **about $10-22** | **about $65-140** | **about $850-1,150** |
| Budget verdict | comfortable | uncomfortable to painful | out of range |

- Medium with the weekly run moved to Sonnet 5.5 ($2.74-7 per run) comes to roughly $50-110.
- Add the VM: about €6-9/month for a 2-4 vCPU shared instance at post-June-2026 Hetzner prices, if available.

### Inferences
- Triage volume barely matters at hosted small-tier prices: going from 200 to 2,000 events/day adds about $12/month. Running a local model to save that money is not worth an extra VM size. The reason to run triage locally is privacy, not cost.
- Frontier cadence is the control knob. One frontier run a month fits a tens-of-dollars budget; weekly does not unless caching works well or the run uses a mid-tier model.
- The $152 AIxCC anchor and my $10-24 patch-task estimate differ by an order of magnitude because AIxCC tasks included fuzzing-scale discovery over large codebases. A solo operator patching a known finding on their own service is closer to the low end; treat $152 as the ceiling for a hard find-and-fix.
- Bedrock, Vertex and Azure change who the processor is and can give regional pinning, but they do not change the fact that plaintext prompts leave the owner's machine. They do not satisfy the "no real IPs or hostnames unless opted in" rule on their own.
- Refusals are a cost line: a blocked red-team run can still be billed, and a fallback model re-runs the request at its own rates.

### Gaps
- DigitalOcean and AWS Lightsail/EC2 small-instance prices were not retrieved (search budget exhausted). One article claims Hetzner's cost-optimised plans remain 3-4x cheaper; no price list behind it.
- GPT-6 API pricing not verified: OpenAI's enterprise rate card names GPT-6 Sol, Astra and Luna, and an aggregator lists "GPT-6 Astra" at $10 / $50, but no official per-token API price was found.
- Google's current top-tier model name and price beyond Gemini 3.1 Pro preview not confirmed.
- Primary-source retention and training terms for OpenAI, Google and AWS Bedrock were not opened; the Bedrock "prompts are not shared with model providers" statement was not found in results.
- No published cost-per-finding figures for XBOW, CAI (Alias Robotics) or Google's Big Sleep were found. A "cost per flag" research note exists but was not opened: [pwnkit docs](https://pwnkit-docs.pages.dev/research/2026-05-08-cost-per-flag/).
- Token counts in the cost model are my assumptions, not measurements. The first week of real usage should replace them.

---

## 5. Privacy: redaction and pseudonymisation gateways and how they fail

### Takeaway
Detector-based redaction of free text is not reliable enough to be the only control: measured recall is around two-thirds for off-the-shelf PII detection and around one-half for secrets, and even perfect identifier removal leaves most inferable information in place. For a security agent the stronger design is an allowlist: send typed, pre-tokenised fields with stable placeholders, never raw text, and keep the mapping table local.

### Cited Findings

**Detection quality**
- Microsoft Presidio's own evaluation docs say recall matters more than precision for PII and recommend an F-beta score with beta = 2; they also say the evaluation notebook uses "vanilla" Presidio and the results "aren't very accurate"; a comprehensive benchmark table is listed as "coming soon". PROVEN — [Presidio evaluation docs](https://microsoft.github.io/presidio/evaluation); [recipes gallery](https://microsoft.github.io/presidio/recipes)
- A third-party benchmark measured Presidio at 98.2% precision and 66.6% recall (F1 79.3%) on Microsoft's synthetic evaluator set (326 entities); this is general PII, not technical text. PROMISING (competitor's benchmark) — [Septum benchmark](https://byerlikaya.github.io/Septum/benchmark)
- A PII pipeline for source code reported above 90% precision and recall for emails, above 80% for IP addresses, and for keys almost 80% precision but only slightly above 50% recall. PROVEN — [SantaCoder, arXiv 2301.03988](https://arxiv.org/pdf/2301.03988)
- A comparative study of secret-detection tools reports GitHub Secret Scanner recall of 6% on its benchmark, showing how many secrets a high-precision tool misses. PROVEN (figure via search summary) — [arXiv 2307.00714](https://arxiv.org/pdf/2307.00714)
- Log entries frequently carry user identifiers, IP addresses, host names and system configuration; a 2025 paper evaluates per-category detection of IPs, MAC addresses and file paths in logs. PROVEN — [SDLog, arXiv 2505.14976](https://ar5iv.labs.arxiv.org/html/2505.14976)
- A study of 25 public log datasets and 45 practitioners found no standard guideline for what to anonymise in software logs. PROVEN — [FSE 2025](https://conf.researchr.org/details/fse-2025/fse-2025-research-papers/122/Protecting-Privacy-in-Software-Logs-What-Should-be-Anonymized-)

**Utility loss**
- An industry report on LLM root-cause analysis over private logs found that replacing entities with structured prefixes (for example `FunctionName…`) rather than opaque tokens improved model accuracy. PROMISING (figures only in slides) — [InsightAI, CAIN 2025](https://conf.researchr.org/details/cain-2025/cain-2025-call-for-papers/18/InsightAI-Root-Cause-Analysis-in-Large-Hierarchical-Log-Files-with-Private-Data-Usin); [slides](https://www.dorsal.polymtl.ca/files/december2024/mEkhlasi_december2024_insight_aI.pdf)
- An older study found anonymised system logs generally lacked adequate usefulness for behavioural analysis, while content-aware methods preserved correlations. PROVEN (2022, RNN models) — [arXiv 2212.01101](https://arxiv.org/abs/2212.01101)

**Residual leakage**
- PAPILLON (local model rewrites the request before a hosted model sees it): best pipeline kept response quality 85.5% of the time and still leaked private information 7.5% of the time. PROVEN — [arXiv 2410.17127](https://arxiv.org/abs/2410.17127v3)
- A 2026 follow-up reports that even perfect PII removal eliminates only 18% of implicit leakage relative to direct delegation; most inferable attributes remain. PROVEN (figure via search summary) — [Findings of EMNLP 2026](https://aclanthology.org/2026.findings-emnlp.998.pdf)

**Gateway tooling**
- LLM Guard (Protect AI) implements the reversible pattern: an `Anonymize` input scanner writes real values to a `Vault`, the sanitised prompt goes to the model, and a `Deanonymize` output scanner restores them. Presidio provides the detection and replacement engine and takes custom recognisers. PROVEN — [Langfuse security docs](https://langfuse.com/docs/security-and-guardrails)
- LiteLLM was compromised on PyPI twice in 2026. On 24 March 2026 malicious versions 1.82.7 and 1.82.8 were published using a token stolen in the earlier Trivy compromise (attributed to "TeamPCP"); the payload was a credential stealer that ran on every Python start, not only on import; sources give 40 minutes to 2 hours of exposure. PROVEN — [NetSPI](https://www.netspi.com/blog/executive-blog/ai-ml-pentesting/litellm-supply-chain-compromise/); [Upwind](https://www.upwind.io/feed/litellm-pypi-supply-chain-attack-malicious-release)
- Datadog (21 October 2026) reports a second compromise: malicious LiteLLM v1.107.0 on PyPI and container registries after multiple maintainer accounts were taken over. PROMISING (single source in results) — [Datadog Security Labs](https://securitylabs.datadoghq.com/articles/litellm-compromised-pypi-docker.md)

**Confidential-computing inference**
- Phala serves open models inside Intel TDX plus NVIDIA GPU enclaves with a verification guide; listed price for Qwen3.5-27B is $0.30 / $2.40 per 1M tokens. NEAR AI's confidential cloud lists DeepSeek V4 Flash at $0.17 / $0.35 with an OpenAI-compatible API. Tinfoil's only found price ($2 per 1M tokens) is from a 2025 directory and likely stale. PROMISING — [Phala docs](https://docs.phala.com/phala-cloud/confidential-ai/confidential-model/confidential-ai-api); [NEAR AI cloud](https://cloud.near.ai/); [Tinfoil directory entry](https://www.toolmage.com/en/tool/tinfoil/)

### Inferences
- **Why technical identifiers are easier and still fail.** IPs, MAC addresses, JWTs and vendor-prefixed API keys have regular shapes, so regex and entropy checks catch most of them. The misses are the cases that matter: hostnames and internal URLs that look like ordinary words, paths that embed usernames, secrets without a known prefix, base64- or hex-encoded payloads, values split across lines, and identifiers inside command lines or stack traces.
- **Failure modes to design for:** (1) detector misses, per the recall numbers above; (2) partial matches that leave half an identifier; (3) encoded data passing through untouched; (4) context leakage, where the redacted text still states what the service is, what software version it runs and what went wrong; (5) re-identification from structure, such as network topology, open-port sets or timing patterns that are unique to the owner; (6) inconsistent placeholders across requests breaking the model's reasoning; (7) the mapping vault itself becoming a high-value secret; (8) the hosted model echoing a placeholder in a form the de-anonymiser does not recognise.
- **Consistent typed pseudonyms preserve most utility.** Map each real value to a stable, typed placeholder (`host-A`, `10.0.0.x → net1-ip-3`, `user-2`, `/path-7/…`) so the model can still correlate across events. The InsightAI result supports typed over opaque tokens. Keep private-range and public addresses distinguishable, since that distinction carries security meaning.
- **Allowlist beats blocklist.** Because the agent controls its own telemetry, it can build hosted prompts from parsed fields (template id, event type, counts, placeholder ids, severity) and never forward raw log lines. Anything not on the allowlist stays local. This turns a recall problem into a schema problem. It costs fidelity on unparsed or novel events, which is exactly where a local model should take over.
- **The gateway is itself supply-chain risk.** Two LiteLLM compromises in one year, with a payload that stole credentials from every Python process, is a direct argument against placing a large third-party proxy on the same host as the agent's API keys and SSH access. A few hundred lines of owned redaction code with pinned, hash-verified dependencies is the safer choice for one person.
- **TEE inference is usable by a solo developer** (OpenAI-compatible endpoints, per-token prices close to ordinary open-model hosting) but only for open-weight models, so it covers the mid tier, not the frontier tier. Trust moves from the provider's policy to the hardware vendor and the attestation check, which the owner has to actually verify.
- An explicit owner opt-in path is still needed: some investigations cannot be done on pseudonymised data, and the agent should ask rather than silently degrade or silently leak.

### Gaps
- No published precision/recall for Presidio or LLM Guard specifically on logs, configs and shell output (IPs, hostnames, paths, API keys, JWTs, internal URLs) was found. This must be measured on the owner's own data.
- No 2024-2026 study was found that measures task-accuracy loss from pseudonymising logs or code before sending them to an LLM, beyond the InsightAI slides. Two candidate papers named by a survey (Aghili et al. 2025; Loiseau et al. 2025) were not retrieved: [survey, arXiv 2601.17717](https://arxiv.org/pdf/2601.17717).
- Not retrieved: Private AI, Nightfall, Lakera, Skyflow, Tonic Textual, Cloudflare AI Gateway DLP (features, pricing, accuracy), LiteLLM's guardrail hook behaviour on a detector miss, Azure confidential inference, NVIDIA confidential GPU offerings, Apple Private Cloud Compute comparisons.
- Scope of the October 2026 LiteLLM incident rests on one source.

---

## 6. Hybrid routing: local model on raw data, hosted model on abstracted tasks

### Takeaway
There is measured support for the pattern, with a clear caveat. Splitting work between a small local model that sees the raw data and a hosted model that sees only instructions and summaries keeps about 98% of hosted-only quality at about one-sixth of the hosted cost when the hosted model decomposes the task. The privacy benefit is real but partial, and the published results are on document question answering, not security telemetry.

### Cited Findings
- Minions (Stanford, ICML 2025): a simple chat protocol between an on-device model holding the data and a cloud frontier model cut remote cost 30.4x but recovered only 87% of frontier performance. PROVEN — [arXiv 2502.15964](https://arxiv.org/html/2502.15964v1)
- MinionS, where the cloud model decomposes the task into subtasks that local models run in parallel over short chunks, cut cost 5.7x on average while recovering 97.9% of remote-only performance. PROVEN — [arXiv 2502.15964](https://arxiv.org/html/2502.15964v1)
- The authors identify why the simple protocol falls short: the local model struggles to follow multi-step instructions and to reason over long contexts. PROVEN — [arXiv 2502.15964](https://arxiv.org/html/2502.15964v1)
- PAPILLON's best configuration (Llama-3.1-8B local, GPT-4o-mini remote, DSPy-optimised prompts): 85.5% quality preserved, 7.5% leakage; authors state the gap to proprietary models is not closed. PROVEN — [arXiv 2410.17127](https://arxiv.org/abs/2410.17127v3)
- Perfect PII removal eliminates only 18% of implicit leakage. PROVEN (via search summary) — [Findings of EMNLP 2026](https://aclanthology.org/2026.findings-emnlp.998.pdf)

### Inferences
- The MinionS finding matches the benchmark picture in §1: small models are adequate for short, single-step extraction over small chunks and poor at multi-step planning. So the hosted model should plan and the local model should read. That is the right shape for this agent: the hosted model writes the investigation plan and the queries against placeholder names; local code and a local model execute them on real data and return typed, pseudonymised results.
- The cost saving matters less here than the privacy property, since hosted triage is already cheap (§4).
- A 7.5% explicit-leak rate from an LLM-based rewriter is too high to be the only barrier. The deterministic allowlist from §5 should be the boundary, with a local model as a helper inside it, not as the redactor of last resort.
- On a CPU-only VM the local half of this pattern is slow (§3). It works as a queue, not as a live conversation between two models. Each local sub-step costs tens of seconds.

### Gaps
- No evaluation of Minions-style or PAPILLON-style delegation on log analysis, incident investigation or code patching was found.
- No measurement of how much investigation quality a frontier model loses when it sees only placeholders and typed summaries instead of raw evidence.

---

## 7. Fine-tuning: is it worth it for a solo builder?

### Takeaway
No, not as a starting point. The compute is cheap (a few dollars per run), but the published evidence shows fine-tuned small models gaining little outside the domain they were trained on, the labelled data does not exist for one person's handful of VMs, and public security datasets are an unvetted supply chain. Prompting plus retrieval with a small or mid model, and an already-tuned open security model for local mapping, covers the need.

### Cited Findings
- For mapping threat-report text to ATT&CK tactics, a generative model with retrieval beat fine-tuned encoder models, particularly when retrieval surfaced directly relevant context. PROVEN (2024, GPT-3.5 era) — [arXiv 2401.00280](https://arxiv.org/html/2401.00280v3)
- For mapping SIEM rules to ATT&CK, the largest hosted model was most accurate and larger beat smaller. PROVEN — [arXiv 2502.02337](https://arxiv.org/pdf/2502.02337)
- A master's thesis on SIEM telemetry found a fine-tuned Mistral-7B learned narrative-to-ATT&CK mapping in its home domain but cross-domain scored micro-F1 0.2707 against 0.2806 for GPT-4o, both low. PROMISING (thesis, not peer reviewed) — [Politecnico di Torino thesis](https://webthesis.biblio.polito.it/37688/1/tesi.pdf)
- A fine-tuned GPT-4o dropped in performance on held-out incidents in ExCyTIn-Bench. PROVEN — [arXiv 2507.14201](https://arxiv.org/abs/2507.14201)
- ExCyTIn-Bench generates tasks with verifiable rewards from investigation graphs, which the authors say extends naturally to reinforcement-learning training of agents. PROVEN (as a capability of the benchmark; not a result) — [arXiv 2507.14201](https://arxiv.org/abs/2507.14201)
- Continued pre-training and fine-tuning at vendor scale does help on in-domain CTI tasks: Foundation-sec-8B-Instruct 0.692 vs 0.558 for its base on CTIBench root-cause mapping; Llama-Primus about +15.88% aggregated. PROVEN — [arXiv 2508.01059](https://arxiv.org/pdf/2508.01059); [arXiv 2502.11191](https://arxiv.org/html/2502.11191v2)
- Cost: QLoRA on an 8B model with about 50,000 examples for 3 epochs takes roughly 6 hours and about $5 (one RTX 4090) to $12 (one A100 80 GB) of rented compute; another vendor estimate for a 7B model is far higher at 40-80 A100-hours, $100-256 per iteration. PROMISING (vendor and community blogs; wide spread) — [Techloy](https://www.techloy.com/fine-tuning-an-open-model-on-a-rented-gpu-what-an-hour-costs-in-2026/); [Spheron](https://www.spheron.network/blog/llm-fine-tuning-cost-2026-api-vs-renting-gpus/)
- Poisoning: backdoors are typically an innocuous-looking trigger inserted into a very small fraction of fine-tuning samples; a compromised popular dataset poisons every model tuned on it. PROVEN as a threat — [arXiv 2406.07778](https://www.arxiv.org/abs/2406.07778v2); [Promptfoo guide](https://www.promptfoo.dev/blog/data-poisoning/)
- A first-person blog describes uploading a dataset with 50 backdoored rows among 1,000 to Hugging Face, which stayed up about six months with about 2,400 downloads. Unverified anecdote — [blog post](https://theguptalog.blogspot.com/2026/05/i-poisoned-hugging-face-dataset-and-it_0613660887.html)
- Datasets: Trend Micro's Primus is an open collection for security LLM training (pre-training, instruction and reasoning sets) released with the models. PROVEN — [arXiv 2502.11191](https://arxiv.org/html/2502.11191v2)

### Inferences
- **Recommendation: do not fine-tune at the start.** Order of work: (1) deterministic pre-filtering and templating; (2) prompt plus a few labelled examples plus retrieval over the owner's own past verdicts; (3) an off-the-shelf security-tuned 8B model if a local model is wanted; (4) only then consider tuning.
- **Why the cheap GPU bill is misleading.** The run costs $5-12. The real costs are building a few thousand correctly labelled examples from one person's environment, building an evaluation set that is kept separate, re-tuning when the base model or the log formats change, and serving a custom model on hardware that manages 3-4 tok/s.
- **Generalisation is the measured weakness.** Both the thesis and ExCyTIn show tuned models falling back on unseen domains or incidents. A solo operator's environment changes every time they deploy something new.
- **Conditions under which the answer flips:**
  - The owner must run fully offline or refuses any hosted call, so a local model has to carry triage alone.
  - There are a few thousand owner-labelled verdicts on a stable, narrow task (for example "benign or not" on a fixed set of templates) and the prompted local model is measurably below target on a held-out set.
  - The target is a small encoder classifier (SecureBERT-class) rather than a generative model. That is cheap to train, cheap to serve on CPU and easy to evaluate.
  - Volume grows to where hosted triage cost matters. At current prices that is well above 10,000 events/day.
- If tuning is done, use only datasets with clear provenance, pin them by hash, and scan for trigger-like rare tokens. Public "cybersecurity instruction" sets from unknown uploaders should be treated as untrusted input.

### Gaps
- No 2025-2026 head-to-head of a LoRA-tuned small model against prompt-plus-retrieval on a current small or mid hosted model for log anomaly classification, alert triage or Sigma rule generation was found. The log-anomaly search (LogLLM and similar) was cut off by the search budget.
- The following datasets were named in the brief and are known to me from background knowledge, but were **not verified this session** (no search results retrieved, URLs from memory): Splunk attack_data (github.com/splunk/attack_data), OTRF Security-Datasets / Mordor (github.com/OTRF/Security-Datasets), the SigmaHQ rule corpus (github.com/SigmaHQ/sigma), LANL authentication datasets, BETH, ATLASv2, DARPA OpTC and Transparent Computing. Licences, sizes and current availability are unconfirmed.
- No evidence found of a real-world poisoned *security* dataset being used in an attack; the risk is demonstrated in research and anecdote only.

---

## 8. Non-LLM methods that are good enough before any LLM call

### Takeaway
Log templating and counting should sit in front of every model call. It is the standard engineering answer and it is what makes hosted triage cost independent of log volume. No published study quantifies the token saving, so the reduction factor has to be measured on the owner's logs.

### Cited Findings
- Practitioner guidance: Drain3-style template mining turns millions of lines into a few hundred templates, and the model should be sent template representatives and counts, not raw streams; "if your token bill scales linearly with log volume, the architecture is wrong". PROMISING (practitioner post, no measured percentage) — [DEV post](https://dev.to/cgivre/using-llms-for-log-analysis-parsing-clustering-and-queries-3350)
- Research on LLM-based log parsing reduces model invocations by matching new lines against cached templates and only calling the model on misses. PROVEN as a technique — [VarParser, arXiv 2601.22676](https://arxiv.org/html/2601.22676v1)
- LLM-driven template generation costs about $1 to $5 in API calls per benchmark dataset. PROVEN — [LLMLog, arXiv 2508.09594](https://arxiv.org/pdf/2508.09594)
- A security-domain encoder reaches F1 0.945 on security named-entity recognition, a non-generative route to entity tagging. PROMISING (README figure) — [SecureBERT 2.0](https://github.com/cisco-ai-defense/securebert2)

### Inferences
- Suggested front end, cheapest first: (1) parse to structured events; (2) Drain3 templating, with per-template counts and first-seen times; (3) baseline diff, so only new templates, rate changes and rare parameter values go forward; (4) allowlist rules for known-benign patterns; (5) optional embedding clustering to merge near-duplicate alerts; (6) only the remainder reaches a model. All of this runs in megabytes of RAM on the same small VM.
- Templating doubles as a privacy control: a template plus typed parameter slots is already most of the way to the allowlisted, pseudonymised payload described in §5.
- The "200 / 2,000 / 10,000 events per day after pre-filtering" figures in §4 depend entirely on this stage. A noisy internet-facing host can emit far more raw lines than that; the pre-filter, not the model choice, sets the bill.
- Classic anomaly detection over template counts gives a recall-oriented first pass and produces explainable features. It also produces false positives on every deployment or config change, which is where a small model's triage step earns its place.

### Gaps
- No study measuring token or cost reduction from Drain3-before-LLM triage, and no comparison of triage accuracy on raw lines against template-plus-count summaries.
- No retrieved evidence on embedding-plus-clustering quality for alert deduplication on small-host telemetry.
- Classic anomaly-detection baselines (isolation forest, count-vector methods on HDFS/BGL-style benchmarks) were not searched this session.
