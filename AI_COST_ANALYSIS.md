# AI Cost Analysis
## AgentForge Healthcare AI Agent System

**Developer:** Joe Panetta (Giuseppe)
**Period:** Feb 24 - Mar 2, 2026 (7-day sprint)
**Last Updated:** Feb 28, 2026

---

## 1. Development & Testing Costs (Actual)

### Pre-Development Phase (Feb 23 - Repo Exploration)

| Item | Tokens Used | API Calls | Cost |
|------|------------|-----------|------|
| Claude Code (repo analysis) | ~300K tokens | 6 agent sessions | ~$4.50 |
| Claude Code (requirements analysis) | ~50K tokens | 1 session | ~$0.75 |
| **Subtotal Pre-Dev** | **~350K** | **7** | **~$5.25** |

### Phase 1: MVP (Day 1 - Feb 24)

| Item | Tokens Used | API Calls | Cost |
|------|------------|-----------|------|
| Groq/Llama 3.3 70B (dev/test) | ~500K tokens | ~50 calls | $0.00 (free tier) |
| Gemini Pro (initial testing) | ~100K tokens | ~10 calls | $0.00 (free tier, hit quota) |
| LangSmith (tracing) | N/A | N/A | $0.00 (free tier) |
| Claude Code (implementation) | ~800K tokens | ~30 sessions | ~$12.00 |
| Render (deployment) | N/A | N/A | $7.00/month (Starter plan) |
| **Subtotal Phase 1** | **~1.4M** | **~90** | **~$12.00** |

### Total Development Cost (Through Day 1)

| Category | Estimated | Actual |
|----------|-----------|--------|
| Claude Code (AI dev tool) | ~$15 | ~$17.25 |
| Groq Llama 3.3 70B (runtime) | $0 | $0.00 |
| Gemini Pro (initial, quota exceeded) | ~$2.25 | $0.00 |
| LangSmith (observability) | $0 | $0.00 |
| OpenEMR (self-hosted Docker) | $0 | $0.00 |
| Render (deployment) | $0 | $7.00/month (Starter plan) |
| **TOTAL DEV COST** | **~$17** | **~$24.25** |

---

## 2. Production Cost Projections

### LLM Provider Evolution

1. **Day 1:** Started with Gemini Pro free tier → quota exhausted (429 RESOURCE_EXHAUSTED)
2. **Day 1 pivot:** Switched to Groq/Llama 3.3 70B free tier → works, adopted as primary

Current architecture: **Groq/Llama 3.3 70B (primary) → Gemini Flash (fallback)**. Rate limit on the primary provider triggers automatic failover to Gemini.

### Assumptions
- 5 queries per user per day
- Average 3,000 tokens per query (2K input, 1K output)
- Primary: Groq/Llama 3.3 70B
- 1.5 tool calls per query average
- 20% verification overhead
- 30-day months

### LLM Pricing Comparison (as of Feb 2026)

| Model | Input (per 1M tokens) | Output (per 1M tokens) | Role |
|-------|----------------------|----------------------|------|
| Groq Llama 3.3 70B | $0.00 (free tier) | $0.00 (free tier) | **Primary** |
| Gemini 2.5 Flash | $0.10 | $0.40 | Fallback |

### Monthly Cost Projections (Groq Primary)

| Users | Queries/Month | LLM Cost | Infra Cost | Total/Month |
|-------|--------------|----------|-----------|-------------|
| 100 | 15,000 | $0.00 | $7 (Render Starter) | **~$7/month** |
| 1,000 | 150,000 | $0.00 | $25 (Render pro) | **~$25/month** |
| 10,000 | 1,500,000 | ~$45 (Groq paid tier) | $75 (Render pro+) | **~$120/month** |
| 100,000 | 15,000,000 | ~$600 (Groq paid + Gemini overflow) | $200 (dedicated infra) | **~$800/month** |

**Scaling notes:**
- At 10K users, Groq free tier rate limits (~6K RPM) are exceeded. Upgrade to Groq Developer plan: $0.05/M input tokens, $0.08/M output tokens for Llama 3.3 70B.
- At 100K users, need dedicated infrastructure (Render Team plan or AWS) + Groq Developer plan + Gemini 2.0 Flash as overflow provider for rate limit spikes.
- Cost advantage vs. Pre-Search projections: switching from Gemini Pro ($47/mo at 100 users) to Groq free tier ($0/mo at 100 users) reduced costs by 99% at demo scale.

### Cost Per Query Breakdown (Current)

| Component | Cost/Query |
|-----------|-----------|
| Groq Llama 3.3 70B (~3K tokens) | ~$0.00 |
| Tool execution (RxNorm, FDA APIs) | $0.000 (free public APIs) |
| Verification overhead | $0.000 |
| Infrastructure (Render Starter) | ~$0.0002 |
| **Total per query** | **~$0.00** |

### Cost Optimization with Fallback

When Groq rate-limits, queries automatically route to Gemini:
- **Gemini fallback cost**: ~$0.001/query
- In practice, demo/review loads stay well within Groq free tier limits

---

## 3. Cost Optimization Strategies

1. **Multi-provider fallback** - Groq primary with automatic failover to Gemini
2. **Prompt caching** - Reuse system prompts and tool schemas (LangChain built-in)
3. **Response caching** - Cache common drug interaction results (TTL: 24h)
4. **Rate limiting** - Cap queries per user (20/day free, 50/day premium)
5. **Token optimization** - Minimize prompt size, use structured output to reduce output tokens
6. **Smart routing** - Route all queries to Groq (free), Gemini fallback on rate limit

---

## 4. Actual Cost vs. Budget

| Metric | Target | Actual |
|--------|--------|--------|
| Development cost | <$50 | ~$24.25 ($17.25 Claude Code + $7 Render) |
| Per-query cost (production) | <$0.05 | ~$0.00 |
| Monthly cost (100 users) | <$100 | ~$7 (Render Starter only) |
| Monthly cost (1,000 users) | <$500 | ~$25 |

**Result:** Well under budget. Upgraded from Render free tier to Starter plan ($7/month) for persistent uptime and no cold starts. Groq free tier as primary LLM. Automatic fallback to Gemini provides resilience during rate limits.

---

## 5. Observability Cost

| Service | Tier | Monthly Cost | What It Provides |
|---------|------|-------------|-----------------|
| LangSmith | Free | $0.00 | Trace logging, latency breakdown, token tracking |
| Custom module | Built-in | $0.00 | TraceRecord persistence, dashboard stats, feedback, eval history |
| Render logs | Free | $0.00 | Application logging, deployment monitoring |

All observability is free-tier or self-hosted. The custom observability module (`app/observability.py`) provides:

- Per-request trace records (17 fields) persisted to JSONL
- Latency breakdown: LLM time, tool time, verification time, total time
- Token usage and provider-aware cost tracking ($0.00 for Groq)
- User feedback (thumbs up/down) stored per trace_id
- Eval history with pass rates and category breakdown
- Dashboard API (`GET /api/dashboard`) for Streamlit sidebar

---

## 6. Testing Infrastructure Cost

| Component | Tests | Runtime | Cost |
|-----------|-------|---------|------|
| Unit tests (pytest) | 165 | <9 seconds | $0.00 (no API keys needed) |
| Integration evals | 100 | ~5-10 min | $0.00 (Groq free tier) |
| LangSmith tracing | N/A | Always-on | $0.00 (free tier) |

Unit tests are fully isolated (no API cost). Integration evals use the same LLM provider as production. CI runs critical-only evals (10 cases) on push; full suite (100 cases) on manual trigger to conserve API quota.
