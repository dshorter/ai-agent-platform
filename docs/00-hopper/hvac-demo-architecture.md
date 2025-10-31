---
**🕐 Response Timestamp: Thursday, October 30, 2025 at 07:29:42 PM EDT**

---

## 🏗️ HVAC Event Generator - System Architecture (Option B)

### 🎯 Core Design Philosophy

**"The Event Generator IS an AI Agent"**

- Not just a dumb loop creating records
- Uses Pure JSON Contract pattern for predictability
- Sequence-aware logging from the start
- Idempotent for demo repeatability
- Observability built-in (dogfooding our own product!)

---

## 📐 Architecture Layers

### **Layer 1: Trigger & Control Plane**

```
┌─────────────────────────────────────────────────────┐
│  TRIGGER OPTIONS                                     │
│  ├─ Manual Webhook (for demos)                      │
│  ├─ Scheduled Cron (for continuous simulation)      │
│  └─ API Endpoint (for dashboard "Generate Events")  │
└─────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────┐
│  POLICY NODE (Central Configuration)                 │
│  ├─ Scenario definitions                            │
│  ├─ Event type weights & patterns                   │
│  ├─ Time-of-day rules                               │
│  ├─ Budget constraints (max events, duration)       │
│  └─ Idempotency settings (TTL)                      │
└─────────────────────────────────────────────────────┘
```

### **Layer 2: State Management**

```
┌─────────────────────────────────────────────────────┐
│  STATE INITIALIZATION                                │
│                                                      │
│  {                                                   │
│    run_id: "ULID-20251030-192942-ABC123"           │
│    scenario_name: "winter_emergency_surge"          │
│    goal: "Generate 50 realistic HVAC events"        │
│    constraints: {                                    │
│      max_events: 50,                                │
│      time_spread_minutes: 60,                       │
│      respect_business_hours: true                   │
│    },                                               │
│    counters: {                                      │
│      events_created: 0,                             │
│      duration_ms: 0,                                │
│      errors: 0                                      │
│    },                                               │
│    scratchpad: {                                    │
│      plan: "Create winter emergency pattern",       │
│      progress: "Starting...",                       │
│      observations: []                               │
│    }                                                │
│  }                                                  │
└─────────────────────────────────────────────────────┘
```

### **Layer 3: Generator Core (The Agent Loop)**

```
┌─────────────────────────────────────────────────────┐
│  GENERATOR AGENT (Pure JSON Contract)               │
│                                                      │
│  INPUT: Current state + scenario config             │
│                                                      │
│  OUTPUT (Pure JSON):                                │
│  {                                                   │
│    "control": {                                     │
│      "done": false,                                 │
│      "reason": "ok"                                 │
│    },                                               │
│    "next_action": {                                 │
│      "type": "create_event",                        │
│      "event_data": {                                │
│        "event_type": "emergency",                   │
│        "customer_id": 2,                            │
│        "urgency": 9,                                │
│        "description": "AC unit failed, 95°F inside",│
│        "estimated_revenue": 380.00,                 │
│        "scenario_name": "summer_heatwave"           │
│      }                                              │
│    },                                               │
│    "state_update": {                                │
│      "observation": "Created emergency event",      │
│      "confidence": 0.98                             │
│    }                                                │
│  }                                                  │
└─────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────┐
│  VALIDATOR NODE                                      │
│  ├─ Verify JSON contract compliance                 │
│  ├─ Validate event_data schema                      │
│  ├─ Check against policy constraints                │
│  └─ Throw on violations                             │
└─────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────┐
│  IDEMPOTENCY GATE                                    │
│  ├─ Hash event parameters                           │
│  ├─ Check cache (TTL: 300s)                         │
│  ├─ If cached: skip creation, log "deduped"         │
│  └─ If new: mark in-flight, proceed                 │
└─────────────────────────────────────────────────────┘
```

### **Layer 4: Event Creation & Logging**

