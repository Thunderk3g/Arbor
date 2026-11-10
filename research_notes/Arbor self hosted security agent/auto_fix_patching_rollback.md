# Automated security remediation on a self-managed Linux VM: patching, hardening, LLM code fixes, verification and rollback (as of 2026-11-10)

> **Read this first — verification depth of these notes.**
> - Every page fetch failed in this session (arxiv.org, huggingface.co, sre.google, team-atlanta.github.io and others are outside the session's allowed network domains), and the shared web-search budget ran out after about 45 queries. Nothing below was read in full text.
> - "Cited Findings" are therefore taken from search-result extracts of the linked pages. Numbers are quoted as the extracts gave them; where an extract was from a secondary source, the bullet says so.
> - Several topics got no search coverage at all (rollback tooling other than snapper, APT phasing, needrestart, NixOS/bootc/MicroOS, etckeeper, incident-containment guidance, LinkedIn Nurse, Netflix, Renovate/uv settings). For these I give background knowledge from training (cutoff mid-2026) under "Inferences", explicitly marked **[BACKGROUND — not verified this session]**. Treat those as leads to confirm, not as citations.
> - Search extracts did not always say which of the returned pages a statement came from. Where that is the case the bullet is marked **(page attribution unconfirmed)** and links the most likely page(s); check the link before quoting.
> - Labels: **PROVEN** = measured or documented in a primary source; **PROMISING** = some measured support, limited or vendor-reported; **HYPE** = claimed without public measurement, or contradicted by measurement.

---

## 1. LLM code-fix quality, measured: how good are automated vulnerability patches really?

### Takeaway
The best published agent fixes about 73% of real C/C++ vulnerabilities on SEC-bench (mid-2026), but every study that checks harder than "the original PoC no longer crashes" finds a large share of patches that look fixed and are not: 31% of one system's failures compiled yet stayed exploitable, PoC-only validation inflates solve rates about 1.8x, and the AIxCC winner had only 31 of 42 "plausible" patches credited. LLM code fixes are a pull-request-only activity; no evidence supports auto-merging them.

### Cited Findings

**AgenticRepair — VERIFIED to exist, numbers match the claim (PROVEN as a benchmark result; pre-print, under review)**
- arXiv 2607.29422, "AgenticRepair: Multi-Faceted Program Context Engineering for Agentic Vulnerability Repair", Michael Fu, Qiyue Mei, Patanamon Thongtanunam, Kla Tantithamthavorn; submitted 31 Jul 2026; marked as under review at IEEE TSE. — [arXiv 2607.29422](https://arxiv.org/abs/2607.29422)
- Reports a 73% success rate on SEC-bench (220 of 300 instances), stated as 29% above the strongest baseline (the extract does not say whether relative or percentage points). — [arXiv 2607.29422](https://arxiv.org/abs/2607.29422)
- Failure analysis of the 80 failures: 53 (66.2%) "Improper Format"; 25 (31.2%) "Still Vulnerable" — the patch compiled but the vulnerability remained exploitable under sanitizer testing. The remaining 2 were not broken down in the extract. — [arXiv 2607.29422 (PDF)](https://arxiv.org/pdf/2607.29422)
- Failed patches are larger: successful patches edit a median of 32 lines in one file; failed submitted patches a median of 47.5 lines across two files. — [arXiv 2607.29422 (PDF)](https://arxiv.org/pdf/2607.29422)
- Success is judged by sanitizer checks only; a secondary summary notes patches "still require functional review beyond sanitizer success". — [arXiv 2607.29422 (HTML)](https://arxiv.org/html/2607.29422)

**SEC-bench (NeurIPS 2025) (PROVEN)**
- SEC-bench (Hwiwon Lee, Ziqi Zhang, Hanxiao Lu, Lingming Zhang) reports that the best code agents at publication (SWE-agent, OpenHands, Aider) reached at most 18.0% on PoC generation and 34.0% on vulnerability patching on the full dataset; building an instance costs $0.87. — [NeurIPS 2025 proceedings](https://proceedings.neurips.cc/paper_files/paper/2025/hash/a9168f1c54e5147027f1e8cf83e1a775-Abstract-Conference.html); [arXiv 2506.11791](https://arxiv.org/pdf/2506.11791)

**DARPA AIxCC finals (Aug 2025) (PROVEN for headline numbers; patch-correctness detail only partly public)**
- Final round: competitors' systems found 54 of 63 synthetic vulnerabilities (86%) and patched 43 (68%), up from 37% and 25% at semifinals. DARPA corrected the denominator from 70 to 63 after publication. — [DARPA, AIxCC results](https://www.darpa.mil/news/2025/aixcc-results)
- Conflict: sources using the old denominator still say 77% found / 61% patched (54/70 and 43/70), including a KAIST summary and DARPA's own main-stage slides. The 86% / 68% figures are the corrected ones. — [KAIST EE](https://ee.kaist.ac.kr/en/?p=202896); [Trail of Bits main-stage PDF](https://www.trailofbits.com/documents/AIxCC_Main_Stage_Presentation.pdf)
- How patches were validated: per the official scoring guide, all available functional tests are executed to confirm functionality is preserved; a patch scores 6 x a time multiplier only if it is rule-compliant, remediates the vulnerability and passes all functionality tests, otherwise 0. Patches may not pass by modifying the functional test source. — [AIxCC Final Procedures and Scoring Guide v2.0, June 2025](https://aicyberchallenge.com/storage/2025/06/AFC-Procedures-and-Scoring-Guide-Version-2_0-_20250606.pdf)
- Each challenge score was scaled by an accuracy multiplier, so wrong submissions cost points. — [FuzzingBrain paper, arXiv 2509.07225](https://arxiv.org/html/2509.07225v1)
- PoVs (proofs of vulnerability) are the foundation of scoring; PoV+patch bundles earn more than patches without a PoV; scores decay with time. — [Trail of Bits, 7 Aug 2025](https://blog.trailofbits.com/2025/08/07/aixcc-finals-tale-of-the-tape/)
- Winner's own patch attrition: Team Atlanta's ATLANTIS submitted plausible patches for 42 challenge vulnerabilities; organizers awarded scores to 31 of them after manual inspection and did not disclose the inspection detail. — [ATLANTIS paper, arXiv 2509.14589](https://arxiv.org/pdf/2509.14589) (page attribution unconfirmed)
- A finalist reported an internal patch success rate of about 90% at mitigating PoVs, yet placed 6th on patch points (14.22). — [whexy, "We lost the AIxCC"](https://www.whexy.com/en/posts/aixcc) (page attribution unconfirmed; single team blog)
- The SoK post-mortem (Cen Zhang and 22 co-authors, arXiv 2602.07666, presented at USENIX Security 2026) re-ran Claude Code v1.0.88 with Claude 3.7 Sonnet on the same 63 vulnerabilities and got semantically correct patches for 33 of 63 crashes (about 52%), as reported by Team Atlanta's blog. — [Team Atlanta blog](https://team-atlanta.github.io/blog/post-patch-2026-ensemble/); [arXiv 2602.07666](https://arxiv.org/abs/2602.07666)
- Georgia Tech's coverage of the USENIX talk says 38% to 46% of AI-generated patches were semantically incorrect; the extract does not make clear which experiment this refers to. — [Georgia Tech College of Computing](https://www.cc.gatech.edu/news/georgia-tech-researchers-share-ai-cyber-challenge-lessons-usenix-security-2026)
- The SoK attributes low patch scores partly to strict patch filtering (build, PoV reproduction, functional tests). — [arXiv 2602.07666 v1 HTML](https://arxiv.org/html/2602.07666v1)

**"Plausible but incorrect" patches — the central evidence (PROVEN)**
- PatchBench (arXiv 2609.04075, Sept 2026): across 11 state-of-the-art agents including the top three AIxCC agents, PoC-only validation inflates the patching solve rate by 1.83x on average. 25% of agent patches are substantially similar to historical developer patches (memorisation). Agents often patch at the crash stack trace to suppress the crash instead of fixing the root cause. 213 tasks, 32 projects, 16 CWEs. — [arXiv 2609.04075](https://arxiv.org/pdf/2609.04075)
- PatchBench pass rates per secondary sources (not checked against the paper's tables): about 59.2% (Codex), 58.2% (OpenHands) and 56.8% (Claude Code) pass all checks, versus roughly 97-98% under the original PoC check. A second blog disagrees on the third configuration (OpenHands + Gemini at 44.1%). — [secrss.com](https://www.secrss.com/articles/93818); [danielvaughan.com, 4 Sep 2026](https://codex.danielvaughan.com/2026/09/04/patchbench-vulnerability-patching-agents-memorization-codex-cli/)
- PoC+ study (arXiv 2603.06858, Mar 2026): across three state-of-the-art automated vulnerability repair systems, over 40% of patches validated as correct by basic tests fail under stronger PoC+ testing. — [arXiv 2603.06858](https://arxiv.org/abs/2603.06858v2)
- Vul4J study (arXiv 2603.10072, Mar 2026): of 319 Gemini-generated Java patches for 64 vulnerabilities, 79 (24.8%) were correct and secure; 33 (10.3%) were "pure security failures" that pass all functional tests while leaving the vulnerability. — [arXiv 2603.10072](https://arxiv.org/html/2603.10072v1)
- VulnRepairEval (arXiv 2509.03331, Sept 2025): exploit-based benchmark on 23 Python CVEs; argues passing unit tests or running without error does not show a vulnerability is gone; most failures come from imprecise vulnerability identification and syntactically or semantically broken patches. — [arXiv 2509.03331](https://arxiv.org/html/2509.03331)
- Single-attempt Java study (reported Dec 2025): models from OpenAI, Meta, DeepSeek and Mistral repaired some Vul4J bugs but often produced incorrect or incomplete patches. — [Help Net Security, 11 Dec 2025](https://www.helpnetsecurity.com/2025/12/11/llms-software-vulnerability-patching-study/)

**Fixes that introduce new problems (PROVEN, small samples)**
- 1Password Off-by-1 Labs (Aug 2026), two frontier models on six recent complex CVEs: only 26.0% of patches fixed the bug without changing application behaviour or adding a flaw; 49.3% failed to close at least one existing exploit path; about 2.3% fixed the issue while introducing a new security issue. Fix success was 65.0% with correct guidance, 50.4% with none and 15.2% with incorrect guidance. An iterative harness helped less than guidance correctness. The authors say the six CVEs were chosen for complexity and do not represent the average bug. — [1Password blog](https://1password.com/blog/why-ai-generated-patches-still-require-human-review); [Help Net Security, 6 Aug 2026](https://www.helpnetsecurity.com/2026/08/06/1password-ai-generated-vulnerability-patches/)
- Minor conflict: SANS and The Register quote 2.1% and 2.2% for neighbouring categories of the same study; The Register notes 1Password added a post-publication note acknowledging a critique. — [The Register, 6 Aug 2026](https://theregister.com/ai-and-ml/2026/08/06/ai-struggles-to-patch-vulns-without-adult-supervision/5284319)
- "Are AI-Generated Fixes Secure?" (arXiv 2507.02976, 2025): on SWE-bench, patches from Llama 3.3 introduced 8.7x more new vulnerabilities than the human-written fixes, with missing context a main driver. — [arXiv 2507.02976 (mirror summary)](https://fugumt.com/fugumt/paper_check/2507.02976v2_enmode)

**Vendor agents**
- Google DeepMind CodeMender (6 Oct 2025): validation uses static analysis, dynamic analysis, differential testing, fuzzing and SMT solvers, plus an LLM critique tool that compares original and modified code and an LLM judge for functional equivalence; only patches that pass are surfaced for human review. 72 security fixes upstreamed over about six months, including to a project of 4.5 million lines. — [DeepMind blog](https://deepmind.google/blog/introducing-codemender-an-ai-agent-for-code-security/) **PROMISING**: the 72 is an activity count; no accept/reject breakdown or accuracy figure has been published. — [ai-era summary](https://ai-era.pages.dev/papers/google-codemender-deepmind)
- OpenAI Aardvark (30 Oct 2025; renamed Codex Security and moved to research preview, noted 6 Mar 2026): identified about 92% of known and synthetic vulnerabilities in internal "golden" repositories; patches are proposed for one-click human review. — [OpenAI](https://openai.com/index/introducing-aardvark) **HYPE-leaning as a quality claim**: the benchmark repositories are undisclosed and no false-positive or patch-correctness rate is published. — [ai-era entity page](https://ai-era.pages.dev/entities/products/codex-security)
- GitHub Copilot Autofix (beta data May-July 2024): median 28 minutes to commit an Autofix for a PR-time alert versus 1.5 hours manually; SQL injection 18 minutes versus 3.7 hours. — [GitHub blog](https://github.blog/news-insights/product-news/secure-code-more-than-three-times-faster-with-copilot-autofix/) **PROVEN for speed, not for correctness**.
- A competitor (Pixee) states GitHub has not disclosed what share of Autofix suggestions developers accept. I found no GitHub-published acceptance rate. — [Pixee blog, 2026](https://www.pixee.ai/blog/best-automated-remediation-tools-2026)

### Inferences
- The gap between "PoC stops crashing" and "actually fixed" is consistent across four independent 2026 measurements: 1.83x inflation (PatchBench), >40% (PoC+), 31 of 42 credited (ATLANTIS at AIxCC, i.e. about 26% rejected) and 25 of 80 failures silently still vulnerable (AgenticRepair). A planning figure of "roughly one in four to one in two plausible LLM patches is wrong or incomplete" is defensible for hard bugs.
- All the high numbers (73%, 68%) are for C/C++ memory-safety bugs with sanitizers and fuzz harnesses, which give a crisp oracle. A solo developer's web app (auth logic, injection, SSRF, access control) has no sanitizer oracle, so real-world reliability there is likely lower and harder to measure. The Java and Python studies (24.8% correct-and-secure; 26% full fixes) point the same way.
- Patch size is a cheap risk signal: failed AgenticRepair patches were about 50% longer and touched two files. An agent can route large or multi-file patches to stricter review.
- Wrong diagnosis is worse than no diagnosis (15.2% vs 50.4% in the 1Password study). A fix agent should be fed the reproduced exploit and raw scanner evidence, not an upstream LLM's prose explanation of the bug.
- Label summary: "LLM agents can draft useful security patches" = PROVEN. "LLM patches can be merged without human review" = HYPE (contradicted by every correctness study above). "Layered automated validation closes the gap" = PROMISING (CodeMender design, AIxCC scoring), not yet quantified publicly.

### Gaps
- Could not read the AgenticRepair, SecRespond, PatchBench or SoK papers in full (arxiv.org blocked), so methodology details, the meaning of "29%", and the last 2 AgenticRepair failures are unconfirmed.
- No public per-patch correctness table for the AIxCC finals: how many submitted patches across all teams were rejected or penalised is not in any extract I saw. The accuracy-multiplier formula is described only in team papers and one blog.
- DARPA's other finals statistics that I recall from training (18 real non-synthetic vulnerabilities found, 11 real patches, about 45 minutes average time to patch, about $152 average cost per task) were not re-verified this session.
- No measured Copilot Autofix acceptance rate exists publicly, as far as I could find.
- No study found that measures LLM fix quality on a small personal web-app codebase.

---

## 2. A practical patch-verification protocol for a solo developer: what evidence supports each step?

### Takeaway
The nine-step protocol in the brief is well supported for steps 1-6 and 9 by competition rules and 2025-2026 studies; steps 7 (performance) and 8 (independent reviewer model) are sensible but had no measured evidence in what I found. The single most important finding is that step 3 (original PoC fails) is necessary and far from sufficient.

### Cited Findings
- Step 1 (reproduce first, as a failing test or PoC): AIxCC made the PoV the foundation of scoring and paid more for PoV+patch bundles than for bare patches. — [Trail of Bits, 7 Aug 2025](https://blog.trailofbits.com/2025/08/07/aixcc-finals-tale-of-the-tape/)
- Step 1 caveat: PoC generation is the harder half. Best agents reached 18.0% PoC generation versus 34.0% patching on SEC-bench in 2025. — [NeurIPS 2025 proceedings](https://proceedings.neurips.cc/paper_files/paper/2025/hash/a9168f1c54e5147027f1e8cf83e1a775-Abstract-Conference.html)
- Steps 2-3 (apply fix; PoC must fail) are the minimum bar used by exploit-based benchmarks. — [VulnRepairEval, arXiv 2509.03331](https://arxiv.org/html/2509.03331)
- Step 3 is insufficient alone: PoC-only checks inflate solve rates 1.83x; agents patch the crash site, and other inputs still reach the same bug by a different path. — [PatchBench, arXiv 2609.04075](https://arxiv.org/pdf/2609.04075)
- Step 4 (variant analysis): over 40% of "validated" patches fail when extra PoC variants are added. — [PoC+ study, arXiv 2603.06858](https://arxiv.org/abs/2603.06858v2)
- Step 4: 49.3% of LLM patches left at least one existing exploit path open. — [Help Net Security on 1Password study, 6 Aug 2026](https://www.helpnetsecurity.com/2026/08/06/1password-ai-generated-vulnerability-patches/)
- Step 5 (full test suite): AIxCC required all functionality tests to pass, with some tests withheld from the system, and forbade editing the tests. — [AIxCC Final Scoring Guide v2.0](https://aicyberchallenge.com/storage/2025/06/AFC-Procedures-and-Scoring-Guide-Version-2_0-_20250606.pdf); [AIxCC semifinal scoring guide v4](https://aicyberchallenge.com/wp-content/uploads/2024/06/ASC-Procedures-and-Scoring-Guide-v4.pdf)
- Step 5 is also insufficient alone: 10.3% of patches in one study passed every functional test while leaving the vulnerability. — [arXiv 2603.10072](https://arxiv.org/html/2603.10072v1)
- Step 6 (static-analysis delta): LLM patches introduced 8.7x more new vulnerabilities than human fixes on SWE-bench; about 2.3% of frontier-model patches fixed the target but added a new security issue. — [arXiv 2507.02976 (mirror summary)](https://fugumt.com/fugumt/paper_check/2507.02976v2_enmode); [Help Net Security, 6 Aug 2026](https://www.helpnetsecurity.com/2026/08/06/1password-ai-generated-vulnerability-patches/)
- Step 8 (independent reviewer): CodeMender uses a separate LLM critique tool and an LLM judge alongside fuzzing, differential testing and SMT, and the agent self-corrects when the judge flags a problem. — [DeepMind blog, 6 Oct 2025](https://deepmind.google/blog/introducing-codemender-an-ai-agent-for-code-security/)
- Step 8 caveat: guidance quality dominates outcomes (65.0% / 50.4% / 15.2%), so a reviewer anchored on a wrong description will also be wrong. — [1Password blog, Aug 2026](https://1password.com/blog/why-ai-generated-patches-still-require-human-review)
- Step 9 (staged deploy + rollback): CrowdStrike's own remediation after July 2024 was to add staged deployment for content updates and more customer control over rollout. — [TechTarget on CrowdStrike RCA](https://www.techtarget.com/searchSecurity/news/366602392/CrowdStrike-details-errors-that-led-to-mass-IT-outage)
- Step 9 trade-off, measured on a benchmark: in GuardedAct (arXiv 2609.11264, Sept 2026), raising the rollback-confidence threshold cut the harm rate from 12% to below 2% but recovery dropped from 94% to 65%. — [arXiv 2609.11264](https://arxiv.org/pdf/2609.11264)

### Inferences
- Proposed protocol with evidence grade:
  1. Reproduce as a failing test — PROVEN necessary. If the agent cannot reproduce, the fix goes to a human as "unverified", never auto-anything.
  2. Apply the fix on a branch, never on the running system.
  3. Original PoC must fail — PROVEN necessary, PROVEN insufficient.
  4. Variant analysis: mutate the PoC (encodings, boundary values, alternative entry points to the same sink), ask "where else is this sink reached?", and fuzz the touched function — PROVEN valuable (this is exactly what catches the 40-50% of false passes).
  5. Full test suite, with coverage on the touched lines; the agent must not be able to edit tests in the same PR without flagging it — PROVEN (AIxCC rule).
  6. Static-analysis delta: run Semgrep/CodeQL before and after; fail on any new finding — PROMISING (direct evidence of new-vulnerability introduction exists; evidence that scanners catch those specific regressions was not found).
  7. Performance/resource check — no evidence found; keep as a cheap sanity check (request latency and memory on the test suite before/after).
  8. Independent reviewer model with a different context (sees diff + PoC + tests, not the author's reasoning) — PROMISING, vendor-design evidence only.
  9. Canary + health checks + auto-rollback — PROVEN as industry practice; on one VM this means "new container beside old, switch the proxy, watch, switch back".
- "A fix counts only if the original attack no longer works and nothing else broke" should be tightened to: "the original attack AND its obvious variants no longer work, the test suite and scanners show no regression, and a human approved the diff". The brief's wording corresponds to step 3 + step 5, which the evidence shows passes a large share of wrong patches.
- **[BACKGROUND — not verified this session]** Cheap tools for differential/regression fuzzing on a personal budget: AFL++ and libFuzzer with ASan/UBSan for C/C++; `go test -fuzz` (built in); `cargo-fuzz` for Rust; Atheris for Python; Jazzer for JVM; property-based testing with Hypothesis (Python) or fast-check (JS) to compare old vs new function behaviour on random inputs; Schemathesis or RESTler for HTTP APIs from an OpenAPI spec; ClusterFuzzLite / CIFuzz to run short fuzz sessions in CI on each PR; AFLGo-style directed fuzzing to aim at the patched lines. For a web app, the realistic version is "differential test": replay a recorded request corpus against old and new builds and diff the responses.

### Gaps
- No measured evidence found for step 7 (performance regression checks catching bad security patches) or for how much a second-model reviewer improves patch correctness.
- No source found comparing the cost-effectiveness of regression-fuzzing tools; the tool list above is from background knowledge.
- The PoC+ and PatchBench methodologies (exactly how variants are generated) could not be read in full.

---

## 3. OS package patching: how safe is automated patching, and is "security pocket auto, everything else approved" the evidence-backed default?

### Takeaway
Auto-applying the distribution's security-pocket updates is the vendor default and the documented consensus, and I found no data showing it breaks systems often — only individual regressions. There is also no published regression-rate statistic, so the claim "security auto-updates are safe" rests on vendor policy plus absence of evidence, not on a measured rate; the big auto-update disasters (CrowdStrike 2024) involved unstaged vendor pushes to kernel-level code, which is a different risk class from distro security pockets.

### Cited Findings
- Canonical's stated position: the risk of applying security updates is lower than the risk of not applying them, which is why unattended-upgrades applies security updates by default on Ubuntu. — [Ubuntu Discourse thread](https://discourse.ubuntu.com/t/should-i-be-scared-of-unattended-upgrades-breaking-things/49832/) **PROVEN as vendor policy**
- Regressions do happen: an apache2 security update on Ubuntu caused a "421 Misdirected Request" regression (Launchpad bug #2117112, cited in the same thread, around 2025). — [Ubuntu Discourse thread](https://discourse.ubuntu.com/t/should-i-be-scared-of-unattended-upgrades-breaking-things/49832/)
- The updater itself can regress: USN-3156-1 (APT security fix, Dec 2016) introduced a regression in unattended-upgrades that could need manual repair; fixed by USN-3156-2. — [Ubuntu Security Notice USN-3156-2](https://ubuntu.com/security/notices/USN-3156-2)
- The updater can silently stop: on Ubuntu 25.10 (Oct 2025) a bug in the Rust coreutils replacement broke unattended upgrades; users had to run `apt update` manually. — [Phoronix](https://www.phoronix.com/news/Ubuntu-25.10-Broken-Upgrade)
- Common mitigations cited by practitioners: keep `Automatic-Reboot` off until a maintenance window; test on a staging host first. — [Ubuntu Discourse thread](https://discourse.ubuntu.com/t/should-i-be-scared-of-unattended-upgrades-breaking-things/49832/)
- CrowdStrike, 19 July 2024: a new Channel File 291 introduced a non-wildcard match on a 21st input parameter, causing an out-of-bounds read in the kernel sensor; a logic error in the content validator let it through. More than 8 million Windows systems entered reboot loops. — [CrowdStrike RCA executive summary](https://crowdstrike.com/wp-content/uploads/2024/08/Executive-Summary_Root-Cause-Analysis_Channel-File-291.pdf); [TechTarget](https://www.techtarget.com/cybersecurity/news/366596579/CrowdStrike-Content-validation-bug-led-to-global-outage)
- CrowdStrike's fix: staged deployment for rapid-response content and customer control over its rollout. — [TechTarget](https://www.techtarget.com/searchSecurity/news/366602392/CrowdStrike-details-errors-that-led-to-mass-IT-outage)
- Kernel live patching on a personal budget: Canonical offers Ubuntu Pro free for personal use on up to five machines, and it includes Livepatch (kernel fixes applied without reboot); enabled with `pro attach <token>` then `pro enable livepatch`. — [Canonical, Ubuntu Pro announcement (Oct 2022)](https://ubuntu.com/blog/ubuntu-pro-beta-release); [Ubuntu Livepatch tutorial](https://ubuntu.com/tutorials/enable-the-livepatch-service)
- Conflict: one 2026 article mentions a standalone Livepatch token limited to three machines, versus five under Ubuntu Pro personal. Current terms should be checked at ubuntu.com/pro. — [oneuptime, 2 Mar 2026](https://oneuptime.com/blog/post/2026-03-02-how-to-enable-kernel-livepatch-on-ubuntu/view)

### Inferences
- "Security pocket auto-apply; everything else needs approval" is the evidence-backed default in the sense that it is what the vendor ships and defends, and the documented failures are isolated and recoverable. It is PROVEN as policy and practice, not as a measured failure rate.
- The CrowdStrike lesson applies by analogy: the dangerous combination is (kernel-level code) x (pushed to everything at once) x (no rollback path when the machine cannot boot). For one VM that translates to: snapshot before kernel/bootloader/libc/systemd/openssh updates, do not auto-reboot blindly, and have an out-of-band console.
- Because the updater can fail silently (Ubuntu 25.10 case), the agent's most valuable patching job may be verification: "did unattended-upgrades actually run, is anything pending, is a reboot required, are services still running old libraries?" That is Tier-0 (read-only) work.
- **[BACKGROUND — not verified this session]**
  - Ubuntu's default `Allowed-Origins` for unattended-upgrades cover `-security` (and ESM) only; `-updates` is commented out. Debian's default covers Debian-Security. Useful knobs: `Package-Blacklist`, `Automatic-Reboot` / `Automatic-Reboot-Time`, `MinimalSteps`, `Mail`, and `--dry-run`.
  - APT phased updates on Ubuntu apply to the `-updates` pocket (stable release updates roll out to a growing percentage of machines); security-pocket updates are not phased. So the security pocket has no built-in canary other than the distro's own pre-release testing.
  - `needrestart` decides which services to restart after library updates; Ubuntu 24.04 restarts most services automatically in non-interactive runs. needrestart itself had local privilege escalation bugs disclosed by Qualys in Nov 2024 (CVE-2024-48990 and related), a reminder that patch helpers are attack surface.
  - `dnf-automatic` (RHEL/Fedora family) supports `upgrade_type = security` and `apply_updates = yes`; it depends on the repo shipping security metadata. `dnf history undo` gives transaction-level rollback when old packages are still available.
  - Live patching alternatives: kpatch (RHEL, with subscription), TuxCare KernelCare (paid, per-server), SUSE kernel live patching. Live patches cover selected high/critical CVEs, not everything; periodic reboots are still needed.
  - Other relevant incidents: Debian 12.3 was pulled in Dec 2023 over an ext4 corruption bug in a stable kernel update; a CrowdStrike Falcon update caused kernel panics on some Debian and Rocky hosts in spring 2024; the xz backdoor (CVE-2024-3094, Mar 2024) reached only unstable/testing/rawhide channels, never stable security pockets — an argument that stable pockets act as a natural cooldown.

### Gaps
- No statistic found on how often Debian or Ubuntu security updates cause regressions (e.g. share of USNs/DSAs followed by a "-2 regression" notice). This would be countable from the USN/DSA archives but I could not do it this session.
- No search coverage of dnf-automatic track record, APT phasing documentation, needrestart behaviour, kpatch or TuxCare pricing; all are background knowledge above.
- No 2025-2026 Linux-specific "auto-update took down fleets" incident on the CrowdStrike scale was found; the search for other auto-update outages was cut off by the budget.
- Microsoft's 8.5 million device estimate for CrowdStrike was not re-verified; the extract I saw says "more than 8 million".

---

## 4. Rollback mechanisms for a single VM: what works in practice, and what cannot be rolled back?

### Takeaway
For a solo operator on a stock Debian/Ubuntu VM, the realistic rollback stack is: provider snapshot before risky OS changes, git for /etc and app code, pinned image digests for containers, and tested database backups — because filesystem-snapshot rollback on Debian/Ubuntu (snapper + grub-btrfs) has documented rough edges and package downgrade is not a real rollback mechanism. Only a small set of things (data migrations, rotated secrets, deleted data, anything sent outside the box) cannot be rolled back, and those define the "never auto" tier.

### Cited Findings
- grub-btrfs scans for read-only btrfs snapshots and adds them as bootable GRUB entries; it is installable from apt on Ubuntu. — [oneuptime guide, 2 Mar 2026](https://oneuptime.com/blog/post/2026-03-02-set-up-boot-time-snapshot-integration-ubuntu/view) (secondary tutorial; page attribution unconfirmed)
- On Debian/Ubuntu, one guide says apt has no first-class snapper plugin and pre/post snapshots are wired up with an apt hook file (`/etc/apt/apt.conf.d/80snapper`). — [oneuptime guide, 2 Mar 2026](https://oneuptime.com/blog/post/2026-03-02-how-to-use-snapper-for-btrfs-snapshots-on-ubuntu/view) (secondary tutorial; page attribution unconfirmed)
- Documented failure: after `snapper rollback` on Ubuntu the default subvolume is set but the system does not boot into the snapshot (Launchpad bug 1734496, 2017-era; fix status not confirmed). — [Launchpad bug 1734496](https://bugs.launchpad.net/bugs/1734496)
- Documented failure: Debian bug 932127, GRUB fails to load a snapshot after `snapper rollback`. — [Debian pkg-grub-devel, July 2019](https://lists.alioth.debian.org/pipermail/pkg-grub-devel/2019-July/016711.html)
- A 2025 siduction talk states GRUB and systemd-boot both fail to create correct default boot entries after a rollback. — [LIT Augsburg 2025 slides (German)](https://luga.de/static/LIT-2025/assets/talks/Siduction-auf-Btrfs-mit-Snapper_LIT-Augsburg-2025.pdf)
- Community workaround: boot the snapshot from the GRUB menu, then make it permanent by swapping subvolumes manually. — [snapper-in-debian-guide (GitHub)](https://github.com/david-cortes/snapper-in-debian-guide) (page attribution unconfirmed)
- Hardening changes are not self-reverting: Red Hat states OpenSCAP remediation cannot be automatically reverted because identifying exactly what the remediation changed is "challenging and unreliable". — [Red Hat KB 7032665](https://access.redhat.com/node/7032665)
- Rollback paths must work when the machine cannot help: CrowdStrike recovery required hands-on fixes on hosts stuck in boot loops. — [CrowdStrike remediation hub](https://www.crowdstrike.com/falcon-content-update-remediation-and-guidance-hub/)

### Inferences
- btrfs + snapper + grub-btrfs is PROVEN on openSUSE (where it is the default design) but only PROMISING on Debian/Ubuntu: it works, yet the documented boot-after-rollback bugs mean a solo operator must rehearse it before trusting it. A provider snapshot is the lower-skill option.
- **[BACKGROUND — not verified this session]** Comparison for one VM:

| Mechanism | What it rolls back | Realistic for solo operator? | Main catch |
|---|---|---|---|
| Provider/hypervisor snapshot | Whole disk | Yes — simplest; cents per GB-month at most providers | Crash-consistent unless filesystem is frozen; restoring discards ALL data written since (DB rows, uploads); restore takes minutes and usually a reboot. Keep data on a separate volume |
| btrfs + snapper (+ grub-btrfs) | Root filesystem, per transaction | Yes with rehearsal | Layout must be set at install (@, @home, separate data subvolumes); /boot on another filesystem breaks kernel rollback; see bugs above |
| ZFS boot environments (ZFSBootMenu, zectl) | Root dataset | For enthusiasts | Not a default install path on Ubuntu any more (zsys abandoned) |
| LVM thin snapshot | Block device | Yes on RHEL-family (boom/snapm) | Merging a root snapshot needs a reboot; thick snapshots fill up and invalidate |
| apt/dpkg downgrade | One package | No, emergency only | Debian does not support downgrades; maintainer scripts are not written for it; old version may be gone from the security pocket (snapshot.debian.org needed). `apt-mark hold` is the practical tool after a bad update |
| NixOS generations | Entire system config + packages | Yes if willing to adopt NixOS | Atomic, boot-menu selectable, `nixos-rebuild switch --rollback`; does not roll back /var state |
| Fedora CoreOS / bootc / rpm-ostree | OS image (A/B) | Yes for container-host VMs | `rpm-ostree rollback` / `bootc rollback`; greenboot can auto-rollback on failed health check; /etc is merged, /var is kept |
| openSUSE MicroOS transactional-update | OS snapshot activated on reboot | Yes | health-checker auto-rolls back on failed boot |
| Ubuntu Core | Snap revisions | Niche (IoT) | Automatic revert of failed snap refresh |
| etckeeper | /etc as git history | Yes — install it | Commits around apt runs; it records, it does not restart services; secrets in /etc land in the repo, so do not push it anywhere unencrypted |
| Config management (Ansible/pyinfra) + git revert | Declared state | Partly | Convergent, not transactional: reverting the playbook does not undo anything the old playbook did unless the inverse state is declared |
| Container tag/digest rollback | App runtime | Yes — the best app-level rollback | Pin by digest, keep previous image; volumes and DB schema are not rolled back |
| DB migration reversal | Schema/data | The hard part | Down-migrations are rarely tested; destructive ones need a backup restore (PITR via pgBackRest/WAL-G). Use expand/contract so old code still runs on new schema |
| Blue/green or canary on one box | App release | Yes | Two containers behind Caddy/Traefik/nginx; switch upstream after health check; shares one DB, so schema must be backward compatible |

- Cannot be rolled back (one-way doors): dropped/overwritten data and destructive migrations without a backup; rotated or revoked secrets (old value is dead, dependents break); deleted logs, backups or snapshots; emails, webhooks, payments and any message already sent; published packages or pushed public commits; data already exfiltrated. Also effectively one-way: release upgrades (`do-release-upgrade`), disk/partition/encryption changes, and killing a process when its memory was the forensic evidence.
- A snapshot is only a rollback if restore has been tested. The agent should run a periodic restore drill (restore snapshot to a scratch VM, boot, health-check) and report the measured time; this is cheap on hourly-billed providers.
- Snapshot rollback and "data written since" conflict on any stateful VM. The practical design is OS disk (snapshot freely, restore freely) + data volume (backed up, never rolled back by the agent).

### Gaps
- No search coverage for NixOS, bootc/rpm-ostree, MicroOS, Ubuntu Core, ZFS boot environments, LVM, etckeeper, apt downgrade policy or provider snapshot pricing — the table is background knowledge and should be confirmed against official docs.
- No current confirmation of whether Launchpad bug 1734496 / Debian bug 932127 are fixed in Ubuntu 24.04/26.04 or Debian 13.
- No measured data on snapshot restore times or consistency failures for small VMs.

---

## 5. Config hardening automation: tools, lockout cases, and guard patterns

### Takeaway
Benchmark-driven auto-remediation (OpenSCAP/ComplianceAsCode, CIS roles) is the one fix class where the vendor itself says changes cannot be automatically undone, and SSH/PAM/firewall rules are the known lockout source. Hardening should run audit-only by default, with remediation applied rule-by-rule under human approval and a timed auto-revert for anything touching remote access.

### Cited Findings
- Red Hat: OpenSCAP remediation runs mainly as bash scripts (Ansible playbooks are also shipped in scap-security-guide), and it cannot be automatically reverted once applied. — [Red Hat KB 7032665](https://access.redhat.com/node/7032665) **PROVEN**
- Lockout risk is called out in hardening guides: misconfiguring `sshd_config` (PermitRootLogin, PasswordAuthentication) can lock administrators out; test SSH changes from a second session; test in staging first; kernel parameter changes can break application networking. — [CIS hardening skill guide](https://openskillindex.com/skills/plurigrid-asi-hardening-linux-endpoint-with-cis-benchmark); [oneuptime, 4 Mar 2026](https://oneuptime.com/blog/post/2026-03-04-remediate-cis-benchmark-failures-ansible-rhel-9/view) (both secondary how-to guides; page attribution unconfirmed)
- Scanner and benchmark disagree with valid configs: the SSG check for "PermitRootLogin disabled" fails on `PermitRootLogin without-password` because the OVAL check looks for the literal `no`; SSG profiles lag the CIS benchmark by one to two quarters. — [linuxjunkies guide](https://linuxjunkies.org/guides/apply-cis-benchmark-with-openscap); [stackharbor knowledge base](https://stackharbor.com/en/knowledge-base/cis-benchmark-application/) (secondary; page attribution unconfirmed)
- Timed auto-revert exists as a built-in for network config: `netplan try` applies a config and rolls back unless confirmed within 120 seconds by default (`--timeout` to change); the docs warn of known bugs and tell the user to verify the revert actually happened after a timeout. — [Netplan docs](https://netplan.readthedocs.io/en/latest/netplan-try/) **PROVEN**

### Inferences
- A scanner "fail" is not automatically a defect (the PermitRootLogin example). An agent that auto-remediates to make the score green will overwrite deliberate choices; findings need a per-rule allow/waive list owned by the human.
- Blanket "apply the CIS profile" is a Tier-3 (human-run, on a snapshot, in a test clone first) action. Individual low-risk rules (file permissions on /etc/shadow, sysctl flags with no app impact, disabling unused services) can be Tier-1/2.
- **[BACKGROUND — not verified this session]**
  - Tools: Lynis and docker-bench-security are audit-only (safe to automate fully). ssh-audit audits and suggests config. OpenSCAP with ComplianceAsCode content can generate bash or Ansible fixes (`oscap xccdf generate fix`), which is better than `--remediate` because the fix can be reviewed as a diff. Ubuntu Security Guide (USG) offers CIS audit/fix under Ubuntu Pro. ansible-lockdown roles carry an explicit caution that they change the system with possible unintended consequences, are remediation not audit tools, and were developed against clean installs. dev-sec `ssh_hardening` disables password and root login by default, which locks out anyone without a working key.
  - Guard patterns: validate before reload (`sshd -t`, `visudo -c`, `nft -c -f`, `nginx -t`); keep the current SSH session open and prove a second login works before closing; `iptables-apply` (applies rules and reverts unless confirmed within a timeout); firewalld runtime-vs-permanent split and `--timeout`; a dead-man switch via `at now + 5 minutes` or `systemd-run --on-active=5m` that restores the previous file and reloads unless cancelled; the pattern originates in network gear ("commit confirmed"). NixOS and transactional OSes give the same effect at whole-system level.
  - Out-of-band access (provider web console / rescue mode) is the precondition for automating anything in SSH, PAM, sudoers, firewall or network config. The agent should verify console access works before the first such change, and should never alter the mechanism it would need to undo its own change.

### Gaps
- Could not retrieve the ansible-lockdown or dev-sec README text to cite the caution wording directly.
- No primary incident write-ups found of automated CIS remediation locking out admins (only guide-level warnings).
- `iptables-apply` and the at-job dead-man pattern returned no search results; they are background knowledge.

---

## 6. PR vs direct apply: an evidence-based decision rule, and dependency auto-merge risk

### Takeaway
Apply directly only when the change was authored and tested by a trusted upstream, is mechanically reversible, and can be health-checked without judgement (distro security updates, TTL'd blocks); open a PR for anything an LLM wrote or anything that changes code, lockfiles or infrastructure definitions. For dependency bumps, the 2025-2026 evidence turned decisively against fast auto-merge: cooldowns of 3-14 days became ecosystem defaults after Shai-Hulud.

### Cited Findings
- Woodruff's analysis (Nov 2025): of ten prominent supply-chain attacks, eight had windows of opportunity under a week, so a 7-day cooldown would have blocked most; a 14-day cooldown would have prevented all but one. — [Simon Willison on Woodruff's post, 21 Nov 2025](https://simonwillison.net/2025/Nov/21/dependency-cooldowns); [Socket glossary](https://socket.dev/glossary/dependency-cooldown); [InfoQ, May 2026](https://infoq.com/news/2026/05/pip-261-dependency-cooldowns) **PROVEN on a small sample (n=10)**
- Shai-Hulud: first self-replicating npm worm wave in mid-September 2025 (one source dates it 16 Sept); second wave ("The Second Coming") 21-24 Nov 2025 compromised hundreds of packages within hours — estimates run from 600-800 to over 1,000 packages and 25,000-27,000+ GitHub repositories — and executed in the pre-install phase. If an npm token was present it republished trojanised versions of up to 20 of the maintainer's other packages. — [The Register, 24 Nov 2025](https://www.theregister.com/2025/11/24/shai_hulud_npm_worm/); [Kroll](https://www.kroll.com/en/publications/cyber/shai-hulud-returns-with-mass-credential-theft); [Invicti](https://www.invicti.com/blog/web-security/shai-hulud-2-worm-supply-chain-attack-on-npm-dependencies) (figures vary by source and were still moving; which page carries each figure is unconfirmed)
- Ecosystem response (state as of Oct 2026): pnpm 11 enables a 1-day minimum release age by default and blocks exotic sub-dependencies; Yarn 4.15 has a default cooldown; npm shipped `min-release-age` in 11.10.0 (Feb 2026) but npm 12 has no default; Bun added `minimumReleaseAge` in 1.3 (Oct 2025); Deno has `--minimum-dependency-age`. — [Socket glossary](https://socket.dev/glossary/dependency-cooldown); [Socket blog](https://socket.dev/blog/npm-introduces-minimumreleaseage-and-bulk-oidc-configuration); [hidekazu-konishi.com comparison](https://hidekazu-konishi.com/entry/dependency_cooldowns_by_package_manager.html) (which of these pages carries each item is unconfirmed)
- pip 26.1 shipped cooldowns, citing Woodruff; RubyGems/Bundler added them in mid-2026. — [InfoQ, May 2026](https://infoq.com/news/2026/05/pip-261-dependency-cooldowns); [Risky Bulletin](https://news.risky.biz/risky-bulletin-rubygems-adds-dependency-cooldowns-to-counter-supply-chain-attacks/)
- Dependabot added a default three-day cooldown for version updates (reported July 2026). — [InfoQ, July 2026](https://infoq.com/news/2026/07/github-dependabot-cooldown)
- Limits of cooldowns: "a cooldown is a clock, not a detector"; they only address fast-detected attacks and should be one layer among several. — [Arrange Act Assert](https://arrangeactassert.com/posts/minimum-release-age-is-necessary-but-not-enough/); [InfoQ, July 2026](https://infoq.com/news/2026/07/github-dependabot-cooldown)
- Detection can be fast: in the TanStack compromise, Socket flagged all 84 malicious artifacts within six minutes of publication. — [Socket glossary](https://socket.dev/glossary/dependency-cooldown)
- Criticism: cooldowns free-ride on other users' detection; the better fix is an upload queue at the registry. Woodruff also argues vendors overhype the threat. — [Cal Paterson](https://calpaterson.com/deps.html); [LWN](https://lwn.net/Articles/1068692/)
- On the code side, no vendor agent auto-merges: CodeMender surfaces only validated patches "for human review"; Aardvark/Codex Security uses one-click human review. — [DeepMind blog](https://deepmind.google/blog/introducing-codemender-an-ai-agent-for-code-security/); [OpenAI](https://openai.com/index/introducing-aardvark)

### Inferences
- Decision rule (synthesis):
  - **Direct apply** if ALL hold: (a) authored and tested by a trusted upstream, not by the agent; (b) rollback mechanism exists and was rehearsed; (c) success is checkable by an automatic health check; (d) blast radius is this VM only; (e) no data or secret is destroyed. Examples: distro security-pocket updates, restarting a service, a TTL'd IP block.
  - **PR (human merges)** if ANY hold: the diff is LLM-authored; it changes application logic, lockfiles, CI, Dockerfiles or IaC; correctness needs semantic judgement; or the verification protocol in section 2 could not be completed.
  - **Human executes** if the action is a one-way door (section 4 list).
- Fast auto-merge of dependency bumps is itself a supply-chain risk: PROVEN by the Shai-Hulud timeline (malicious versions live for hours) and the 8-of-10 statistic. Recommended setting for a solo developer: 7-day minimum release age at both the bot (Renovate/Dependabot) and the package manager; auto-merge only patch-level bumps after cooldown AND green tests; lockfile + `--ignore-scripts`/frozen installs in CI.
- Tension to state plainly: a cooldown delays genuine security fixes too. The usual resolution is to let advisories with a known CVE bypass the cooldown as a PR for human review, not as an auto-merge. The agent's verification step ("is the vulnerable function even reachable in my code?") decides urgency.
- Distro security pockets already behave like a cooldown plus vendor review, which is why direct-apply is acceptable there and not for language-ecosystem registries where anyone can publish instantly.
- **[BACKGROUND — not verified this session]** Renovate's setting is `minimumReleaseAge` (formerly `stabilityDays`), with presets for npm; uv supports `exclude-newer` (including relative durations); Dependabot's option is `cooldown` with per-semver-level days. Exact names and defaults should be checked in current docs.

### Gaps
- Renovate, Dependabot and uv documentation could not be retrieved; whether Dependabot's default cooldown exempts security updates is unconfirmed.
- No measured data found on how often auto-merged dependency PRs break builds or introduce malware in small projects.
- Details of 2026 Shai-Hulud-style waves (beyond the Nov 2025 second wave and a passing TanStack mention) were not retrieved.

---

## 7. Lessons from SRE auto-remediation and self-healing systems

### Takeaway
Two decades of production auto-remediation show the same pattern: automation fixes the common case well (Meta's FBAR handled most routine host failures) and causes the worst outages when it acts on a wrong or empty input at full speed with no rate limit (Google Diskerase, AWS DynamoDB DNS in Oct 2025). LLM agents doing SRE remediation are improving fast but still fail a quarter to most of the time on benchmarks, so the classic safeguards — rate limits, blast-radius caps, idempotency, dry-run, circuit breakers — matter more, not less.

### Cited Findings
- Meta FBAR ("Facebook Auto-Remediation"): a daemon whose alert-fetch loop polls monitoring and runs remediation plugins in precedence order through an API exposing host data, power control and command execution; by the 2011 post it managed more than 50% of Facebook's infrastructure, with humans needed only for physical repairs. — [Engineering at Meta, 15 Sep 2011](https://engineering.fb.com/2011/09/15/data-center-engineering/making-facebook-self-healing/) **PROVEN at scale (self-reported)**
- FBAR's 2016 rack-maintenance extension states that neither serial nor parallel execution was safe enough: serial could drain a service's capacity one server at a time, parallel was prone to races — so aggregate, capacity-aware handlers were added. FBAR re-runs the machine checker afterwards to verify the failure is gone. — [Engineering at Meta, 11 Jul 2016](https://engineering.fb.com/2016/07/11/production-engineering/making-facebook-self-healing-automating-proactive-rack-maintenance/)
- Google SRE book, chapter 7 ("The Evolution of Automation at Google"), includes the Diskerase incident; a third-party study summary says the incident showed the need for sanity checks and rate limiting, and the chapter stresses idempotency and the cost of automation failure at scale. — [Google SRE book ch. 7](https://sre.google/sre-book/automation-at-google/); [third-party summary](https://docs-bzt.pages.dev/SRE/SiteReliabilityEngineering/part2-principals/07.TheEvolutionOfAutomationAtGoogle) (summary not checked against the chapter text this session)
- AWS, 19-20 Oct 2025: a race condition between DynamoDB's DNS Planner and DNS Enactor automation left an empty DNS record for the regional endpoint that the automation could not repair; AWS disabled that automation worldwide until safeguards were added. — [InfoQ, Nov 2025](https://www.infoq.com/news/2025/11/aws-dynamodb-outage-postmortem); [The Register, 23 Oct 2025](https://www.theregister.com/2025/10/23/amazon_outage_postmortem/) **PROVEN: automation as root cause**
- LLM agents for SRE, measured:
  - ITBench (IBM, Feb 2025; ICML 2025): agents on state-of-the-art models resolved 13.8% of SRE scenarios, 25.2% of CISO (compliance) scenarios and 0% of FinOps scenarios. — [arXiv 2502.05352](https://arxiv.org/abs/2502.05352v1)
  - SREGym (arXiv 2605.07161, 2026; 90 realistic problems): end-to-end success (diagnosis and mitigation both right in the same run) ranged from 38.9% to 72.6% across agent-model pairs, with Claude Code highest. — [SREGym summary](https://chatpaper.com/paper/277448); [related-papers page naming arXiv 2605.07161](https://arxiv.deeppaper.ai/papers/2605.07161v1/similar)
  - AIOpsLab (Microsoft, Jan 2025) is a framework that deploys microservice environments, injects faults and evaluates agents; no resolution rate was in the extract. — [Microsoft Research](https://www.microsoft.com/en-us/research/publication/aiopslab-a-holistic-framework-for-evaluating-ai-agents-for-enabling-autonomous-cloud)
  - GuardedAct (arXiv 2609.11264, Sept 2026): a stricter rollback-confidence threshold reduced harmful remediations from 12% to under 2% while successful recovery fell from 94% to 65%. — [arXiv 2609.11264](https://arxiv.org/pdf/2609.11264) **PROMISING, benchmark only**

### Inferences
- Design rules that transfer directly to a one-VM security agent:
  1. **Empty or surprising input means stop.** Diskerase and the AWS DNS race were both "automation acted on a degenerate plan". Guard: refuse any action whose target set is empty, "all", or larger than N.
  2. **Rate-limit and cap blast radius.** One remediation at a time; at most K auto-actions per day; never restart every service in one pass.
  3. **Circuit breaker for loops.** If the same fix is applied twice and the alert recurs, stop and page the human (systemd's start-limit and Kubernetes' CrashLoopBackOff are the built-in versions of this idea).
  4. **Idempotent, declarative actions** so a retry is harmless.
  5. **Dry-run first, and log the plan before the act.**
  6. **Verify after acting** (FBAR re-runs the checker); "fixed" is a measured state, not an assumption.
  7. **Do not depend on the thing you are changing.** Facebook 2021: the repair tools needed the network that was down. For one VM: the rollback path (console, snapshot API) must not run through the SSH/firewall config being modified.
  8. **Kill switch.** AWS's remedy was to turn the automation off globally; the solo operator needs a single file or flag that halts the agent.
- The harm/recovery trade-off in GuardedAct is the quantitative argument for tiering: aggressive autonomy recovers more but breaks more. On a personal VM where downtime is cheap and data loss is not, the conservative threshold is the right default.
- "Agents can autonomously run remediation in production" is PROMISING on 2026 benchmarks (up to 72.6% end-to-end) and HYPE as an unsupervised production claim: a 27-61% failure rate on realistic problems is not safe without gates.
- **[Seen in a search extract, but the extract did not identify the source page — treat as unverified]** Cloudflare, 18 Nov 2025: a database permission change produced an oversized feature file that propagated network-wide and broke the proxy. Facebook, Oct 2021: a BGP withdrawal from an audit/maintenance command removed the DNS servers that the repair tooling depended on.
- **[BACKGROUND — not verified this session]** The SRE book describes Diskerase as turndown automation that interpreted an empty machine list as "all machines" and queued a large part of a CDN for disk erase; it also proposes an automation hierarchy ending in systems that need no automation. Google Cloud's 12 June 2025 global outage was a policy change replicated globally within seconds, triggering a crash loop in Service Control with no feature flag and no backoff. LinkedIn's Nurse and Netflix's Winston (built on StackStorm) are published event-driven remediation platforms. AWS Systems Manager Automation supports approval steps and concurrency/error-rate limits; Rundeck/PagerDuty Runbook Automation and StackStorm provide the same workflow-with-approval shape and are heavier than a solo operator needs.

### Gaps
- Could not read the Google SRE chapter directly; the Diskerase specifics rest on a third-party summary plus background knowledge.
- No sources retrieved for LinkedIn Nurse, Netflix, Kubernetes operator failure modes, StackStorm/Rundeck, or AWS SSM Automation.
- The phrase "automation must be safer than the human doing it" could not be traced to a source.
- Cloudflare Nov 2025, Facebook 2021 and Google Cloud June 2025 need primary post-mortems; only unattributed search-extract mentions (or none) were retrieved, so they are not listed as cited findings.
- SREGym's publication date and per-model table were not confirmed.

---

## 8. Incident containment actions on a single VM: reversibility and what is safe to automate

### Takeaway
SecRespond is a real paper and confirms agents are weak at exactly the remediation half of incident response — no model fully detected and remediated any of 10 compromised hosts — but I could not confirm the specific "skips credential rotation and post-cleanup verification" wording. Containment actions that are reversible and time-limited (temporary IP block, pause a container, stop a service) are reasonable to automate; evidence-destroying or dependency-breaking ones (kill, delete, rotate, revoke) should be prepared by the agent and approved by the human.

### Cited Findings
- SecRespond — VERIFIED to exist: arXiv 2607.26791, "SecRespond: Benchmarking AI Agents for Real-World Post-Compromise Incident Response", Lehan Wang and nine co-authors (Alibaba-NLP), posted 29 Jul 2026. — [arXiv 2607.26791](https://arxiv.org/abs/2607.26791)
- Design: 10 cyber ranges on fully instantiated cloud hosts, 4 entry-point types, 21 ATT&CK techniques, 5 operating systems; 23 frontier LLMs run on the OpenCode harness; 280 expert checkpoints on detection and planning axes. — [alphaXiv listing](https://www.alphaxiv.org/abs/2607.26791); [arXiv 2607.26791 (HTML)](https://arxiv.org/html/2607.26791)
- Findings: agents reliably uncover problems that alerts expose, but struggle to proactively investigate the disk for silent intrusions and to produce comprehensive, verified remediation plans; no model achieved complete detection and remediation on any single range. — [arXiv 2607.26791](https://arxiv.org/abs/2607.26791) **PROVEN as benchmark result**
- Secondary coverage adds that following a structured routine made agents less likely to forget critical remediation steps, and that a good plan cleans the machine without destroying evidence or leaving backdoors. — [toknow.ai summary](https://toknow.ai/posts/secrespond-post-compromise-incident-response-benchmark/); [notatechguy summary](https://www.notatechguy.com/23-ai-agents-tested-on-breach-response-zero-passed/)
- The specific claim that agents skip credential rotation and post-cleanup verification: **could not verify**. No extract mentions credential rotation; "verified remediation plans" being a weak point is consistent with it but is not the same statement. — [arXiv 2607.26791](https://arxiv.org/abs/2607.26791)
- Related benchmark: SIR-Bench (arXiv 2604.12040, 2026) evaluates investigation depth of incident-response agents; no figures retrieved. — [arXiv 2604.12040](https://arxiv.org/pdf/2604.12040)
- Vendor guidance on rotation: rotation can look clean while the same access persists through a secondary token, integration or copied secret; verify after remediation. — [NHI Mgmt Group FAQ](https://nhimg.org/faq/what-do-security-teams-get-wrong-about-rotating-credentials-after-an-ai-related/) (vendor/community source)

### Inferences
- SecRespond's result (alert-driven findings fine, silent persistence missed) means an agent's "host is clean" verdict is not trustworthy. After a real compromise, the evidence-backed remediation for a single VM is still rebuild from a known-good image and restore data, with the agent assisting — not agent-led in-place cleanup.
- The finding that a structured routine reduces forgotten steps supports giving the agent a fixed containment checklist (with rotation and re-verification as explicit, non-skippable items) instead of free-form response.
- **[BACKGROUND / reasoning — not verified this session]** Reversibility table:

| Action | Reversible? | Automate? | Notes |
|---|---|---|---|
| Snapshot disk for forensics | Non-destructive | Yes, do it FIRST | Costs storage; captures disk not memory |
| Block source IP | Yes | Yes, with TTL and admin allowlist | Risk: blocking yourself, a CDN or shared NAT. fail2ban / CrowdSec already do this with expiry |
| Pause/freeze container or process (`docker pause`, SIGSTOP, cgroup freeze) | Yes | Yes | Preserves memory for forensics; preferable to kill |
| Disconnect container from network | Yes | Yes | |
| Stop a service | Yes | Yes for non-critical; approval if it is the main app | Availability cost only |
| Network quarantine via provider firewall (allow admin IP only) | Yes | With approval, or auto only on high-confidence compromise | Must be set outside the VM so the attacker cannot undo it, and so the admin keeps console access |
| Kill process | Process state is lost | Approval (auto only if already snapshotted and clearly malicious) | Destroys volatile evidence; attacker persistence may respawn it |
| Lock user account | Yes | Approval | `passwd -l` does not stop SSH-key logins; expire the account and kill sessions as well |
| Remove an authorized key / revoke a session | Yes if backed up | Approval | Never the admin's last key |
| Revoke API token / rotate credentials | No | Never automatic; agent prepares the runbook | One-way; breaks dependents; must be ordered issue-new -> deploy -> revoke-old -> verify old is dead |
| Delete suspicious files, "clean up" | No | Never automatic | Destroys evidence; move to quarantine instead |
| Rebuild from clean image | Old host is gone | Human decision | The reliable remediation after confirmed compromise |

- Order matters: snapshot -> contain (reversible actions) -> human decision -> eradicate/rotate -> verify (re-run the original detection and confirm old credentials fail). The last step is what agents and humans most often skip.

### Gaps
- SecRespond full text not readable: per-model scores, the planning-axis checkpoint list, and any statement about credential rotation or post-cleanup verification remain unconfirmed.
- No retrieval of NIST SP 800-61r3 or SOAR vendor guidance on which containment actions are considered safe to automate; the table is reasoning from background knowledge.
- No measured data on false-positive rates of automated IP blocking or account lockout on small servers.

---

## 9. Synthesis: proposed autonomy tier table and concrete tool recommendations

### Takeaway
Evidence supports four tiers: read-only work is always automatic; vendor-authored, reversible, health-checkable changes are auto-applied behind a snapshot; anything LLM-authored or touching remote access goes through a PR or a timed-revert approval; and one-way doors are never automated. The dividing lines follow who authored the change and whether it can be undone, not how severe the vulnerability is.

### Cited Findings
- Vendor-authored security updates are applied automatically by default on Ubuntu, and Canonical judges that safer than not patching. — [Ubuntu Discourse thread](https://discourse.ubuntu.com/t/should-i-be-scared-of-unattended-upgrades-breaking-things/49832/)
- LLM-authored patches: 25 of 80 failures compiled but stayed exploitable; PoC-only validation overstates success 1.83x; 31 of 42 of the AIxCC winner's plausible patches were credited. — [arXiv 2607.29422](https://arxiv.org/pdf/2607.29422); [arXiv 2609.04075](https://arxiv.org/pdf/2609.04075); [arXiv 2509.14589](https://arxiv.org/pdf/2509.14589)
- Hardening remediation cannot be auto-reverted. — [Red Hat KB 7032665](https://access.redhat.com/node/7032665)
- Newly published dependency versions are the attack window; 3-day to 7-day cooldowns are now defaults or recommended. — [InfoQ, July 2026](https://infoq.com/news/2026/07/github-dependabot-cooldown); [Socket glossary](https://socket.dev/glossary/dependency-cooldown)
- Automation acting at speed on bad input causes the largest outages; the operator's remedy was to disable it. — [InfoQ on AWS post-mortem, Nov 2025](https://www.infoq.com/news/2025/11/aws-dynamodb-outage-postmortem)
- Stricter gating trades recovery for safety (harm 12% -> <2%, recovery 94% -> 65%). — [arXiv 2609.11264](https://arxiv.org/pdf/2609.11264)
- No agent produced a complete, verified remediation on any compromised host. — [arXiv 2607.26791](https://arxiv.org/abs/2607.26791)

### Inferences

**Proposed autonomy tier table**

| Tier | Rule | Fix classes | Why (evidence) |
|---|---|---|---|
| **0 — Always automatic (read-only)** | No state change on the host | Scans (Lynis, OpenSCAP audit, ssh-audit, docker-bench, Semgrep/CodeQL, dependency audit); checking that unattended-upgrades ran and whether a reboot is pending; reproducing an exploit in a sandbox copy; opening issues; drafting runbooks; restore drills on a scratch VM | Updaters fail silently (Ubuntu 25.10); agents are good at alert-surfaced findings (SecRespond) |
| **1 — Auto-apply, snapshot first, health-check, auto-rollback, rate-limited** | Change authored by trusted upstream OR trivially reversible and time-limited | Distro security-pocket package updates; restart of non-critical services after library updates; temporary IP block with expiry and admin allowlist; pausing/disconnecting a container flagged as compromised; forensics snapshot; pulling an already-approved image digest | Vendor default and stance (Canonical); FBAR-style routine remediation; all reversible |
| **2 — Agent prepares, human approves** (PR, or apply-with-timed-revert) | LLM-authored, or touches access paths, or needs semantic judgement | All application code fixes (PR with PoC test, variant tests, scanner delta, reviewer-model notes); dependency bumps (PR; auto-merge at most for patch-level after 7-day cooldown and green tests); non-security package upgrades; kernel reboot scheduling; SSH/firewall/PAM/sudoers/sysctl hardening (one rule at a time, validated, with dead-man revert and console access confirmed); Dockerfile/base-image changes; killing processes, locking users, removing keys; stopping the main app; provider-level quarantine | Plausible-but-wrong patch rates of 25-50%; 2.3% new-vulnerability rate; OpenSCAP not revertible; Shai-Hulud window; kill destroys evidence |
| **3 — Never automated (human executes; agent may write the plan)** | One-way doors | Destructive DB migrations or any data deletion; deleting logs, backups or snapshots; credential/secret rotation and token revocation; blanket "apply CIS profile"; release upgrades; bootloader, partition or disk-encryption changes; force-push or history rewrite; in-place "cleanup" after confirmed compromise (rebuild instead); editing the agent's own permissions, approval rules or audit log; disabling a security control; anything that sends messages or money off the box | Cannot be rolled back (section 4); SecRespond shows agents cannot be trusted to verify eradication; AWS/Diskerase show cost of unbounded automation |

**Cross-tier safeguards (from section 7):** one change at a time; daily cap on Tier-1 actions; refuse empty/"all" target sets; same fix failing twice trips a circuit breaker; append-only action log; single kill-switch file; a promoted action must have passed N times at the tier above before moving down a tier.

**Concrete tool recommendations for a solo operator on Debian/Ubuntu (the tool-specific facts are [BACKGROUND] unless cited above)**
- OS patching: `unattended-upgrades` restricted to the security pocket, auto-reboot off or in a fixed window, `needrestart` for service restarts, Ubuntu Pro free tier for Livepatch (cited: free for up to five personal machines).
- Rollback: provider snapshot before any Tier-1 kernel/libc/openssh/systemd update and before every Tier-2 host change; `etckeeper` for /etc history; app in containers pinned by digest with previous digest retained; database backups with point-in-time recovery, restore-tested monthly; data on a separate volume from the OS disk. Consider NixOS or a bootc/MicroOS-style host if starting fresh and rollback is the top priority.
- Hardening: Lynis and OpenSCAP in audit mode on a schedule; generate fixes as reviewable scripts, apply per-rule; `sshd -t` and second-session test; `netplan try` (cited: 120-second auto-revert) and an at-job/systemd-timer dead-man switch for firewall and SSH changes; verify provider console access first.
- Code fixes: agent opens PRs only; CI runs the PoC test, variant tests, full suite, Semgrep/CodeQL delta and a short fuzz session (`go test -fuzz`, Atheris, cargo-fuzz, or ClusterFuzzLite); a second model reviews the diff without the author's reasoning.
- Dependencies: Renovate or Dependabot with a 7-day minimum release age, package-manager cooldown as a second layer (cited: pnpm 11 and Yarn 4.15 default-on, npm `min-release-age` since 11.10.0, pip 26.1), lockfiles and frozen installs.
- Containment: CrowdSec or fail2ban for TTL'd blocks; `docker pause` / network disconnect; snapshot-first rule.

**Label summary**
- PROVEN: auto-applying distro security updates as default practice; plausible-but-incorrect LLM patches are common; cooldowns block most fast supply-chain attacks (small sample); automation without rate limits causes large outages; OpenSCAP remediation is not auto-revertible.
- PROMISING: multi-layer automated patch validation (CodeMender-style); LLM agents for SRE mitigation (up to 72.6% on SREGym); btrfs/snapper rollback on Debian/Ubuntu; independent reviewer models.
- HYPE: "autonomous agents fix vulnerabilities end-to-end without review"; vendor recall figures without disclosed benchmarks (Aardvark's 92%); agent-led cleanup of a compromised host.

### Gaps
- The tier table is a synthesis; no published source proposes or validates this exact tiering for a single self-managed VM.
- Thresholds (7-day cooldown, daily action caps, "N successful runs before promotion") are judgement calls; only the 7-day figure has direct evidence (8 of 10 attacks).
- Because no page could be opened this session, every number here should be spot-checked against the primary source before it appears in a final report; the highest-value checks are the AgenticRepair failure table, the SecRespond remediation findings, PatchBench's per-agent table, and the AIxCC SoK patch-correctness section.
