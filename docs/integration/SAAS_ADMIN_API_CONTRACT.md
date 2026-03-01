# SaaS Admin ↔ SETTLE Service API Contract

**Version:** 1.0  
**Last Updated:** December 15, 2025  
**Status:** Phase 2 Implementation

---

## 📋 **OVERVIEW**

This document defines the API contract between the SaaS Admin Platform and the SETTLE Service.

**SETTLE Service Base URL:**
- **Development:** `http://localhost:8002`
- **Production:** `https://settle-api.truevow.law`

---

## 🔐 **AUTHENTICATION**

All SaaS Admin requests to SETTLE must include an admin API key:

```typescript
// Headers
{
  "Authorization": "Bearer settle_admin_xxxxxxxxxxxxx",
  "Content-Type": "application/json"
}
```

**Admin API Key:**
- Format: `settle_admin_{32_char_random}`
- Access Level: `admin`
- Permissions: Full access to all endpoints

---

## 📊 **1. CONTRIBUTION REVIEW**

### **1.1 List Pending Contributions**

**Endpoint:** `GET /api/v1/admin/contributions/pending`

**Query Parameters:**
```typescript
{
  page?: number;        // Default: 1
  limit?: number;       // Default: 20, Max: 100
  status?: string;      // "pending" | "flagged" | "all"
  sort_by?: string;     // "created_at" | "jurisdiction" | "case_type"
  sort_order?: string;  // "asc" | "desc"
}
```

**Response:**
```typescript
{
  contributions: [
    {
      id: string;                    // UUID
      jurisdiction: string;          // "Maricopa County, AZ"
      case_type: string;            // "Motor Vehicle Accident"
      injury_category: string[];    // ["Spinal Injury"]
      medical_bills: number;        // 85000.00
      outcome_amount_range: string; // "$300k-$600k"
      status: string;               // "pending" | "flagged"
      contributed_at: string;       // ISO datetime
      contributor_user_id: string;  // User ID
      founding_member: boolean;     // true/false
      flags: string[];              // ["Possible PHI", "Outlier"]
    }
  ];
  pagination: {
    page: number;
    limit: number;
    total: number;
    total_pages: number;
  };
}
```

---

### **1.2 Get Contribution Details**

**Endpoint:** `GET /api/v1/admin/contributions/{contribution_id}`

**Response:**
```typescript
{
  id: string;
  // Full contribution data (all fields)
  jurisdiction: string;
  case_type: string;
  injury_category: string[];
  primary_diagnosis: string | null;
  treatment_type: string[];
  duration_of_treatment: string;
  imaging_findings: string[];
  medical_bills: number;
  lost_wages: number | null;
  policy_limits: string | null;
  defendant_category: string;
  outcome_type: string;
  outcome_amount_range: string;
  
  // Metadata
  contributed_at: string;
  created_at: string;
  updated_at: string;
  status: string;
  
  // Contributor info
  contributor_user_id: string;
  founding_member: boolean;
  
  // Validation
  blockchain_hash: string;
  consent_confirmed: boolean;
  flags: string[];              // Auto-detected issues
  confidence_score: number;     // 0.0-1.0
  is_outlier: boolean;
}
```

---

### **1.3 Approve Contribution**

**Endpoint:** `POST /api/v1/admin/contributions/{contribution_id}/approve`

**Request Body:**
```typescript
{
  notes?: string;  // Optional admin notes
}
```

**Response:**
```typescript
{
  status: "approved";
  contribution_id: string;
  approved_at: string;
  approved_by: string;  // Admin user ID
}
```

---

### **1.4 Reject Contribution**

**Endpoint:** `POST /api/v1/admin/contributions/{contribution_id}/reject`

**Request Body:**
```typescript
{
  reason: string;  // REQUIRED: "PHI detected", "Outlier", "Invalid data", etc.
  notes?: string;  // Optional detailed explanation
}
```

**Response:**
```typescript
{
  status: "rejected";
  contribution_id: string;
  rejected_at: string;
  rejected_by: string;  // Admin user ID
  reason: string;
}
```

---

## 👥 **2. FOUNDING MEMBER MANAGEMENT**

### **2.1 List Waitlist Entries**

**Endpoint:** `GET /api/v1/admin/waitlist`

**Query Parameters:**
```typescript
{
  page?: number;
  limit?: number;
  status?: "pending" | "approved" | "rejected" | "all";
  state?: string;  // Filter by state
}
```

**Response:**
```typescript
{
  entries: [
    {
      id: string;
      email: string;
      law_firm_name: string;
      practice_area: string;
      state: string;
      referral_source: string;
      status: "pending" | "approved" | "rejected";
      joined_at: string;
      notes: string | null;
    }
  ];
  pagination: { ... };
}
```

---

### **2.2 Approve Waitlist Entry (Enroll as Founding Member)**

**Endpoint:** `POST /api/v1/admin/founding-members/enroll`

**Request Body:**
```typescript
{
  waitlist_id: string;      // Waitlist entry ID
  user_id: string;          // Central users table ID
  email: string;
  first_name: string;
  last_name: string;
  law_firm_name: string;
  bar_number: string;       // Verified bar number
  state: string;
  send_welcome_email: boolean;  // Default: true
}
```

**Response:**
```typescript
{
  founding_member_id: string;
  api_key: string;          // ONLY returned once - display to admin
  api_key_prefix: string;   // "settle_fm_abc123"
  status: "active";
  enrolled_at: string;
  email_sent: boolean;      // If welcome email was sent
}
```

**⚠️ IMPORTANT:** The full `api_key` is only returned ONCE and is never stored in plain text.  
Display it immediately to the admin and/or email it to the attorney.

---

## 📚 **TYPESCRIPT CLIENT EXAMPLE**

```typescript
// settleClient.ts
import axios, { AxiosInstance } from 'axios';

class SettleClient {
  private client: AxiosInstance;
  
  constructor(apiKey: string, baseURL: string = 'http://localhost:8002') {
    this.client = axios.create({
      baseURL,
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
      },
    });
  }
  
  async listPendingContributions(page = 1, limit = 20) {
    const { data } = await this.client.get('/api/v1/admin/contributions/pending', {
      params: { page, limit },
    });
    return data;
  }
  
  async approveContribution(contributionId: string, notes?: string) {
    const { data } = await this.client.post(
      `/api/v1/admin/contributions/${contributionId}/approve`,
      { notes }
    );
    return data;
  }
  
  async getAnalyticsDashboard() {
    const { data } = await this.client.get('/api/v1/admin/analytics/dashboard');
    return data;
  }
}

export default SettleClient;
```

---

**Status:** Ready for frontend implementation in SaaS Admin platform.