```
┌─────────────────────────────────────────────────────┐
│  POSTGRES INSERT NODE                                │
│  ├─ Insert into hvac_events table                   │
│  ├─ Capture event_id (RETURNING *)                  │
│  └─ Handle errors gracefully                        │
└─────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────┐
│  WORKFLOW_EXECUTION LOGGER                           │
│  ├─ Insert into workflow_executions                 │
│  ├─ execution_id (UUID)                             │
│  ├─ workflow_name: "event_generator"                │
│  ├─ status: "running"                               │
│  └─ Link to event_id                                │
└─────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────┐
│  AGENT_DECISION LOGGER (Sequence-Aware)             │
│  ├─ decision_id (auto)                              │
│  ├─ event_id (from hvac_events)                     │
│  ├─ workflow_execution_id (from above)              │
│  ├─ workflow_sequence_id (groups this run)          │
│  ├─ agent_name: "event_generator"                   │
│  ├─ decision_type: "create_event"                   │
│  ├─ step_number (monotonic)                         │
│  ├─ routing_reason: "Scenario: winter_emergency"    │
│  ├─ decision_confidence: 0.98                       │
│  └─ decision_payload: {full_event_details}          │
└─────────────────────────────────────────────────────┘
```

### **Layer 5: Loop Control & Budgets**

```
┌─────────────────────────────────────────────────────┐
│  BUDGET CHECK NODE                                   │
│                                                      │
│  Hard Stops:                                        │
│  ├─ events_created >= max_events ? → DONE          │
│  ├─ duration_ms >= max_duration ? → DONE           │
│  ├─ errors >= 3 ? → FAIL                           │
│  └─ Otherwise → LOOP BACK                          │
└─────────────────────────────────────────────────────┘
```

---

## 🎨 Scenario System Design

### **Pre-Configured Scenarios**

Each scenario is a JSON object defining event patterns:

```javascript
{
  "winter_emergency_surge": {
    "description": "Cold snap causes HVAC failures",
    "event_count": 50,
    "time_spread_minutes": 120,
    "event_distribution": {
      "emergency": 0.60,      // 60% emergencies
      "inquiry": 0.25,        // 25% panicked inquiries
      "appointment": 0.10,    // 10% scheduling
      "complaint": 0.05       // 5% complaints
    },
    "urgency_bias": "high",   // More 8-10 urgency scores
    "time_pattern": "evening_heavy", // 5pm-10pm spike
    "customer_pool": [1, 2, 3, 4], // Residential customers
    "revenue_range": [250, 600]
  },
  
  "routine_maintenance_day": {
    "description": "Normal business day",
    "event_count": 30,
    "time_spread_minutes": 480, // 8 hours
    "event_distribution": {
      "appointment": 0.50,
      "inquiry": 0.25,
      "follow_up": 0.15,
      "maintenance": 0.10
    },
    "urgency_bias": "low",
    "time_pattern": "business_hours", // 8am-5pm
    "customer_pool": [1, 2, 3, 4, 5], // All customers
    "revenue_range": [150, 350]
  },
  
  "summer_heatwave": {
    "description": "AC failures during heat emergency",
    "event_count": 75,
    "time_spread_minutes": 180,
    "event_distribution": {
      "emergency": 0.70,
      "inquiry": 0.20,
      "complaint": 0.10
    },
    "urgency_bias": "extreme",
    "time_pattern": "afternoon_spike", // 2pm-6pm
    "customer_pool": [1, 2, 5], // Residential + commercial
    "revenue_range": [300, 800]
  }
}
```

---

## 🔄 Event Generation Algorithm

### **Time Distribution Logic**

```javascript
// Pseudo-code for realistic timing
function calculateEventTimestamp(scenario, eventIndex, totalEvents) {
  const startTime = Date.now();
  const spreadMs = scenario.time_spread_minutes * 60 * 1000;
  
  // Base distribution (linear spread)
  let baseOffset = (spreadMs / totalEvents) * eventIndex;
  
  // Apply time pattern weighting
  if (scenario.time_pattern === "evening_heavy") {
    // Cluster 70% of events in last 30% of time window
    if (eventIndex > totalEvents * 0.7) {
      baseOffset = spreadMs * 0.7 + (eventIndex - totalEvents * 0.7) * 
                   (spreadMs * 0.3) / (totalEvents * 0.3);
    }
  }
  
  // Add realistic jitter (±5 minutes)
  const jitter = (Math.random() - 0.5) * 10 * 60 * 1000;
  
  return new Date(startTime + baseOffset + jitter);
}
```

