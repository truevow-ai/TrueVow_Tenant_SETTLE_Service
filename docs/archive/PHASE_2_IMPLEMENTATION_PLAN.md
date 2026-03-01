# SETTLE Service - Phase 2 Implementation Plan

**Start Date:** December 15, 2025  
**Target Completion:** Q1 2026  
**Status:** 🚧 IN PROGRESS

---

## 📋 **PHASE 2 OVERVIEW**

Phase 2 transforms SETTLE from a functional backend service to a production-ready platform with:
- SaaS Admin UI integration
- Email notifications
- PDF report generation
- File storage (S3)
- Payment processing (Stripe)
- Production monitoring

---

## 🎯 **PHASE 2 OBJECTIVES**

### **Primary Goals:**
1. ✅ Enable SaaS Admin to manage SETTLE service
2. ✅ Automate attorney workflows (notifications, reports)
3. ✅ Enable monetization (billing for reports)
4. ✅ Production-ready deployment
5. ✅ Monitoring and observability

### **Success Metrics:**
- [ ] SaaS Admin can review/approve contributions
- [ ] SaaS Admin can enroll Founding Members
- [ ] Attorneys receive automated email notifications
- [ ] PDF reports generate in <2 seconds
- [ ] Stripe billing processes successfully
- [ ] System handles 100+ concurrent users

---

## 📦 **PHASE 2 COMPONENTS (7 Major Areas)**

### **1. SaaS Admin UI Integration** 🎨
**Priority:** 🔴 CRITICAL (Week 1-2)  
**Complexity:** HIGH  
**Dependencies:** None

**Features:**
- [ ] Contribution Review Dashboard
  - [ ] List pending contributions with filters
  - [ ] View contribution details (sanitized)
  - [ ] Approve/Reject workflow
  - [ ] PHI detection highlights
  - [ ] Bulk actions
  
- [ ] Founding Member Management
  - [ ] Waitlist approval workflow
  - [ ] Member enrollment form
  - [ ] API key generation and display
  - [ ] Contribution tracking per member
  - [ ] Status management (active/suspended)
  
- [ ] Analytics Dashboard
  - [ ] Real-time metrics (contributions, queries, reports)
  - [ ] Jurisdiction coverage map
  - [ ] Revenue tracking
  - [ ] Member growth charts
  - [ ] Data quality metrics
  
- [ ] API Key Management
  - [ ] Generate new keys
  - [ ] Revoke/rotate keys
  - [ ] Usage tracking per key
  - [ ] Rate limit configuration

**Technical Stack:**
- Frontend: React + TypeScript (existing SaaS Admin tech)
- State: React Query for API calls
- UI: Existing component library
- Charts: Recharts or Chart.js

**Files to Create:**
```
C:\Users\yasha\OneDrive\Documents\TrueVow\Cursor\2025-TrueVow-Tenant-Application\
└── saas-admin-platform/
    └── src/
        └── features/
            └── settle/
                ├── components/
                │   ├── ContributionReviewList.tsx
                │   ├── ContributionDetailModal.tsx
                │   ├── FoundingMemberEnrollment.tsx
                │   ├── FoundingMemberList.tsx
                │   ├── AnalyticsDashboard.tsx
                │   └── APIKeyManagement.tsx
                ├── hooks/
                │   ├── useContributions.ts
                │   ├── useFoundingMembers.ts
                │   └── useSettleAnalytics.ts
                └── api/
                    └── settleClient.ts
```

---

### **2. Email Notifications** 📧
**Priority:** 🟡 HIGH (Week 2)  
**Complexity:** MEDIUM  
**Dependencies:** Email service provider account

**Email Types:**
1. [ ] **Waitlist Confirmation**
   - Sent immediately after joining waitlist
   - Position in queue
   - Expected wait time
   
2. [ ] **Founding Member Welcome**
   - API key delivery (secure link)
   - Getting started guide
   - Contribution requirements
   
3. [ ] **Contribution Status**
   - Approved: Thank you + count toward goal
   - Rejected: Reason + how to fix
   - Flagged: Manual review needed
   
4. [ ] **Report Delivery**
   - Secure download link (7-day expiration)
   - Report summary
   - Blockchain verification hash
   
