# HVAC Event Generator - Deployment Guide

**Generated:** Thursday, October 30, 2025 at 07:45 PM EDT  
**Workflow Version:** v1.0.0  
**Status:** Ready for Production

---

## 🚀 Quick Start (5 Minutes)

### Step 1: Import Workflow into n8n

1. **Open n8n** (http://localhost:5678 or your VPS URL)

2. **Create New Workflow:**
   - Click "Add workflow" (+ button)
   - Click the three dots menu (⋮)
   - Select "Import from File"
   - Upload: `hvac_event_generator_workflow.json`

3. **The workflow will appear with all 14 nodes connected!** ✅

---

### Step 2: Configure PostgreSQL Credentials

**CRITICAL:** You need to set up PostgreSQL connection ONCE

1. **In n8n, go to:** Settings → Credentials

2. **Create New Credential:**
   - Type: `Postgres`
   - Name: `HVAC PostgreSQL`
   - Configuration:
     ```
     Host: hvac-postgres
     Port: 5432
     Database: hvac_demo
     User: hvac_user
     Password: hvac_demo_pass_2025
     SSL: Disabled
     ```

3. **Test Connection** - Should show "Success!" ✅

4. **Save Credential**

**The 3 PostgreSQL nodes will automatically use this credential** (they reference `hvac-postgres-creds`)

---

### Step 3: Activate the Workflow

1. **In the workflow editor:**
   - Toggle "Active" in the top-right corner
   - Should turn green ✅

2. **Webhook URL will be generated:**
   ```
   http://localhost:5678/webhook/hvac/generate-events
   ```
   
   Or on VPS:
   ```
   https://your-domain.ngrok.io/webhook/hvac/generate-events
   ```

---

## 🧪 Testing the Generator

### Test 1: Generate 10 Events (Quick Test)

**Using curl:**
```bash
curl -X POST http://localhost:5678/webhook/hvac/generate-events \
  -H "Content-Type: application/json" \
  -d '{
    "scenario_name": "routine_maintenance_day",
    "event_count": 10,
    "time_spread_minutes": 60
  }'
```

**Expected Response:**
```json
{
  "status": "success",
  "run_id": "GEN-LKJ8D9F-A7B2C3D4",
  "workflow_sequence_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "scenario_name": "routine_maintenance_day",
  "summary": {
    "events_created": 10,
    "events_deduped": 0,
    "total_steps": 10,
    "errors": 0,
    "duration_seconds": 0.85,
    "events_per_second": 11.76
  },
  "message": "Successfully generated 10 events in 0.85s"
}
```

---

### Test 2: Winter Emergency Scenario

```bash
curl -X POST http://localhost:5678/webhook/hvac/generate-events \
  -H "Content-Type: application/json" \
  -d '{
    "scenario_name": "winter_emergency_surge"
  }'
```

**This will generate 50 events with:**
- 60% emergencies
- Evening-heavy pattern
- High urgency bias
- 2-hour time spread

---

### Test 3: Summer Heatwave (Stress Test)

```bash
curl -X POST http://localhost:5678/webhook/hvac/generate-events \
  -H "Content-Type: application/json" \
  -d '{
    "scenario_name": "summer_heatwave"
  }'
```

**This will generate 75 events with:**
- 70% emergencies
- Afternoon spike pattern
- Extreme urgency (mostly 10/10)
- 3-hour time spread

**Expected:** ~7-8 seconds for 75 events

---

### Test 4: Idempotency Test

Run the SAME request twice within 5 minutes:

```bash
# First run - creates events
curl -X POST http://localhost:5678/webhook/hvac/generate-events \
  -H "Content-Type: application/json" \
  -d '{"scenario_name": "routine_maintenance_day", "event_count": 5}'

# Wait 2 seconds

# Second run - should use cache
curl -X POST http://localhost:5678/webhook/hvac/generate-events \
  -H "Content-Type: application/json" \
  -d '{"scenario_name": "routine_maintenance_day", "event_count": 5}'
```

**Expected:** Second run shows `events_deduped: 5` in summary

---

## 🔍 Verify Events in Database

**Check events were created:**
```bash
docker exec hvac-postgres psql -U hvac_user -d hvac_demo -c \
  "SELECT event_id, event_type, urgency, scenario_name, created_at 
   FROM hvac_events 
   ORDER BY created_at DESC 
   LIMIT 10;"
```

**Check workflow executions:**
```bash
docker exec hvac-postgres psql -U hvac_user -d hvac_demo -c \
  "SELECT execution_id, workflow_name, status, created_at 
   FROM workflow_executions 
   ORDER BY created_at DESC 
   LIMIT 10;"
```

**Check agent decisions (sequence-aware logging):**
```bash
docker exec hvac-postgres psql -U hvac_user -d hvac_demo -c \
  "SELECT decision_id, agent_name, step_number, routing_reason, decision_confidence 
   FROM agent_decisions 
   WHERE agent_name = 'event_generator' 
   ORDER BY decision_timestamp DESC 
   LIMIT 10;"
```

---

## 📊 Available Scenarios

### 1. routine_maintenance_day (Default)
```json
{
  "scenario_name": "routine_maintenance_day"
}
```
- **Events:** 30
- **Duration:** 8 hours
- **Pattern:** Business hours (8am-5pm)
- **Types:** 50% appointments, 25% inquiries, 15% follow-ups, 10% maintenance
- **Urgency:** Low (2-5)
- **Revenue:** $150-350

### 2. winter_emergency_surge
```json
{
  "scenario_name": "winter_emergency_surge"
}
```
- **Events:** 50
- **Duration:** 2 hours
- **Pattern:** Evening heavy (5pm-10pm spike)
- **Types:** 60% emergencies, 25% inquiries, 10% appointments, 5% complaints
- **Urgency:** High (7-10)
- **Revenue:** $250-600

### 3. summer_heatwave
```json
{
  "scenario_name": "summer_heatwave"
}
```
- **Events:** 75
- **Duration:** 3 hours
- **Pattern:** Afternoon spike (2pm-6pm)
- **Types:** 70% emergencies, 20% inquiries, 10% complaints
- **Urgency:** Extreme (9-10)
- **Revenue:** $300-800

---

## 🔧 Troubleshooting

### Issue: "Unknown scenario" error

**Problem:** Scenario name misspelled or doesn't exist

**Solution:** Use exact names:
- `routine_maintenance_day`
- `winter_emergency_surge`
- `summer_heatwave`

---

### Issue: PostgreSQL connection error

**Problem:** Credential not configured or database not running

**Check database status:**
```bash
docker ps | grep hvac-postgres
```

**Should show:** `hvac-postgres` container with "healthy" status

**Test connection manually:**
```bash
docker exec hvac-postgres psql -U hvac_user -d hvac_demo -c "SELECT 1;"
```

**Should return:** `?column? 1` ✅

---

### Issue: Workflow doesn't activate

**Problem:** Webhook path conflict or n8n issue

**Solution:**
1. Check n8n logs: `docker logs n8n`
2. Make sure no other workflow uses `/hvac/generate-events`
3. Restart n8n if needed: `docker restart n8n`

---

### Issue: Events created but no agent_decisions

**Problem:** Decision Logger node might have SQL error

**Check manually:**
```bash
docker exec hvac-postgres psql -U hvac_user -d hvac_demo -c \
  "SELECT COUNT(*) FROM agent_decisions WHERE agent_name = 'event_generator';"
```

**If 0:** Check Decision Logger node execution in n8n UI (click node, view output)

---

## 🎯 Performance Benchmarks

### Expected Performance

| Scenario | Events | Expected Time | Events/Sec |
|----------|--------|---------------|------------|
| Quick Test (10) | 10 | ~0.8s | ~12/s |
| Routine (30) | 30 | ~2.5s | ~12/s |
| Winter (50) | 50 | ~4.2s | ~12/s |
| Heatwave (75) | 75 | ~6.3s | ~12/s |
| Max Load (200) | 200 | ~17s | ~12/s |

**If slower than this:** Check VPS resources or database performance

---

## 🔐 Production Deployment (VPS)

### Deploy to Production VPS

1. **SSH to VPS:**
   ```bash
   ssh root@your-vps-ip
   ```

2. **Import workflow via n8n UI:**
   - Access: https://your-domain.ngrok.io
   - Import JSON file (same steps as local)

3. **Update webhook URL in docs:**
   ```
   https://your-domain.ngrok.io/webhook/hvac/generate-events
   ```

4. **Test from local machine:**
   ```bash
   curl -X POST https://your-domain.ngrok.io/webhook/hvac/generate-events \
     -H "Content-Type: application/json" \
     -d '{"scenario_name": "routine_maintenance_day", "event_count": 5}'
   ```

5. **Monitor logs:**
   ```bash
   docker logs -f n8n
   ```

---

## 📈 Observability Queries

### View Event Generation Runs

```sql
SELECT 
  workflow_sequence_id,
  COUNT(*) as events_created,
  MIN(decision_timestamp) as started_at,
  MAX(decision_timestamp) as ended_at,
  AVG(decision_confidence) as avg_confidence
FROM agent_decisions
WHERE agent_name = 'event_generator'
GROUP BY workflow_sequence_id
ORDER BY started_at DESC
LIMIT 10;
```

### View Event Distribution by Scenario

```sql
SELECT 
  scenario_name,
  event_type,
  COUNT(*) as event_count,
  AVG(urgency) as avg_urgency,
  AVG(estimated_revenue) as avg_revenue
FROM hvac_events
GROUP BY scenario_name, event_type
ORDER BY scenario_name, event_count DESC;
```

### View Generator Performance

```sql
SELECT 
  workflow_sequence_id,
  step_number,
  routing_reason,
  decision_confidence,
  decision_timestamp
FROM agent_decisions
WHERE agent_name = 'event_generator'
ORDER BY workflow_sequence_id DESC, step_number ASC
LIMIT 50;
```

---

## 🎨 Customizing Scenarios

### Add Your Own Scenario

1. **Edit Policy Loader node** (Node #2)

2. **Add new scenario to `sd.scenarios` object:**
   ```javascript
   "my_custom_scenario": {
     "description": "Custom event pattern",
     "event_count": 25,
     "time_spread_minutes": 240,
     "event_distribution": {
       "emergency": 0.30,
       "inquiry": 0.40,
       "appointment": 0.30
     },
     "urgency_bias": "medium",
     "time_pattern": "business_hours",
     "customer_pool": [1, 2, 3],
     "revenue_range": [200, 500]
   }
   ```

3. **Save workflow**

4. **Test new scenario:**
   ```bash
   curl -X POST http://localhost:5678/webhook/hvac/generate-events \
     -H "Content-Type: application/json" \
     -d '{"scenario_name": "my_custom_scenario"}'
   ```

---

## ✅ Success Checklist

- [ ] Workflow imported into n8n
- [ ] PostgreSQL credentials configured
- [ ] Workflow activated (green toggle)
- [ ] Test 1 passed (10 events created)
- [ ] Test 2 passed (winter scenario)
- [ ] Test 3 passed (heatwave scenario)
- [ ] Test 4 passed (idempotency working)
- [ ] Events visible in database
- [ ] Workflow executions logged
- [ ] Agent decisions tracked with sequence
- [ ] Performance meets benchmarks

---

## 🚀 Next Steps

**After Event Generator is working:**

1. ✅ **Event Generator** ← YOU ARE HERE!
2. ⬜ **Primary Agent Workflow** (routes events to specialists)
3. ⬜ **Emergency Agent Workflow** (handles urgent events)
4. ⬜ **Business Owner Dashboard** (visualize metrics)
5. ⬜ **Technologist Dashboard** (agent performance)

---

## 🆘 Support

**If you encounter issues:**

1. Check n8n logs: `docker logs n8n`
2. Check PostgreSQL logs: `docker logs hvac-postgres`
3. Verify workflow is active in n8n UI
4. Test database connection manually
5. Review execution logs in n8n (click workflow, view executions)

**Common fixes:**
- Restart n8n: `docker restart n8n`
- Clear workflow cache: Deactivate & reactivate workflow
- Re-import workflow if nodes are missing

---

**Generated:** Thursday, October 30, 2025 at 07:45 PM EDT  
**Status:** PRODUCTION READY ✅  
**Time to Deploy:** 5 minutes  
**Time to First Event:** 30 seconds