### **Event Type Selection**

```javascript
function selectEventType(scenario) {
  const rand = Math.random();
  let cumulative = 0;
  
  for (const [eventType, probability] of Object.entries(scenario.event_distribution)) {
    cumulative += probability;
    if (rand <= cumulative) return eventType;
  }
  
  return "inquiry"; // fallback
}
```

### **Urgency Assignment**

```javascript
function calculateUrgency(eventType, urgencyBias) {
  const baseUrgency = {
    "emergency": [8, 9, 10],
    "complaint": [5, 6, 7],
    "inquiry": [3, 4, 5],
    "appointment": [2, 3, 4],
    "follow_up": [1, 2, 3],
    "maintenance": [2, 3, 4]
  };
  
  const range = baseUrgency[eventType] || [3, 4, 5];
  
  // Apply bias
  if (urgencyBias === "high" || urgencyBias === "extreme") {
    return Math.max(...range); // Use highest in range
  }
  
  // Random within range
  return range[Math.floor(Math.random() * range.length)];
}
```

---

## 📊 Observability Integration

### **What Gets Logged (Per Event Created)**

```sql
-- 1. The event itself
INSERT INTO hvac_events (...) VALUES (...);

-- 2. Workflow execution record
INSERT INTO workflow_executions (
  execution_id,
  workflow_name,
  event_id,
  status,
  started_at
) VALUES (
  gen_random_uuid(),
  'event_generator',
  <new_event_id>,
  'success',
  NOW()
);

-- 3. Agent decision record (sequence-aware!)
INSERT INTO agent_decisions (
  event_id,
  workflow_execution_id,
  workflow_sequence_id,  -- Same for entire run
  agent_name,
  decision_type,
  step_number,           -- Increments: 1, 2, 3...
  routing_reason,
  decision_confidence,
  decision_payload
) VALUES (
  <new_event_id>,
  <execution_id>,
  <run_sequence_id>,     -- UUID for this generator run
  'event_generator',
  'create_event',
  <step_counter>,
  'Scenario: winter_emergency_surge [Event 15/50]',
  0.98,
  '{"scenario": "winter_emergency_surge", "pattern": "evening_heavy"}'::jsonb
);
```

---

## 🎯 Success Criteria

### **Generator Quality Metrics**

1. **Distribution Accuracy**
   - Event types match scenario percentages (±5%)
   - Urgency scores follow expected patterns
   - Time distribution matches pattern definition

2. **Realism**
   - No two events at exact same millisecond
   - Revenue estimates make sense for event type
   - Customer selection follows constraints

3. **Observability**
   - Every event has full audit trail
   - Sequence numbers are monotonic
   - No orphaned records in any table

4. **Performance**
   - Generate 100 events in <10 seconds
   - No database errors
   - Memory usage stable across runs

---

## 🔧 n8n Workflow Node Summary

**Total Nodes: ~12**

1. **Webhook Trigger** - Manual/scheduled entry point
2. **Policy Loader** - Load scenario config from static data
3. **State Initializer** - Create run state with run_id, counters
4. **Generator Logic** - Pure JSON contract output
5. **Validator** - Contract compliance check
6. **Idempotency Gate** - Dedupe check
7. **PostgreSQL Insert (hvac_events)** - Create event
8. **PostgreSQL Insert (workflow_executions)** - Log workflow
9. **PostgreSQL Insert (agent_decisions)** - Sequence-aware log
10. **Counter Updater** - Increment state counters
11. **Budget Checker** - Loop control logic
12. **Response Formatter** - Final summary output

---

## 🚀 What This Enables

✅ **Demo Repeatability** - Same scenario = same events (idempotent)  
✅ **Time Travel** - Replay any generator run from logs  
✅ **Pattern Analysis** - "Show me all winter_emergency events"  
✅ **Cost Tracking** - No LLM costs (deterministic generation)  
✅ **Observability Dogfooding** - We use our own sequence-aware logging  
✅ **Professional Polish** - Not a toy, this is production-grade  

---

## 💭 Next Steps

**Ready to move to:**

**Option 2: n8n Workflow Structure** - Detailed node-by-node breakdown  
**Option 3: Jump to Code** - Start building the actual nodes

**Which direction, broham?** 🔥