5. [ ] **Founding Member Milestones**
   - 1st contribution submitted
   - 10th contribution (full access activated)
   - Quarterly stats summary

**Email Service Options:**
- **Recommended:** SendGrid (99%+ deliverability, great APIs)
- Alternative: Mailgun, AWS SES
- Templates: Handlebars or React Email

**Implementation:**
```python
# app/services/notifications/
├── email_service.py        # SendGrid integration
├── templates/
│   ├── waitlist_confirmation.html
│   ├── founding_member_welcome.html
│   ├── contribution_approved.html
│   ├── contribution_rejected.html
│   └── report_delivery.html
└── tests/
    └── test_email_service.py
```

**Environment Variables:**
```bash
SETTLE_SENDGRID_API_KEY=SG.xxxxx
SETTLE_FROM_EMAIL=settle@truevow.law
SETTLE_REPLY_TO_EMAIL=support@truevow.law
```

---

### **3. PDF Report Generation** 📄
**Priority:** 🟡 HIGH (Week 3)  
**Complexity:** HIGH  
**Dependencies:** None

**Report Structure (4-page template):**

**Page 1: Settlement Range Summary**
- Case overview (jurisdiction, injury type, medical bills)
- Settlement range visualization (box plot)
- Confidence level indicator
- Number of comparable cases
- TrueVow SETTLE™ branding

**Page 2: Comparable Cases Table**
- 10-15 anonymized similar cases
- Columns: Jurisdiction | Case Type | Injury | Medical Bills | Outcome Range | Date
- Color coding by confidence
- NO narratives, NO identifying information

**Page 3: Range Justification**
- Methodology explanation (percentile vs multiplier)
- County clustering (if applicable)
- Adjustment factors
- Confidence level explanation
- Data quality statement

**Page 4: Compliance & Integrity**
- "This report contains ZERO PHI" statement
- OpenTimestamps blockchain hash
- QR code for verification
- Disclaimer: "Descriptive statistics only, not legal advice"
- Attorney safety guarantees
- TrueVow contact information

**Technology Options:**
1. **WeasyPrint** (Recommended)
   - Python-based, HTML/CSS to PDF
   - Great for templates
   - Easy styling
   
2. **Playwright PDF**
   - Render React components
   - Chrome-based rendering
   
3. **ReportLab**
   - Python PDF library
   - More code, less design flexibility

**Implementation:**
```python
# app/services/reports/
├── pdf_generator.py         # WeasyPrint integration
├── templates/
│   ├── base.html           # Base template with header/footer
│   ├── page1_summary.html
│   ├── page2_cases.html
│   ├── page3_justification.html
│   └── page4_compliance.html
├── static/
│   ├── css/
│   │   └── report_styles.css
│   └── images/
│       └── truevow_logo.png
└── tests/
    └── test_pdf_generator.py
```

**Dependencies:**
```txt
weasyprint==60.1
pillow==10.1.0  # For images
qrcode==7.4.2   # For blockchain verification QR
```

---

### **4. File Storage (AWS S3)** 🗄️
**Priority:** 🟡 HIGH (Week 3)  
**Complexity:** MEDIUM  
**Dependencies:** AWS account, S3 bucket

**Storage Structure:**
```
truevow-settle-reports/
├── reports/
│   ├── 2025/
│   │   ├── 12/
│   │   │   ├── {report_id}.pdf
│   │   │   └── {report_id}.json
│   └── ...
└── temp/
    └── {report_id}_temp.pdf  # 7-day auto-delete
```

**Features:**
- [ ] Presigned URLs (7-day expiration)
- [ ] Automatic cleanup (delete after 30 days)
- [ ] Encryption at rest (S3 SSE)
- [ ] Access logging
- [ ] CDN integration (CloudFront)

**Implementation:**
```python
# app/services/storage/
├── s3_service.py           # AWS S3 integration
├── storage_config.py       # Bucket config
└── tests/
    └── test_s3_service.py
```

