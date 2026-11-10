# State of the Art in AI/LLM Security Agents (as of 2026-11-10): What Was Actually Measured

*Method note for the report writer (read first).* In this session, direct page fetches were blocked (arxiv.org, alphaxiv.org, dev.to all failed DNS; the GitHub API was not enabled), and the shared web-search budget ran out before the last batch of queries. Every finding below therefore comes from **search-result summaries and snippets**, not from reading the primary PDF or repo. Where a number was seen only in a secondary write-up, it is marked "(secondary)". Where nothing was retrieved, it is in Gaps. Star counts, licences and "last commit" dates come from third-party listings, not from the repos themselves. Labels: **PROVEN** = independently measured or widely deployed; **PROMISING** = credible early results, usually author-reported; **HYPE** = marketing or unreproduced.

---

## 1. Verification of the specific papers and claims

### Takeaway
All six named items trace to real sources, but three need correcting: the "30–40% of attack actions trigger alerts" figure is a **design parameter of the SecRespond benchmark**, not an empirical finding about real environments; the AgenticRepair "25 compiled but still exploitable" count was seen only in a secondary summary; and the SecRespond "skipped credential rotation and post-cleanup checks" detail could not be confirmed. AIxCC's 86% / 68% / ~$152 figures are confirmed against DARPA sources, with a denominator revision (70 → 63) that explains conflicting press numbers.

### Cited Findings

