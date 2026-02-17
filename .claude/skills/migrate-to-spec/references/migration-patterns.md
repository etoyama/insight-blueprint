# Migration Patterns Reference

Common scenarios for migrating `/startproject` work to formal spec-workflow.

## Pattern 1: Bug Fix → Security Audit

**Scenario:** Started as simple bug fix, discovered wider security implications.

**Original /startproject scope:**
- Fix input validation error in login form
- Estimated: 2 hours
- Files affected: `auth/login.py`

**Why migration needed:**
- Discovered broader XSS vulnerability
- Affects multiple endpoints
- Requires security review & approval

**Migration approach:**

1. **Requirements:**
   - User Story: "As a user, I want my input to be sanitized so that XSS attacks are prevented"
   - Functional: Sanitize all user inputs across application
   - Non-Functional: OWASP compliance, < 5ms overhead
   - Acceptance: Pass security audit, no XSS in penetration test

2. **Design:**
   - Centralized input sanitization middleware
   - Whitelist-based approach
   - Content Security Policy headers

3. **Tasks:**
   - 1.1 Fix original login bug (DONE)
   - 1.2 Audit all input points (TODO)
   - 1.3 Implement sanitization middleware (TODO)
   - 1.4 Security penetration test (TODO)
   - 1.5 Documentation (TODO)

---

## Pattern 2: Feature → Multi-Phase Project

**Scenario:** Simple feature request expanded into multi-phase project.

**Original /startproject scope:**
- Add email notifications for new messages
- Estimated: 1 day
- Files: `notifications/email.py`

**Why migration needed:**
- Stakeholder requested SMS, push notifications too
- Needs notification preferences UI
- Requires infrastructure (queues, rate limiting)
- 3+ week timeline

**Migration approach:**

1. **Requirements:**
   - Phase 1: Email notifications (DONE)
   - Phase 2: SMS & push notifications
   - Phase 3: User preference management
   - Phase 4: Analytics & A/B testing

2. **Design:**
   - Pluggable notification system architecture
   - Event-driven with message queues
   - Provider abstraction (SendGrid, Twilio, FCM)

3. **Tasks by Phase:**
   - Phase 1: 1.1-1.3 (DONE)
   - Phase 2: 2.1-2.5 (approval needed)
   - Phase 3: 3.1-3.4 (pending)
   - Phase 4: 4.1-4.3 (future)

---

## Pattern 3: Prototype → Production

**Scenario:** POC worked well, now needs production hardening.

**Original /startproject scope:**
- Proof of concept: ML model serving
- Estimated: 3 days
- Files: `ml/predictor.py`, `api/predict.py`

**Why migration needed:**
- CEO demo went well, wants production deployment
- Needs monitoring, error handling, scalability
- Security review required
- Load testing needed

**Migration approach:**

1. **Requirements:**
   - Functional: All POC features + error handling
   - Non-Functional:
     - 99.9% uptime SLA
     - < 100ms p95 latency
     - Support 1000 req/sec
   - Security: API key auth, rate limiting
   - Monitoring: Metrics, logging, alerting

2. **Design:**
   - Containerized deployment (Docker)
   - Load balancer + auto-scaling
   - Redis for rate limiting
   - Prometheus + Grafana for monitoring
   - Sentry for error tracking

3. **Task Breakdown:**
   - 1.x: POC implementation (DONE)
   - 2.x: Production infrastructure (TODO)
     - 2.1: Containerization
     - 2.2: CI/CD pipeline
     - 2.3: Monitoring setup
   - 3.x: Hardening (TODO)
     - 3.1: Error handling
     - 3.2: Authentication
     - 3.3: Rate limiting
   - 4.x: Testing (TODO)
     - 4.1: Load testing
     - 4.2: Security audit
     - 4.3: Chaos engineering

---

## Decision Framework

Use this checklist to decide if migration is needed:

| Indicator | /startproject OK | Migrate to Spec |
|-----------|------------------|-----------------|
| **Timeline** | < 1 day remaining | 1+ days remaining |
| **Stakeholders** | Just you | Multiple people |
| **Approval** | Not needed | Required |
| **Risk** | Low impact | High impact |
| **Complexity** | Original estimate accurate | Scope creep occurred |
| **Visibility** | No tracking needed | Progress tracking needed |

**Migration trigger phrases:**
- "This is bigger than I thought"
- "Need to get approval for this"
- "Other teams are affected"
- "Can we track progress on this?"
- "How do we coordinate on this?"

---

## Post-Migration Best Practices

### 1. Link Original Work
In requirements.md:
```markdown
## Context
This spec formalizes work originally started via /startproject.
Original docs: `.claude/docs/DESIGN.md`
```

### 2. Document Scope Creep
In design.md:
```markdown
## Evolution
Originally scoped as simple bug fix. During implementation,
discovered wider security implications requiring formal review.
```

### 3. Honest Task Status
Don't mark incomplete work as done:
```markdown
✅ 1.1 Fix login validation (DONE)
⚠️  1.2 Audit other endpoints (IN PROGRESS - 60% done)
❌ 1.3 Security testing (TODO)
```

### 4. Technical Debt Callout
```markdown
## Known Issues
- Used quick fix in 1.1, needs refactoring
- Input sanitization is basic, should use library
- No unit tests yet (blocked by infrastructure)
```
