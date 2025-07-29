# SF Transit Tracker - Current TODO

## 🚨 CRITICAL: API Rate Limiting Fixes (Active Sprint)

### Context
Production app is hitting 511.org API rate limits (60 requests/hour). Currently making 480 requests/hour!
- 4 agency APIs (SF, GG, AC, RG) × every 30 seconds = 8 requests/minute
- Multiple instances running (local dev + production)
- Health checks adding extra API calls

### Fix Strategy

#### FIX #1 (CRITICAL): Increase Update Interval ⏱️
- [ ] File: `backend/services/background_updater.py`
- [ ] Change: `update_interval: int = 30` → `update_interval: int = 300` (5 minutes)
- [ ] Math: 4 APIs × 12 cycles/hour = 48 requests/hour ✅ (under 60 limit)
- [ ] Impact: Transit data updates every 5 minutes instead of 30 seconds

#### FIX #3 (CRITICAL): API-Independent Health Checks 🏥
- [ ] Create `/api/ping` endpoint that just returns 200 OK (no API calls)
- [ ] Update Dockerfile: Change health check to use `/api/ping`
- [ ] Update fly.toml: Change health check path to `/api/ping`
- [ ] Keep `/api/health` for monitoring but make it rate-limit aware

#### FIX #2 (IMPORTANT): Rate Limit Detection and Backoff 🛑
- [ ] File: `backend/services/transit_fetcher.py`
- [ ] Detect 429 response codes
- [ ] Implement exponential backoff
- [ ] Add circuit breaker logic
- [ ] Show "Rate Limited" status instead of "Connecting"

#### FIX #4 (DEVELOPMENT): Mock API Mode 🧪
- [ ] Add `MOCK_APIS=true` environment variable
- [ ] Return fake vehicle data when enabled
- [ ] Create `run_local.sh` script that sets this automatically
- [ ] Allow unlimited local testing without API quota

#### FIX #5 (OPTIMIZATIONS): Additional Improvements 🚀
- [ ] **5A**: Agency rotation - call 1 agency per cycle instead of all 4
- [ ] **5B**: Smart caching - cache API responses for 2-3 minutes
- [ ] **5C**: Monitoring - add API quota tracking in logs

## ✅ Completed Tasks

### Phase 1: Backend Refactoring ✓
- [x] Created backend directory structure
- [x] Extracted models to `backend/models/`
- [x] Extracted services to `backend/services/`
- [x] Split API routes to `backend/api/`
- [x] Cleaned up app.py (<200 lines)
- [x] Tested functionality preservation

### Phase 2: Frontend Refactoring ✓
- [x] Extracted CSS into modular files
- [x] Created theme system (TRON/Default)
- [x] Split JavaScript into TransitTracker class
- [x] Created clean index_clean.html template
- [x] Preserved all animations and functionality

### Deployment ✓
- [x] Created production-ready Dockerfile with multi-stage build
- [x] Cleaned up repository and pushed to GitHub (private repo)
- [x] Configured Fly.io application and fly.toml
- [x] Set production environment variables and secrets
- [x] Deployed to Fly.io (https://sf-transit-tracker.fly.dev)

### Mobile UX Improvements ✓
- [x] Added mobile responsive design
- [x] Implemented collapsible filter panel with hamburger menu
- [x] Created unified status panel (replaced dual panels)
- [x] Added route-aware count to status display

## 📋 Pending Tasks

### Phase 3: Testing Implementation
- [ ] Create /test/frontend endpoint with monitoring dashboard
- [ ] Add real-time performance metrics display (FPS, memory, vehicle count)
- [ ] Implement vehicle movement verification tools
- [ ] Run comprehensive manual testing checklist

### Bug Fixes & Investigation
- [ ] Investigate README file duplication issue (user reports seeing README.md and READ_ME.md)

### Deployment Monitoring
- [ ] Configure production monitoring and alerts
- [ ] Set up scaling policies
- [ ] Implement proper health check endpoints

## 🎯 Priority Order
1. **FIX #1**: Increase update interval (immediate relief)
2. **FIX #3**: Fix health checks (stop extra API calls)
3. **FIX #2**: Add rate limit handling (graceful degradation)
4. **FIX #4**: Add mock mode (better developer experience)
5. **FIX #5**: Optimizations (long-term sustainability)

## 📝 Notes
- API rate limit is the #1 blocker - fix this first!
- Health checks are burning quota unnecessarily
- Consider reaching out to 511.org for higher rate limits
- Mock mode will prevent future developer quota issues

---

*Last Updated: July 28 2025*
*Focus: Fix API rate limiting to restore functionality*