**Environment Variables:**
```bash
SETTLE_AWS_ACCESS_KEY_ID=AKIA...
SETTLE_AWS_SECRET_ACCESS_KEY=...
SETTLE_AWS_REGION=us-west-2
SETTLE_S3_BUCKET=truevow-settle-reports
SETTLE_CLOUDFRONT_DOMAIN=reports.truevow.law
```

---

### **5. Payment Processing (Stripe)** 💳
**Priority:** 🟢 MEDIUM (Week 4)  
**Complexity:** MEDIUM  
**Dependencies:** Stripe account

**Pricing Model:**
- **Founding Members:** Free forever (0-2,100)
- **Standard Users:** $49 per report
- **Premium Subscription:** $199/month unlimited
- **Enterprise:** Custom pricing

**Features:**
- [ ] One-time payment ($49 per report)
- [ ] Subscription management ($199/month)
- [ ] Invoice generation
- [ ] Payment receipts (email)
- [ ] Failed payment handling
- [ ] Refund processing

**Stripe Integration:**
```python
# app/services/billing/
├── stripe_service.py       # Stripe integration
├── pricing.py              # Pricing logic
├── webhooks.py             # Stripe webhooks
└── tests/
    └── test_stripe_service.py
```

**Database Updates:**
```sql
-- Add to settle_api_keys table
ALTER TABLE settle.settle_api_keys ADD COLUMN stripe_customer_id TEXT;
ALTER TABLE settle.settle_api_keys ADD COLUMN subscription_status TEXT;
ALTER TABLE settle.settle_api_keys ADD COLUMN subscription_id TEXT;

-- Create payments table
CREATE TABLE settle.settle_payments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id TEXT NOT NULL,
    api_key_id UUID REFERENCES settle.settle_api_keys(id),
    amount DECIMAL(10,2) NOT NULL,
    currency TEXT DEFAULT 'USD',
    stripe_payment_intent_id TEXT,
    stripe_charge_id TEXT,
    status TEXT NOT NULL, -- pending, succeeded, failed, refunded
    report_id UUID REFERENCES settle.settle_reports(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Environment Variables:**
```bash
SETTLE_STRIPE_SECRET_KEY=sk_test_...
SETTLE_STRIPE_PUBLISHABLE_KEY=pk_test_...
SETTLE_STRIPE_WEBHOOK_SECRET=whsec_...
```

---

### **6. Production Monitoring** 📊
**Priority:** 🟢 MEDIUM (Week 5)  
**Complexity:** MEDIUM  
**Dependencies:** Monitoring service accounts

**Monitoring Stack:**
1. **Application Monitoring:** Sentry
   - Error tracking
   - Performance monitoring
   - User feedback
   
2. **Logging:** CloudWatch or Papertrail
   - Centralized logs
   - Search and filtering
   - Alerts on errors
   
3. **Uptime Monitoring:** UptimeRobot or Pingdom
   - Endpoint health checks
   - Alert on downtime
   
4. **Analytics:** PostHog or Mixpanel
   - User behavior
   - Feature usage
   - Conversion funnels

**Implementation:**
```python
# app/core/monitoring.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn=settings.SENTRY_DSN,
    integrations=[FastApiIntegration()],
    environment=settings.ENVIRONMENT,
    traces_sample_rate=0.1,
)
```

**Alerts:**
- [ ] API error rate > 1%
- [ ] Response time > 2s (p95)
- [ ] Database query time > 500ms
- [ ] Failed payments
- [ ] PHI detection triggered

---

### **7. Production Deployment** 🚀
**Priority:** 🟢 MEDIUM (Week 6)  
**Complexity:** HIGH  
**Dependencies:** All above features complete

**Deployment Options:**

**Option A: Fly.io (Recommended for MVP)**
- Easiest setup
- Auto TLS certificates
- Global distribution
- $10-20/month starting cost

**Option B: AWS ECS/Fargate (Enterprise)**
- More control
- Better for scale
- Higher initial cost

**Deployment Checklist:**
- [ ] Environment variables configured
- [ ] Database migrations run
- [ ] CORS configured for production domain
- [ ] API keys rotated
- [ ] Rate limiting enabled
- [ ] Monitoring configured
- [ ] SSL certificates installed
- [ ] DNS configured
- [ ] Load testing completed
- [ ] Backup strategy implemented

**Infrastructure:**
```
Production Environment:
├── API Server (Fly.io/AWS)
│   ├── 2+ instances (high availability)
│   ├── Load balancer
│   └── Auto-scaling
├── Database (Supabase Production)
│   ├── Daily backups
│   ├── Point-in-time recovery
│   └── Read replicas (if needed)
├── File Storage (S3)
│   └── CloudFront CDN
├── Monitoring (Sentry + CloudWatch)
└── Email (SendGrid)
```

---

## 📅 **IMPLEMENTATION TIMELINE**

### **Week 1-2: SaaS Admin UI** (Dec 15-29)
- [ ] Contribution Review Dashboard
- [ ] Founding Member Management
- [ ] Analytics Dashboard
- [ ] API Key Management

### **Week 3: Email + PDF** (Dec 30 - Jan 5)
- [ ] SendGrid integration
- [ ] Email templates (5)
- [ ] PDF generation (WeasyPrint)
- [ ] 4-page report template

### **Week 4: Storage + Billing** (Jan 6-12)
- [ ] AWS S3 setup
- [ ] File upload/download
- [ ] Stripe integration
- [ ] Payment workflows

### **Week 5: Monitoring** (Jan 13-19)
- [ ] Sentry setup
- [ ] CloudWatch logs
- [ ] Uptime monitoring
- [ ] Analytics tracking

### **Week 6: Production Launch** (Jan 20-26)
- [ ] Deploy to production
- [ ] Load testing
- [ ] Security audit
- [ ] Go-live checklist

---

## 🎯 **IMMEDIATE NEXT STEPS (TODAY)**

### **Priority 1: SaaS Admin Integration Specifications**
1. [ ] Create API contract for SaaS Admin
2. [ ] Design UI mockups for key screens
3. [ ] Define data models for UI
4. [ ] Set up API client in SaaS Admin codebase

### **Priority 2: Enable Authentication**
1. [ ] Implement `APIKeyAuth` dependency properly
2. [ ] Create API key generation endpoint
3. [ ] Add authentication middleware
4. [ ] Test with real API keys

### **Priority 3: Email Service Setup**
1. [ ] Choose email provider (SendGrid recommended)
2. [ ] Create email templates
3. [ ] Implement email service class
4. [ ] Test email delivery

---

## 📊 **PHASE 2 METRICS**

### **Development Metrics:**
- [ ] Lines of code written
- [ ] Tests added (target: 80%+ coverage)
- [ ] API endpoints added
- [ ] UI components created

### **Quality Metrics:**
- [ ] Test coverage > 80%
- [ ] API response time < 500ms (p95)
- [ ] PDF generation < 2s
- [ ] Email delivery > 99%
- [ ] Payment success rate > 99%

### **Business Metrics:**
- [ ] Founding Members enrolled
- [ ] Reports generated
- [ ] Revenue generated
- [ ] User satisfaction score

---

## 🚦 **GO/NO-GO CRITERIA**

**Phase 2 is complete when:**
- ✅ SaaS Admin can fully manage SETTLE
- ✅ All 5 email types working
- ✅ PDF reports generate correctly
- ✅ S3 storage operational
- ✅ Stripe billing processing successfully
- ✅ Monitoring dashboards live
- ✅ Production deployment complete
- ✅ Load testing passed (100+ concurrent users)
- ✅ Security audit passed
- ✅ Documentation updated

---

## 📚 **RESOURCES NEEDED**

### **Accounts/Services:**
- [ ] SendGrid account (free tier: 100 emails/day)
- [ ] AWS account (S3 + CloudWatch)
- [ ] Stripe account (test + production)
- [ ] Sentry account (free tier: 5k errors/month)
- [ ] Fly.io account (or AWS)

### **Development:**
- [ ] Access to SaaS Admin codebase
- [ ] Figma/design tool for UI mockups
- [ ] Postman/Insomnia for API testing

### **Testing:**
- [ ] Test email addresses
- [ ] Test Stripe cards
- [ ] Load testing tool (K6 or Artillery)

---

**Status:** 🚧 Ready to begin Phase 2 implementation!

**Next Action:** Start with SaaS Admin UI integration specifications and API authentication.



