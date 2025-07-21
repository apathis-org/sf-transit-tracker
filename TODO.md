# SF Transit Tracker - Current TODO

## 🔥 Active Sprint

### Phase 1: Backend Refactoring (In Progress)
- [ ] **Create backend directory structure**
  - [ ] `mkdir -p backend/{models,services,api,utils}`
  - [ ] Create `__init__.py` files for Python packages

- [ ] **Extract models** → `backend/models/`
  - [ ] Move `Vehicle` dataclass → `backend/models/vehicle.py`
  - [ ] Extract GTFS-related classes → `backend/models/gtfs.py`
  - [ ] Update imports throughout codebase

- [ ] **Extract services** → `backend/services/`
  - [ ] Move `TransitDataFetcher` → `backend/services/transit_fetcher.py`
  - [ ] Move `GTFSProcessor` → `backend/services/gtfs_processor.py`
  - [ ] Extract background update logic → `backend/services/background_updater.py`

- [ ] **Split API routes** → `backend/api/`
  - [ ] Main API routes → `backend/api/routes.py`
  - [ ] Test endpoints → `backend/api/test_routes.py`
  - [ ] WebSocket handlers → `backend/api/websocket.py`

- [ ] **Clean up app.py**
  - [ ] Keep only Flask app initialization and route imports
  - [ ] Remove all business logic
  - [ ] Target: <100 lines

- [ ] **Test functionality preservation**
  - [ ] All API endpoints respond correctly
  - [ ] WebSocket connections work
  - [ ] Vehicle data updates properly
  - [ ] No performance regressions

## ⏳ Next Phase

### Phase 2: Frontend Refactoring (Queued)
- [ ] Create `frontend/` directory structure
- [ ] Extract CSS from index.html into modular files
- [ ] Split JavaScript into focused classes
- [ ] Create clean index.html template
- [ ] Test UI functionality preservation

### Phase 3: Testing Implementation (Queued)
- [ ] Set up Playwright testing environment
- [ ] Create frontend testing dashboard
- [ ] Implement automated vehicle movement tests
- [ ] Add performance monitoring

## 📋 Definition of Done (Phase 1)
- [ ] ✅ Code split into logical modules with single responsibilities
- [ ] ✅ All original functionality preserved (no breaking changes)
- [ ] ✅ Tests pass (existing + new verification tests)
- [ ] ✅ Performance maintained (no slowdowns)
- [ ] ✅ Documentation updated
- [ ] ✅ Team can easily understand new structure

## 🚨 Critical Requirements
- **Zero Breaking Changes**: All existing functionality must work
- **Performance Maintained**: No degradation in speed or responsiveness  
- **WebSocket Preserved**: Real-time updates continue working
- **API Compatibility**: All endpoints respond identically

## 📝 Notes
- Start with models extraction (lowest risk)
- Test each extraction step before proceeding
- Keep git commits small and focused
- Backup working version before major changes

---

*Focus: One phase at a time, test continuously, preserve all functionality*