**SecRespond (arXiv 2607.26791) — EXISTS; core claim VERIFIED, two details NOT verified**
- Title: "SecRespond: Benchmarking AI Agents for Real-World Post-Compromise Incident Response"; first author Lehan Wang; posted 2026-07-29 (one listing shows 2026-07-30). — [arXiv abs](https://arxiv.org/abs/2607.26791), [arXiv PDF](https://arxiv.org/pdf/2607.26791)
- Affiliation is reported two ways: "Alibaba and HKUST" in one summary, "Tongyi Lab, Alibaba Group and Alibaba Cloud Computing" in another. Code/data are public under Alibaba-NLP. — [Hugging Face dataset](https://huggingface.co/datasets/Alibaba-NLP/SecRespond), [Hugging Face paper page](https://huggingface.co/papers/2607.26791)
- Scope: 10 cyber ranges on fully instantiated cloud-host environments, 4 entry-point types, 21 ATT&CK techniques, 5 operating systems. — [arXiv abs](https://arxiv.org/abs/2607.26791)
- Setup: each agent gets a **frozen forensic disk snapshot plus synthetic host-security-product alert outputs**; 23 frontier LLMs were run on the OpenCode agent harness. — [aiweekly.co alert](https://aiweekly.co/alerts/alibaba-secrespond-no-llm-fully-solves-any-incident-range), [toknow.ai](https://toknow.ai/posts/secrespond-post-compromise-incident-response-benchmark/)
- VERIFIED headline: "No model achieving complete detection and remediation on any single range." — [arXiv abs](https://arxiv.org/abs/2607.26791); repeated in [notatechguy.com](https://www.notatechguy.com/23-ai-agents-tested-on-breach-response-zero-passed/)
- Scores retrieved: average planning score peaks at 55.3% on "baseline risk" and reaches only 31.8% on "investigation & response quality". — [arXiv PDF](https://arxiv.org/pdf/2607.26791)
- VERIFIED persistence weakness: models did best on the Intrusion Entity (ENT) category "largely because malicious processes often trigger visible alerts"; performance "dropped significantly in the Persistence Mechanism (PER) category" because detecting persistence "requires proactive scanning of system-wide configuration files and crontabs". — [alphaXiv listing of 2607.26791](https://www.alphaxiv.org/abs/2607.26791)
- Qualitative finding: agents "reliably surfaced alert-exposed problems but failed to proactively investigate disks for silent intrusions or produce comprehensive, verified remediation plans." — [aiweekly.co alert](https://aiweekly.co/alerts/alibaba-secrespond-no-llm-fully-solves-any-incident-range)
- Stated limitation (commentary): it is a cloud-host benchmark; identity-plane and network-only incidents are out of scope. Commentary also notes the public abstract does not say which model was best/worst or how partial remediation is scored. — [aiweekly.co alert](https://aiweekly.co/alerts/alibaba-secrespond-no-llm-fully-solves-any-incident-range)

**"Only about 30–40% of attack actions trigger alerts" — SOURCE FOUND; CLAIM NEEDS REWORDING**
- The source is SecRespond itself, and it is a benchmark construction choice: "The designers ensured that only 30% to 40% of the attack actions trigger security alerts." It is not a measurement of real-world EDR coverage. — [alphaXiv listing of 2607.26791](https://www.alphaxiv.org/abs/2607.26791)
- The "agents miss persistence most" half of the claim is the PER-category result above, from the same paper. — [alphaXiv listing of 2607.26791](https://www.alphaxiv.org/abs/2607.26791)
- A separate vendor test (Permiso, Feb 2026) had an AI agent run a purple-team exercise in AWS and found every technique in its chain triggered alerts, i.e. no independent source supports 30–40% as a general constant. — [Permiso blog](https://permiso.io/blog/can-an-ai-agent-run-a-purple-team-exercise)

**AgenticRepair (arXiv 2607.29422) — EXISTS; 73% VERIFIED (author-reported); "25 still exploitable" seen only secondhand**
- Title: "AgenticRepair: Multi-Faceted Program Context Engineering for Agentic Vulnerability Repair"; authors Michael Fu, Qiyue Mei, Patanamon Thongtanunam, Kla Tantithamthavorn; v1 dated 2026-07-31, cs.SE. — [arXiv PDF](https://arxiv.org/pdf/2607.29422)
- Result: 73% success (220/300) on SEC-bench's 300 instances with sanitizer-based verification; about 29 points above the strongest baseline tested. Self-reported. — [arXiv HTML](https://arxiv.org/html/2607.29422)
- Architecture: three LLM sub-agents, one per context gap — code structure, runtime execution, commit history. — [arXiv PDF](https://arxiv.org/pdf/2607.29422)
- Failure analysis: the paper examines "the 80 failures" using SEC-bench's taxonomy, including "Still Vulnerable (SV) — the patch compiled successfully, but the vulnerability remained exploitable under sanitizer testing." — [arXiv HTML](https://arxiv.org/html/2607.29422)
- Per-category counts (secondary): 53 improper-format patches and 25 compiled-but-still-vulnerable among the 80. — [API Made podcast summary](https://apimade.com/podcasts/research/agenticrepair-multi-faceted-program-context-engineering-for-agenti-3569ff27/)
- Conflicting number: the ContraFix paper evaluates an "Agenticrepair-GPT-5.2" configuration and reports a 23.5% *semantic* repair rate on SEC-bench — a different metric and setup. — [ContraFix, arXiv 2605.17450](https://arxiv.org/pdf/2605.17450)

**SEC-bench (NeurIPS 2025) — VERIFIED**
- "SEC-bench: Automated Benchmarking of LLM Agents on Real-World Software Security Tasks", arXiv 2506.11791, NeurIPS 2025 poster. — [NeurIPS proceedings](https://proceedings.neurips.cc/paper_files/paper/2025/hash/a9168f1c54e5147027f1e8cf83e1a775-Abstract-Conference.html), [NeurIPS poster page](https://neurips.cc/virtual/2025/poster/118134)
- Final-version headline: state-of-the-art code agents reach "at most 18.0% success in PoC generation and 34.0% in vulnerability patching" on the full dataset. — [arXiv 2506.11791](https://arxiv.org/pdf/2506.11791)
- The June 2025 version reported 12.5% PoC and 31.5% patching; cite the 18.0% / 34.0% figures from arXiv v2 (Oct 2025) / NeurIPS. — [author publication page](https://lhxxh.github.io/publication/neurips_2025)
- Benchmark construction uses a multi-agent scaffold that builds repos with harnesses, reproduces vulnerabilities in isolated environments and generates gold patches, at $0.87 per instance. — [NeurIPS proceedings](https://proceedings.neurips.cc/paper_files/paper/2025/hash/a9168f1c54e5147027f1e8cf83e1a775-Abstract-Conference.html)
- SEC-bench uses real C/C++ projects, native builds with real entry points, human-readable PoCs, and sanitizer-based oracles. — [arXiv 2607.29422](https://arxiv.org/pdf/2607.29422)

**DARPA AIxCC finals (Aug 2025, DEF CON 33) — VERIFIED, with a denominator correction**
- Placement: Team Atlanta 1st ($4M), Trail of Bits 2nd, Theori 3rd. — [Infosecurity Magazine](https://www.infosecurity-magazine.com/news/defcon-ai-cyber-challenge-winners/), [Trail of Bits blog, 2025-08-09](https://blog.trailofbits.com/2025/08/09/trail-of-bits-buttercup-wins-2nd-place-in-aixcc-challenge/)
- CRSs identified 54 synthetic vulnerabilities and patched 43, across 54 million lines of code. — [MeriTalk](https://www.meritalk.com/?p=200433), [DARPA results page](https://www.darpa.mil/news/2025/aixcc-results)
- Denominator: DARPA's page carries an editor's note that the administrator determined the final contained **63** synthetic vulnerabilities; 54/63 ≈ 86% and 43/63 ≈ 68%. Axios's early coverage used 70 injected bugs and reported 77% found / 61% patched. — [DARPA results page](https://www.darpa.mil/news/2025/aixcc-results); earlier count in [Axios](https://www.axios.com/newsletters/axios-future-of-cybersecurity-thought-bubble-04e655f0-73be-11f0-9251-67d188444922)
- The finalists also found 18 real-world (non-injected) vulnerabilities. — [Axios](https://www.axios.com/newsletters/axios-future-of-cybersecurity-thought-bubble-04e655f0-73be-11f0-9251-67d188444922)
- Cost: average cost per competition task of about $152; each team received $50,000 in LLM credits for the final. — [AIxCC finals winners announcement](https://aicyberchallenge.com/finals-winners-announcement/)
- Open source: DARPA said all seven finalist CRSs would be released under an OSI-approved licence; four were available on announcement day. — [AIxCC finals winners announcement](https://aicyberchallenge.com/finals-winners-announcement/)
- Team Atlanta / Atlantis: repo `Team-Atlanta/aixcc-afc-atlantis`, MIT. — [GitHub](https://github.com/Team-Atlanta/aixcc-afc-atlantis)
- Trail of Bits / Buttercup: repo `trailofbits/buttercup`, AGPL-3.0; semifinal and final versions plus a standalone version were released. — [GitHub](https://github.com/trailofbits/buttercup), [Trail of Bits blog, 2025-08-08](https://blog.trailofbits.com/2025/08/08/buttercup-is-now-open-source/)
- Theori / RoboDuck: finals source at `theori-io/aixcc-afc-archive`, AGPL-3.0. — [GitHub](https://github.com/theori-io/aixcc-afc-archive), [Theori aixcc-public](https://github.com/theori-io/aixcc-public)
- SIFT / Lacrosse: semifinal CRS `siftech/asc-crs-lacrosse`, MIT. — [GitHub](https://github.com/siftech/asc-crs-lacrosse)
- Buttercup self-reported finals stats: 28 vulnerabilities across 20 CWEs, 90% accuracy, $181 per point, using only non-reasoning LLMs. — [Trail of Bits Buttercup page](https://www.trailofbits.com/buttercup/)
- Atlantis technical report (arXiv 2509.14589) reports 61% vulnerability coverage and a 72.1% patch success rate for Atlantis alone — a per-team metric, not the 86% / 68% field aggregate. — [arXiv 2509.14589](https://arxiv.org/abs/2509.14589v1)
- Compute in the final: CRSs ran on self-provisioned Azure clusters with budgets of hundreds of dollars per challenge. — [SoK: DARPA's AIxCC, arXiv 2602.07666](https://arxiv.org/html/2602.07666)
- Usability outside the competition: OSS-CRS (arXiv 2603.08566, now an OpenSSF project) is an orchestration framework that runs AIxCC-style CRSs locally in Docker with CPU, memory, network and LLM-budget controls. — [arXiv 2603.08566](https://arxiv.org/html/2603.08566v2), [OpenSSF project page](https://openssf.org/projects/oss-crs/), [GitHub ossf/oss-crs](https://github.com/ossf/oss-crs)
- OSS-CRS evaluation ran the Atlantis port on one machine with 32 CPU cores and 128 GB RAM, a 24-hour timeout and a $50 LLM budget per campaign; the paper warns an uncapped CRS run "can exceed $1,000 per hour". — [arXiv 2603.08566](https://arxiv.org/html/2603.08566v2)
- Buttercup standalone: Trail of Bits says it runs on a typical laptop; a third-party blog lists 8 cores, 16 GB RAM, Docker and one LLM API key, targeting C and Java code. — [Trail of Bits blog, 2025-08-08](https://blog.trailofbits.com/2025/08/08/buttercup-is-now-open-source/); specs from [brightcoding.dev, 2025-08-18 (secondary)](https://blog.brightcoding.dev/2025/08/18/meet-buttercup-the-ai-powered-cyber-reasoning-system-that-finds-and-fixes-bugs-while-you-sleep)

**CVE-Bench (~13%) — VERIFIED**
- "CVE-Bench: A Benchmark for AI Agents' Ability to Exploit Real-World Web Application Vulnerabilities", Zhu et al. (UIUC Kang Lab), ICML 2025, PMLR v267, arXiv 2503.17332. — [PMLR](https://proceedings.mlr.press/v267/zhu25i.html), [ICML poster](https://icml.cc/virtual/2025/poster/46522)
- 40 critical-severity CVEs in real web applications, each with a reference exploit. — [arXiv 2503.17332v4](https://arxiv.org/html/2503.17332v4)
- The 13% is the *best* case: teams of LLM agents with tools such as sqlmap, five attempts, one-day setting (vulnerability description given). A Cybench baseline agent scored 2.5% in the same setting. — [arXiv 2503.17332v4](https://arxiv.org/html/2503.17332v4)

**Survey quantifying the lab-vs-real gap — FOUND**
- "A Survey of LLM-Driven Penetration Testing: Taxonomy, Co-Evolution, and Open Challenges" (arXiv 2607.02605, Jul 2026) analyses 81 papers from 2023–2026 and argues CTF-style testbeds overestimate real capability and binary success metrics cannot separate capability from benchmark alignment. — [arXiv 2607.02605](https://arxiv.org/html/2607.02605v1)
- Its headline example: PentestAgent scores 21% on AutoPenBench but 74.2% on its own 67-target benchmark — a 53.2-point gap attributed to benchmark choice. — [arXiv 2607.02605](https://arxiv.org/html/2607.02605v1)
- PentestEval (arXiv 2512.14233, Dec 2025): end-to-end pipelines reach only 31% success; "fully autonomous agents achieve low success rates". — [arXiv 2512.14233](https://arxiv.org/html/2512.14233)
- The widely quoted "87%" comes from a 15-CVE test where GPT-4 was given the CVE description; without it the same agent scored 7%. — [CyberOrbit blog (secondary)](https://cyberorbit.ai/blog/ai-pentest-accuracy-13-percent-real-cves-2026)

### Inferences
- SecRespond evaluates investigation and *planned* remediation from a disk snapshot plus alerts; the retrieved material describes "planning scores" and "remediation plans". Describing it as agents "remediating real cloud hosts" probably overstates what is executed. This needs a check of the paper's method section.
- The AIxCC 86% / 68% are field-level union figures across seven well-funded teams on synthetic bugs in OSS-Fuzz-style C/Java targets; the best single system (Atlantis) reports 61% coverage. A solo builder should plan around the single-system figure.
- AgenticRepair's 73% (sanitizer-pass) versus a 23.5% semantic-repair figure for an "AgenticRepair" configuration in another paper suggests that "PoC no longer crashes" overstates true fix rates, but the two numbers were not reconciled here.

### Gaps
- **Could not verify**: that SecRespond agents' plans specifically "skipped credential rotation and post-cleanup checks". Search results returned nothing specific on those two items; the closest verified wording is failure to produce "comprehensive, verified remediation plans".
- **Could not verify against the primary table**: AgenticRepair's 25 still-vulnerable count (secondary source only; 53 + 25 = 78, so two failures are in other categories).
- SEC-bench per-model PoC and patch rates were not retrieved; only the "at most" figures.
- Repos and licences for the other finalists (Shellphish "Artiphishell", "All You Need Is a Fuzzing Brain", 42-b3yond-6ug, the Lacrosse finals repo) were not found in this session.
- No official Buttercup hardware spec or per-run cost was retrieved; the 8-core/16 GB figure is third-party.
- CVE-Bench's zero-day-setting figure was not retrieved.

---

## 2. Open-source and commercial offensive / pentest agents in 2026

### Takeaway
There are many open-source pentest agents, but almost every published score is self-reported on the XBOW 104-challenge suite or a modified fork of it, and no standardized independent comparison of PentAGI, Strix, CAI and Shannon was found. The only rigorous live-environment comparison is the Stanford ARTEMIS study.

### Cited Findings

**Open-source agents**
- Strix: Apache-2.0; roughly 74k stars and v1.7.0 on one listing, "50k+" on another (early Nov 2026); oriented to web/API testing with proof-of-concept exploits. — [aipentestingtools.com](https://aipentestingtools.com/open-source/), [Strobes](https://strobes.co/blog/open-source-agentic-pentesting-tools/) — **PROMISING** (popular; no independent score found)
- Shannon (Keygraph): open-source edition AGPL-3.0, about 51k stars; one comparison site lists it as proprietary, so check the LICENSE file. — [aipentestingtools.com](https://aipentestingtools.com/open-source/); conflicting licence in [dark-moon.org](https://dark-moon.org/comparison/)
- Shannon's headline: 96.15% (100/104) on a "cleaned, hint-free" fork of the XBOW benchmark in **white-box (source-available)** mode. Keygraph itself says this is not apples-to-apples with other published scores. — [Keygraph xben results README (mirror)](https://github-users.yhajoa.workers.dev/KeygraphHQ/shannon/blob/d6b1097e695dbc52f2e23377a4d4b7e99167c47e/xben-benchmark-results/README.md) — **PROMISING tool, HYPE headline number**
- Shannon limits: requires source code in `./repos/`; executes real exploits that can corrupt databases and trigger alerts; a reviewer says it missed privilege escalation via role confusion that human audits caught. Pro tier is $50 per active developer per month; "~$50 per run" appears only in secondary blogs. — [byteiota](https://byteiota.com/?p=9751), [agentconn review](https://agentconn.com/blog/shannon-ai-pentester-review-autonomous-web-security-2026)
- Third-party critique (0sec, Apr 2026): the upstream XBOW benchmark "is not directly runnable today", the Keygraph fork timed out at 330 minutes in a sequential run, and several scoring denominators are in use — XBOW-suite scores are hard to compare. — [0sec "The Unsolved Nine"](https://0sec-ai-homepage.pages.dev/blog/2026-04-07-the-unsolved-nine)
- PentAGI (vxcontrol): MIT source, about 34k stars; an EULA applies to its images; self-hosted, network-focused. — [aipentestingtools.com](https://aipentestingtools.com/open-source/), [devtoollab](https://devtoollab.com/blog/best-ai-penetration-testing-tools) — **PROMISING** (no measured score found)
- CAI (Alias Robotics): about 9.8k stars; GitGuardian says the repo was archived 2026-08-28, another listing shows a last commit of 2026-08-22 with no archive note; described as the most flexible framework for custom agents. — [GitGuardian](https://blog.gitguardian.com/ai-pentesting-tools-beyond-artex/), [aipentestingtools.com](https://aipentestingtools.com/open-source/)
- CAI competition results (all reported by Alias Robotics): #1 among AI teams and #6 of 163 overall in HTB "AI vs Human" CTF (19 flags); #1 at Neurogrid CTF (41/45 flags, $50,000 prize); Dragos OT CTF 2025 rank 1 at hours 7–8 but 6th overall of 1,000+ teams after pausing at 24h; peak #22 of 8,129 teams in Cyber Apocalypse 2025. — [arXiv 2512.02654](https://arxiv.org/pdf/2512.02654), [arXiv 2511.05119](https://arxiv.org/pdf/2511.05119) — **PROMISING** (public scoreboards, but vendor-authored write-ups)
- Alias Robotics' "11× faster and 156× cheaper" and "up to 3,600×" claims rest on its own methodology. — [Alias Robotics benchmarking page](https://aliasrobotics.com/benchmarking.php) — **HYPE**
- MAPTA (academic, multi-agent web pentest, arXiv 2508.20816): 76.9% (80/104) on XBOW black-box; 57% on XSS and **0% on blind SQL injection**. — [arXiv 2508.20816](https://arxiv.org/pdf/2508.20816) — **PROMISING**
- AWE (arXiv 2603.00960) re-ran the 104-challenge set and reports MAPTA 76.9% vs AWE 51.9% — the nearest thing to an independent replication of an XBOW-suite score. — [arXiv 2603.00960](https://arxiv.org/html/2603.00960)
- Cyber-AutoAgent: 84.62% on XBOW at v0.1.3 per third-party tables; LuaN1aoAgent self-reports 90.4% on DeepSeek-V3.2; a fully local agent reports ~78%. — [FireCompass XBEN explainer](https://firecompass.com/blog-xben-benchmark/), [LuaN1aoAgent results](https://sanmuzzzzz-luan1aoagent-56.mintlify.app/project/benchmark-results), [xoxruns on Medium](https://xoxruns.medium.com/feedback-driven-iteration-and-fully-local-webapp-pentesting-ai-agent-achieving-78-on-xbow-199ef719bf01)
- HexStrike AI: an MCP server exposing "150+" security tools and "12+ autonomous AI agents" to Claude/GPT/Copilot (its own count). — [GitHub 0x4m4/hexstrike-ai](https://github.com/0x4m4/hexstrike-ai)
- Check Point (Sept 2025) reported dark-web chatter of threat actors trying HexStrike-AI against fresh Citrix NetScaler zero-days and *claiming* exploitation time cut from days to under 10 minutes. — [Check Point blog](https://blog.checkpoint.com/executive-insights/hexstrike-ai-when-llms-meet-zero-day-exploitation/)
- Counter-view: HexStrike is "simply orchestrating common tools such as Nmap and Katana, generating the same fingerprints". — [Communications of the ACM](https://cacm.acm.org/news/hexstrike-exploit-raises-cyber-stakes/) — tool-server idea **PROVEN as plumbing**, "150 tools = capability" **HYPE**
- Claude-Code-native: `anthropics/claude-code-security-review` is a GitHub Action plus `/security-review` command; the default prompt flags only issues it is >80% confident are exploitable and runs a false-positive filtering pass with user-supplied filter instructions; the README warns of more false positives on many-commit PRs. — [GitHub](https://github.com/anthropics/claude-code-security-review), [command prompt file](https://github.com/anthropics/claude-code-security-review/blob/main/.claude/commands/security-review.md)
- Anthropic says automated reviews "should complement, not replace, existing security practices and manual code reviews". — [Claude help center](https://support.claude.com/en/articles/11932705-automated-security-reviews-in-claude-code) — **PROVEN as a plug-in; accuracy unmeasured**
- ARTEMIS (Stanford/CMU/Gray Swan scaffold): source code is public. — [Stanford RegLab](https://reglab.stanford.edu/publications/comparing-ai-agents-to-cybersecurity-professionals-in-real-world-penetration-testing) — **PROVEN** (see section 3)
- Landscape counts: GitGuardian catalogued 45 AI pentesting tools; AppSecSanta tracked 39+. — [GitGuardian](https://blog.gitguardian.com/ai-pentesting-tools-beyond-artex/), [AppSecSanta](https://appsecsanta.com/research/ai-pentesting-agents-2026)

**Commercial and big-vendor**
- XBOW: commercial, proprietary, enterprise-only pricing. Its 85% on the 104-challenge benchmark is its own figure. — [xhack.io](https://xhack.io/blog/autonomous-ai-hacking-agent), [FireCompass](https://firecompass.com/blog-xben-benchmark/)
- XBOW reached #1 on HackerOne's **US** leaderboard (June 2025), ranked by **reputation**, not earnings; it was 6th overall on 2025-06-25 and later claimed global #1 for Q2. — [TechRepublic](https://www.techrepublic.com/article/news-ai-xbow-tops-hackerone-us-leaderboad/), [Gigazine](https://gigazine.net/news/20250625-hackerone-xbow), [XBOW blog, 2025-08-18](https://xbow.com/blog/xbow-on-hackerone-whats-next)
- XBOW's security team reviewed findings before submission to comply with HackerOne policy on automated tools. — [XBOW "Top 1: how XBOW did it"](https://xbow.com/blog/top-1-how-xbow-did-it/) — **PROVEN that it finds real bugs at scale; "matches human pentesters" framing is HYPE**
- Critique of the milestone framing. — [LessWrong](https://www.lesswrong.com/posts/qefrWyeiMvWEFRitN/be-skeptical-of-milestone-announcements-by-young-ai-startups)
- Google Big Sleep: credited with 20 flaws in FFmpeg and ImageMagick (Aug 2025) and with catching SQLite CVE-2025-6965 before exploitation; internal tool. — [agentsast.com review](https://agentsast.com/tools/big-sleep/) — **PROVEN** (real CVEs), not available to plug in
- Google CodeMender (Oct 2025): 72 security fixes upstreamed in six months, to projects as large as 4.5M lines; every patch human-reviewed before submission. — [Google DeepMind](https://deepmind.google/blog/introducing-codemender-an-ai-agent-for-code-security/)
- OpenAI Aardvark (Oct 2025; renamed Codex Security 2026-03-06, research preview): identified 92% of known and synthetically introduced vulnerabilities in unnamed "golden" repositories; ten disclosed findings received CVE IDs; Codex-generated patches go to human review. — [OpenAI](https://openai.com/index/introducing-aardvark/), [The Register, 2025-10-31](https://www.theregister.com/2025/10/31/openai_aardvark_agentic_security) — 92% is **vendor-reported on an undisclosed set**
- Anthropic Claude Mythos Preview (Apr 2026), UK AISI evaluation: 73% on expert-level CTF tasks; first model to fully solve the 32-step "The Last Ones" corporate-network range (3 of 10 attempts; average 22/32 steps vs 16 for Opus 4.6; estimated 20 human hours). — [TOSWO summary of AISI evaluation](https://www.toswo.com/simulations/claude-mythos-preview-cyber-evaluation-by-uk-aisi), [Frontier Risk substack](https://frontierrisk.substack.com/p/anthropics-claude-mythos-preview) — **PROVEN** (independent government evaluator), secondary reporting
- AISI caveats: its ranges lack active defenders and are easier than a mature enterprise, so results may overstate performance against hardened systems. — [Frontier Risk substack](https://frontierrisk.substack.com/p/anthropics-claude-mythos-preview)
- Cybench is saturated: Mythos and Opus 4.6 both reportedly score 100%, and Anthropic calls it "no longer sufficiently informative". — [Frontier Risk substack](https://frontierrisk.substack.com/p/anthropics-claude-mythos-preview)
- Project Glasswing restricts Mythos to a few defensive partners (AWS, Microsoft, Google, Linux Foundation); Anthropic says it scanned 1,000+ open-source projects. — [Penligent write-up](https://www.penligent.ai/hackinglabs/project-glasswing-and-claude-mythos/)
- Microsoft Security Copilot: see section 4.

### Inferences
- Architecture pattern across the open-source field: multi-agent or planner/executor designs with specialist roles (MAPTA, Shannon, Wazuh-Autopilot, AgenticRepair's three sub-agents, ARTEMIS's up to 8 parallel sub-agents) dominate; single-loop scaffolds (Codex, Claude Code used raw) underperformed in ARTEMIS.
- XBOW-suite scores in the 77–96% range are effectively saturated and methodologically non-comparable (white-box vs black-box, cleaned forks, different denominators). They should not be used to choose a tool.
- Safety controls are thin in the open-source tools as documented in what was retrieved: Shannon explicitly warns of destructive exploitation; scope enforcement and rate limiting are not described in any retrieved source.

### Gaps
- No search results were obtained (budget exhausted) for: Strix and PentAGI internal architecture and safety controls; PentestGPT's 2026 status; RunSybil; Horizon3 NodeZero; Pentera; Anthropic's "Claude Code Security" product and its published open-source vulnerability counts; Google Sec-Gemini. **No reliable sources were gathered on these in this session.**
- Cost per run is not reliably reported for any open-source pentest agent; the only figures are secondary (~$50/run for Shannon) or competition-level ($152/task AIxCC, $18/hour ARTEMIS variant).
- The claim that 90% of XBOW's HackerOne score came from XSS appeared only as a secondhand report and is unverified.
- A search summary attributed the HexStrike/Citrix activity to a named threat group; that attribution was not confirmed against Check Point's text and is omitted.
- CAI's archive status is contradictory across sources.

---

## 3. What independent evaluations say about real-target success, and where agents fail

### Takeaway
On a live 10-hour enterprise engagement, the best purpose-built scaffold (ARTEMIS) beat 9 of 10 professionals at lower cost, but off-the-shelf scaffolds lost to most humans, and agents had more false positives and missed a GUI-reachable critical RCE that 80% of humans found. On real CVEs without hand-holding, success remains low (≤13% on CVE-Bench; 31% end-to-end on PentestEval).

### Cited Findings
- ARTEMIS study (arXiv 2512.09882, Dec 2025, revised Mar 2026): target was Stanford's CS network (Unix, IoT, Windows, embedded); 10 professionals with student-level credentials and a 10-hour window. — [arXiv 2512.09882](https://arxiv.org/html/2512.09882v1), [Gray Swan](https://www.grayswan.ai/blog/conducting-the-first-live-enterprise-comparison-between-agents-and-human-professionals)
- ARTEMIS placed second overall: 9 valid vulnerabilities, 82% valid-submission rate, outperforming 9 of 10 humans. — [Cyber Security News](https://cybersecuritynews.com/ai-agent-outperformed-human-penetration-testers/amp/)
- Cost: some ARTEMIS variants cost $18/hour versus $60/hour for professionals; it ran up to 8 concurrent sub-agents. — [Cyber Security News](https://cybersecuritynews.com/ai-agent-outperformed-human-penetration-testers/amp/)
- Failures: higher false-positive rates; struggled with GUI-based tasks; ~80% of humans found a critical RCE in the TinyPilot web interface that the agents missed entirely. — [Cyber Security News](https://cybersecuritynews.com/ai-agent-outperformed-human-penetration-testers/amp/)
- Existing scaffolds (Codex, Claude Code, CyAgent, Incalmo, MAPTA) "underperformed all but two human participants". — [Stanford RegLab](https://reglab.stanford.edu/publications/comparing-ai-agents-to-cybersecurity-professionals-in-real-world-penetration-testing) — **PROVEN**
- CVE-Bench: ≤13% of 40 real critical web CVEs, best case. — [arXiv 2503.17332v4](https://arxiv.org/html/2503.17332v4) — **PROVEN**
- PentestEval: 31% end-to-end. — [arXiv 2512.14233](https://arxiv.org/html/2512.14233)
- Class-specific failure: MAPTA 0% on blind SQL injection and 57% on XSS; a blog reports Cyber-AutoAgent also fails blind SQLi. — [arXiv 2508.20816](https://arxiv.org/pdf/2508.20816), [xoxruns on Medium](https://xoxruns.medium.com/feedback-driven-iteration-and-fully-local-webapp-pentesting-ai-agent-achieving-78-on-xbow-199ef719bf01)
- Benchmark-choice effect: the same agent swings 21% → 74.2% between benchmarks. — [arXiv 2607.02605](https://arxiv.org/html/2607.02605v1)
- Frontier-model ranges: Mythos Preview fully solved a 32-step network range in 3/10 attempts with no active defender. — [TOSWO summary](https://www.toswo.com/simulations/claude-mythos-preview-cyber-evaluation-by-uk-aisi)
- Human-competition evidence (vendor-authored): CAI topped AI teams in HTB events but in the Dragos OT CTF human teams overtook it "through extended operation". — [arXiv 2511.05119](https://arxiv.org/pdf/2511.05119)
- Defender side mirrors the pattern: agents anchor on visible alerts and under-investigate silent evidence. — [arXiv 2607.26791](https://arxiv.org/abs/2607.26791)
- Related 2026 papers surfaced by title only: "Autonomous LLM Agents & CTFs: A Second Look" (arXiv 2605.21497), "Big Enough to Break Out: Tracking the Rising Capability of LLM Penetration-Testing Agents" (arXiv 2609.10780), "Red-Teaming the Agentic Red-Team" (arXiv 2606.24496), "Toward Secure AI-Powered Penetration Testing Agents" (arXiv 2609.16694). — [2605.21497](https://arxiv.org/pdf/2605.21497), [2609.10780](https://arxiv.org/pdf/2609.10780), [2606.24496](https://arxiv.org/pdf/2606.24496), [2609.16694](https://arxiv.org/pdf/2609.16694)

### Inferences
- Reliable failure areas, as far as the retrieved evidence goes: anything requiring inference without direct feedback (blind SQLi), GUI or browser-driven flows, findings needing validation discipline (false positives), and long-running persistence of effort. Evidence specifically on business logic, multi-step auth flows and chained exploits was not retrieved, apart from one reviewer's note that Shannon missed role-confusion privilege escalation.
- For a single Linux VM and the owner's own apps, the white-box setting (source available) is the favourable case, and the agent-as-attacker result that matters most is ARTEMIS: scaffolding quality, not model choice alone, separated winners from losers.

### Gaps
- Not retrieved (search budget exhausted): current Cybench, NYU CTF Bench, CyberSecEval 3/4 and AutoPenBench per-model numbers; HackTheBox's own (non-vendor) AI-vs-human analysis; the content of the four title-only 2026 papers above.
- No retrieved study measures agent performance on business-logic flaws or stateful multi-step auth directly.

---

## 4. AI SOC / blue-team / incident-response agents

### Takeaway
Independent measurement of SOC agents is weak: the best-known "study" (CSA/Dropzone) and Microsoft's RCT measure **humans assisted by AI** and are vendor-linked; benchmarks that test agents directly show low absolute scores (ExCyTIn best 0.368 → 0.606; CyberSOCEval 15–28% on malware analysis; SecRespond zero full solves). Open-source building blocks exist mainly as MCP servers for Wazuh and Velociraptor.

### Cited Findings
- ExCyTIn-Bench (Microsoft, arXiv 2507.14201, Jul 2025): agents query a MySQL mirror of an Azure tenant with 57 Sentinel-style tables, 8 multi-stage attacks, 44 days of logs. Original results: average reward 0.249, best 0.368 (o4-mini). A later version reports Claude Opus 4.5 at 0.606. — [arXiv 2507.14201](https://arxiv.org/pdf/2507.14201) — **PROVEN benchmark; vendor-built**
- Critique: ExCyTIn reports no confidence intervals or sensitivity analysis; SentinelOne Labs argues current benchmarks fail SOC teams. — [SentinelOne Labs](https://www.sentinelone.com/labs/llms-in-the-soc-part-1-why-benchmarks-fail-security-operations-teams/)
- CyberSOCEval (Meta + CrowdStrike, arXiv 2509.20166, Sept 2025, open source): 609 malware-analysis and 588 threat-intel questions; models score 15–28% on malware analysis and 43–53% on threat intelligence; reasoning models do not get the boost seen in coding/maths. — [arXiv 2509.20166](https://arxiv.org/pdf/2509.20166), [Meta AI](https://ai.meta.com/research/publications/cybersoceval-benchmarking-llms-capabilities-for-malware-analysis-and-threat-intelligence-reasoning/) — **PROVEN**
- SIR-Bench (AWS researchers, arXiv 2604.12040, Apr 2026): 794 test cases from 129 anonymized incident patterns; the authors' own agent scores 97.1% true-positive detection, 73.4% false-positive rejection, 5.67 novel key findings per case. — [arXiv 2604.12040](https://arxiv.org/html/2604.12040v1) — **PROMISING** (author-reported)
- SecRespond (Jul 2026): 23 models, no full solve on any of 10 ranges; persistence weakest. — [arXiv 2607.26791](https://arxiv.org/abs/2607.26791) — **PROVEN** as a negative result
- CSA + Dropzone "Beyond the Hype" (Oct 2025): 148 analysts randomly assigned to investigate with or without Dropzone's AI; 45–61% faster; accuracy gain reported as 22–29% (Dropzone) or 23% (another summary); 94% viewed AI more positively afterwards. — [Cloud Security Alliance](https://cloudsecurityalliance.org/artifacts/a-benchmark-study-of-ai-agents-in-the-soc), [SC World](https://www.scworld.com/news/ai-assisted-soc-analysts-up-to-61-faster-29-more-accurate-study-finds), [Dropzone press release](https://www.dropzone.ai/press-release/new-study-from-dropzone-ai-and-the-cloud-security-alliance-demonstrates-effectiveness-of-ai-augmentation-in-socs) — **PROMISING** (controlled, but vendor-sponsored and human-in-the-loop)
- Microsoft Phishing Triage Agent RCT (arXiv 2511.13860, Nov 2025): 167 professional analysts each triaged a 25-email queue with or without the agent. Microsoft markets 78% faster triage and 77% more accurate verdicts; a separate "up to 550% faster" figure is from simulated scenarios. The agent was later renamed Security Alert Triage Agent. — [arXiv 2511.13860](https://arxiv.org/html/2511.13860v1), [Microsoft Security blog, 2025-11-18](https://www.microsoft.com/en-us/security/blog/2025/11/18/agents-built-into-your-workflow-get-security-copilot-with-microsoft-365-e5/), [Microsoft Learn](https://learn.microsoft.com/en-us/defender-xdr/phishing-triage-agent) — **PROMISING** (vendor RCT)
- Open source — Wazuh-Autopilot (gensecaihq): self-hosted 13-agent swarm on Strands Agents that reaches Wazuh only through the Wazuh MCP Server (v4.3.0, 55 tools); policy-gated autonomy, approvals, RBAC, audit, evals; supports Anthropic, vLLM, LiteLLM and air-gapped Ollama. — [GitHub](https://github.com/gensecaihq/Wazuh-Autopilot) — **PROMISING** (no measured accuracy)
- Open source — SOCFortress publishes `velociraptor-mcp-server` (AGPL-3.0, updated Oct 2026) and a `wazuh-mcp-server`. — [SOCFortress GitHub org](https://github.com/socfortress)
- Open source — `zhadyz/AI_SOC`: Wazuh-format ingestion with local Ollama triage; last updated about a year ago. — [GitHub](https://github.com/zhadyz/AI_SOC) — research prototype
- Supporting platforms: DFIR-IRIS is LGPL-3.0 case management without an automation engine; Plaso and Timesketch are Apache-2.0. — [Heimdal SOAR comparison](https://heimdalsecurity.com/blog/open-source-soar-tools/), [NHIMG DFIR landscape](https://nhimg.org/open-source-dfir-tools-landscape-guide)
- Survey: "Large Language Models for Security Operations Centers: A Comprehensive Survey" (arXiv 2509.10858). — [arXiv 2509.10858](https://arxiv.org/pdf/2509.10858)
- Purple-team data point (vendor, Feb 2026): Permiso ran an AI agent as purple-team operator in AWS; every technique triggered alerts, and the exercise exposed an instruction-following gap in the agent. — [Permiso](https://permiso.io/blog/can-an-ai-agent-run-a-purple-team-exercise)

### Inferences
- The measured benefit is "analyst + AI is faster and somewhat more accurate on escalated alerts", not "agent autonomously contains an incident". Autonomous end-to-end response has only negative published results (SecRespond).
- For one VM, the SecRespond persistence finding translates into a design rule: do not rely on the agent's alert-driven reasoning for persistence; run deterministic sweeps (crontabs, systemd units, authorized_keys, shell rc files, SUID changes) and feed results in.

### Gaps
- No search results were obtained (budget exhausted) for independent measurement of Dropzone, Prophet Security, 7AI, Exaforce or CrowdStrike Charlotte AI beyond the CSA study; no reliable sources were gathered on their accuracy claims.
- Nothing was found on Falco + LLM triage, a Timesketch-specific agent or MCP server, Google Sec-Gemini, or CTIBench / "SOC-bench" results.
- The 78% / 77% Microsoft figures were not confirmed against the RCT paper's tables.
- STAIR (arXiv 2608.09524, agentic IR planning) surfaced by title only.

---

## 5. AI vulnerability repair beyond AIxCC

### Takeaway
Vendors publish volume and speed (72 upstreamed fixes; 92% detection on undisclosed repos; median 28 minutes to fix) but not correctness rates. The only quantified "compiles but still exploitable" evidence retrieved is academic: 34% best-case patching on SEC-bench in 2025, 73% for AgenticRepair in 2026 with a reported 25 of 80 failures still vulnerable, and a much lower semantic-repair figure in a competing paper.

### Cited Findings
- SEC-bench baseline: at most 34.0% patch success for 2025 code agents. — [NeurIPS proceedings](https://proceedings.neurips.cc/paper_files/paper/2025/hash/a9168f1c54e5147027f1e8cf83e1a775-Abstract-Conference.html)
- AgenticRepair: 73% (220/300), sanitizer-verified; failures dominated by improper-format patches (53) and still-vulnerable patches (25) per a secondary summary. — [arXiv 2607.29422](https://arxiv.org/html/2607.29422), [API Made (secondary)](https://apimade.com/podcasts/research/agenticrepair-multi-faceted-program-context-engineering-for-agenti-3569ff27/) — **PROMISING**
- ContraFix reports an "Agenticrepair-GPT-5.2" configuration at 23.5% semantic repair rate on SEC-bench. — [arXiv 2605.17450](https://arxiv.org/pdf/2605.17450)
- AIxCC: 43 of 63 synthetic vulnerabilities patched by the field (68%); Atlantis alone reports 72.1% patch success. — [DARPA](https://www.darpa.mil/news/2025/aixcc-results), [arXiv 2509.14589](https://arxiv.org/abs/2509.14589v1) — **PROVEN**
- CodeMender: 72 fixes upstreamed in six months, all human-reviewed; a later secondary tally cites 178 fixes (48 patched, 130 hardened). In preview on Google Cloud per one review. — [Google DeepMind](https://deepmind.google/blog/introducing-codemender-an-ai-agent-for-code-security/), [agentsast.com](https://agentsast.com/tools/big-sleep/) — **PROVEN** (accepted upstream), no failure rate published
- Aardvark / Codex Security: 92% detection on "golden" repos (unnamed), ten CVEs; patches are proposed for human one-click merge. — [OpenAI](https://openai.com/index/introducing-aardvark/), [CyberScoop](https://cyberscoop.com/openai-aardvark-security-and-patching-model-beta/) — detection figure **vendor-reported**; no patch-correctness figure
- GitHub Copilot Autofix: GitHub's May–July 2024 beta data shows a median 28 minutes to fix versus 1.5 hours manually, measured only on alerts where Autofix produced a fix; GitHub has not disclosed acceptance rates; output is non-deterministic. — [Augment Code comparison](https://www.augmentcode.com/tools/best-ai-sast-tools), [Pixee comparison](https://www.pixee.ai/blog/best-automated-remediation-tools-2026) — **PROVEN deployment, correctness unmeasured**
- Semgrep Assistant: 2024 vendor post says findings Assistant rated true-positive had more than double the fix rate; a 2026 comparison cites "95% agreement with security reviewers across 6M+ findings" (unverified against Semgrep); Semgrep Autofix public beta reportedly began 2026-03-16. — [Semgrep blog, 2024](https://semgrep.dev/blog/2024/ai-assisted-remediation/), [Augment Code](https://www.augmentcode.com/tools/semgrep-ai-code-review)
- Practitioner consensus in comparison posts: a confidently wrong autofix is worse than none, so verification is the part that matters. — [safeguard.sh](https://safeguard.sh/resources/blog/top-sast-auto-fixing-tools)
- Relevant 2026 papers surfaced by title only: "PatchBench: Evaluating AI Agents for Vulnerability Patching" (arXiv 2609.04075); "When Passing Tests Hides Vulnerabilities: An Empirical Study of Silent Failures in Agentic Systems" (arXiv 2609.10548); "SecProbe: Adaptive Evaluation of Coding Agents on Cybersecurity Vulnerabilities" (arXiv 2609.33763). — [2609.04075](https://arxiv.org/pdf/2609.04075), [2609.10548](https://arxiv.org/html/2609.10548v1), [2609.33763](https://arxiv.org/html/2609.33763v1)

### Inferences
- "PoC no longer triggers the sanitizer" is the standard oracle, and it is necessary but not sufficient: roughly a third of AgenticRepair's failures were patches that built cleanly yet stayed exploitable, and a semantic-equivalence metric gives a far lower rate for a similarly named system. An auto-fix loop for the user's own apps needs both the exploit re-run and the functional test suite, plus human review before merge — which is what CodeMender, Aardvark and AIxCC all do.
- All strong repair results are on C/C++ (and Java in AIxCC) memory-safety bugs with sanitizers. No retrieved evidence covers auto-repair of web-app logic bugs in Python/JS/Go.

### Gaps
- No measured "plausible but wrong patch" rate was found for Copilot Autofix, Semgrep, Snyk agent fix, CodeMender or Aardvark. No search results were obtained on Snyk at all.
- Meta's AutoPatchBench numbers and the contents of PatchBench / "When Passing Tests Hides Vulnerabilities" were not retrieved (search budget exhausted).

---

## 6. Architectural lessons that recur in the systems that work

### Takeaway
The systems with measured results wrap the LLM in deterministic oracles (sanitizers, PoC re-execution, test suites), decompose work across specialist sub-agents with parallelism, give agents purpose-built tools rather than a bare shell, cap spend at a proxy, and keep a human gate before anything irreversible or externally visible.

### Cited Findings
- Deterministic exploit/patch oracle: SEC-bench and AgenticRepair verify with sanitizer-based oracles and real PoCs. — [arXiv 2607.29422](https://arxiv.org/pdf/2607.29422)
- Runtime context beats static-only context: AgenticRepair's gain comes from adding runtime-execution and commit-history context alongside code structure. — [arXiv 2607.29422](https://arxiv.org/pdf/2607.29422)
- Cheap models inside a strong pipeline suffice: Buttercup took 2nd in AIxCC with "exclusively non-reasoning LLMs" at 90% accuracy. — [Trail of Bits Buttercup page](https://www.trailofbits.com/buttercup/)
- Real tools lift results: on CVE-Bench, agent teams equipped with tools such as sqlmap reached 13% versus 2.5% for a generic CTF agent. — [arXiv 2503.17332v4](https://arxiv.org/html/2503.17332v4)
- Scaffolding and parallel sub-agents matter more than the raw model: ARTEMIS (up to 8 concurrent sub-agents) beat 9 of 10 humans, while raw Codex / Claude Code scaffolds lost to all but two. — [Stanford RegLab](https://reglab.stanford.edu/publications/comparing-ai-agents-to-cybersecurity-professionals-in-real-world-penetration-testing)
- Budget enforcement outside the agent: OSS-CRS enforces a per-CRS LLM dollar budget at an LLM proxy and isolates CPU, memory and network per container. — [arXiv 2603.08566](https://arxiv.org/html/2603.08566v2)
- Confidence threshold plus a separate false-positive filtering pass: Claude Code security review flags only >80%-confidence exploitable issues and runs a filter stage. — [GitHub](https://github.com/anthropics/claude-code-security-review)
- Keep agents away from state-changing actions; gate with policy and approvals: Wazuh-Autopilot's design. — [GitHub](https://github.com/gensecaihq/Wazuh-Autopilot)
- Human review before external submission or merge: XBOW (pre-submission review), CodeMender (all patches human-reviewed), Aardvark (one-click human merge). — [XBOW](https://xbow.com/blog/top-1-how-xbow-did-it/), [Google DeepMind](https://deepmind.google/blog/introducing-codemender-an-ai-agent-for-code-security/), [OpenAI](https://openai.com/index/introducing-aardvark/)
- Alert-anchoring is a systematic failure: agents handle alerted artifacts and miss silent ones such as persistence. — [alphaXiv listing of 2607.26791](https://www.alphaxiv.org/abs/2607.26791)
- Benchmarks with hints or leaked structure inflate scores: Keygraph had to strip descriptive variable names, comments, file paths, titles and Dockerfile configuration to make XBOW "hint-free". — [Keygraph README (mirror)](https://github-users.yhajoa.workers.dev/KeygraphHQ/shannon/blob/d6b1097e695dbc52f2e23377a4d4b7e99167c47e/xben-benchmark-results/README.md)
- The AIxCC SoK covers competition design, CRS architectures and lessons learned across all finalists. — [arXiv 2602.07666](https://arxiv.org/html/2602.07666v1)

### Inferences
- A workable loop for a single VM: deterministic detectors and sweeps produce evidence → LLM triages and plans → every claimed vulnerability must come with a re-runnable PoC → every fix must pass "PoC now fails" and "tests still pass" → human approves merge or any state-changing response.
- The persistence finding and the false-positive finding point the same way: the LLM is the weakest component at exhaustive enumeration and at self-validation, so both should be done by code.

### Gaps
- The fuzzing + LLM hybrid design of the AIxCC CRSs is widely described, but the SoK's specific architectural findings were not retrieved in this session (search budget exhausted); treat "fuzzing + LLM hybrid is what won AIxCC" as unverified here.
- No retrieved source measures the effect of scope enforcement or rate limiting on agent safety.

---

## 7. What a solo builder can plug in versus only borrow from

### Takeaway
Realistic plug-ins are small and boring: the Claude Code security-review action for CI, MCP servers for Wazuh and Velociraptor, Buttercup standalone or OSS-CRS for fuzzable C/Java code, and one white-box web pentest agent (Shannon or Strix) run against a staging copy. The frontier results (Mythos, Big Sleep, XBOW, CodeMender, Aardvark) are not self-hostable and are useful only as design references.

### Cited Findings
- CI plug-in: `anthropics/claude-code-security-review` runs as a GitHub Action on PRs. — [GitHub](https://github.com/anthropics/claude-code-security-review)
- Blue-team plug-ins: Wazuh MCP Server (55 tools) and SOCFortress Velociraptor MCP server (AGPL-3.0). — [Wazuh-Autopilot repo](https://github.com/gensecaihq/Wazuh-Autopilot), [SOCFortress](https://github.com/socfortress)
- Find-and-patch for fuzzable code: Buttercup standalone (AGPL-3.0, laptop-class per Trail of Bits) and OSS-CRS (local Docker, LLM budget cap; Atlantis port evaluated on 32 cores / 128 GB). — [Trail of Bits blog](https://blog.trailofbits.com/2025/08/08/buttercup-is-now-open-source/), [arXiv 2603.08566](https://arxiv.org/html/2603.08566v2)
- White-box web pentest: Shannon (AGPL-3.0, needs source, runs real exploits) and Strix (Apache-2.0). — [aipentestingtools.com](https://aipentestingtools.com/open-source/), [byteiota](https://byteiota.com/?p=9751)
- Tool server: HexStrike AI exposes common security tools over MCP. — [GitHub](https://github.com/0x4m4/hexstrike-ai)
- Evaluation harnesses that can be reused to test one's own agent: SecRespond data (public), SEC-bench, CVE-Bench, CyberSOCEval (open source). — [Hugging Face](https://huggingface.co/datasets/Alibaba-NLP/SecRespond), [arXiv 2506.11791](https://arxiv.org/pdf/2506.11791), [arXiv 2503.17332v4](https://arxiv.org/html/2503.17332v4), [arXiv 2509.20166](https://arxiv.org/pdf/2509.20166)
- Not self-hostable: XBOW (enterprise only), Big Sleep (internal), Mythos (restricted partners), CodeMender (Google Cloud preview), Codex Security (research preview). — [xhack.io](https://xhack.io/blog/autonomous-ai-hacking-agent), [agentsast.com](https://agentsast.com/tools/big-sleep/), [Penligent](https://www.penligent.ai/hackinglabs/project-glasswing-and-claude-mythos/), [OpenAI](https://openai.com/index/introducing-aardvark/)

### Inferences

Classification summary (researcher's judgment from the evidence above):

| Item | Label | Plug in or borrow | Basis |
|---|---|---|---|
| AIxCC result: fuzz + LLM find-and-patch on C/Java | PROVEN | Borrow design; plug in Buttercup standalone / OSS-CRS if code is fuzzable | DARPA-scored, 54/63 found, 43/63 patched |
| Atlantis (MIT) | PROVEN | Borrow; heavy (32 cores / 128 GB in OSS-CRS eval) | AIxCC winner |
| Buttercup (AGPL-3.0) | PROVEN | Plug in as subprocess (AGPL matters only if redistributed or served) | AIxCC 2nd; laptop version |
| Theori RoboDuck (AGPL-3.0) | PROVEN | Borrow (archive repo) | AIxCC 3rd |
| OSS-CRS | PROMISING | Plug in as orchestrator | OpenSSF project, paper results |
| SEC-bench, CVE-Bench, CyberSOCEval, ExCyTIn | PROVEN benchmarks | Use as test harnesses | Peer-reviewed / multi-model |
| SecRespond | PROVEN negative result | Use data; borrow failure taxonomy | 23 models, zero full solves |
| ARTEMIS scaffold | PROVEN | Borrow architecture; code is public | Live comparison vs 10 professionals |
| AgenticRepair | PROMISING | Borrow the three-context design | 73% self-reported |
| Claude Code security review | PROVEN deployment, unmeasured accuracy | Plug in (CI) | Official action |
| Strix | PROMISING | Plug in against staging | Popular; no independent score |
| Shannon | PROMISING | Plug in against staging, white-box only | 96.15% is self-reported on a modified suite |
| PentAGI | PROMISING | Plug in (self-hosted) | No measured score retrieved |
| CAI | PROMISING, maintenance uncertain | Borrow / library | Vendor-authored CTF results; possibly archived |
| HexStrike AI and similar MCP tool servers | PROVEN plumbing / HYPE capability claims | Plug in selectively, with allow-lists | Tool count is not a result |
| Wazuh MCP, Velociraptor MCP, Wazuh-Autopilot | PROMISING | Plug in | No accuracy measurement |
| XBOW | PROVEN at finding real bugs; "human-level pentester" HYPE | Borrow (validators, human review) | Reputation-based US #1; vendor benchmark |
| Big Sleep, CodeMender | PROVEN | Borrow only | Real CVEs, 72 upstreamed fixes |
| Aardvark / Codex Security | PROMISING | Borrow only (or use as a hosted service) | 92% on undisclosed repos |
| Mythos Preview cyber capability | PROVEN (AISI) | Not available | 3/10 on 32-step range, no defenders |
| CSA/Dropzone, Microsoft RCT | PROMISING | Borrow (human + AI framing) | Vendor-linked, human-in-loop |
| "X× faster / cheaper than humans" claims; XBOW-suite scores above 85% as proof of real-world ability | HYPE | Ignore | Unreproduced or non-comparable |

- For a single Linux VM with the owner's own apps, the plug-in set that the evidence supports is: Wazuh or Falco for detection (deterministic), an MCP bridge so the agent can query but not change state, a white-box pentest agent pointed at a staging clone, Claude Code security review in CI, and Buttercup only if there is fuzzable C/Java code. Autonomous remediation on the live host is not supported by any measured result.
- AGPL-3.0 on Buttercup, RoboDuck, Shannon and the Velociraptor MCP server is not a problem for private self-hosting but would bind a redistributed or hosted product.

### Gaps
- Actual install effort, API cost per run and failure behaviour of Strix, PentAGI, Shannon and Wazuh-Autopilot on a small VM were not measured by any retrieved source, and repos could not be inspected directly in this session.
- Licences and activity for all repos should be re-checked at the source; listings conflicted for Shannon and CAI.
- Network access to arxiv.org, alphaxiv.org, dev.to and the GitHub API would be needed to close the "could not verify" items in section 1; the session's search budget also needs raising for the unsearched vendors (NodeZero, Pentera, RunSybil, Prophet, 7AI, Exaforce, Charlotte AI, Snyk, Sec-Gemini).
