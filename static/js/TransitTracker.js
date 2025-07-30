/**
 * SF Transit Tracker - Main application class
 * Coordinates map, vehicles, filters, and real-time updates
 * 
 * Note: Uses Socket.IO for real-time communication, which automatically
 * falls back to HTTP polling when WebSocket libraries are unavailable.
 * This provides reliable connection tracking for our API optimization.
 */

class TransitTracker {
    constructor() {
        this.map = null;
        this.vehicles = new Map();
        this.markers = new Map();
        this.socket = null;
        this.vehicleCounts = {};
        this.routeManager = null;

        // Animation system
        this.vehicleStates = new Map(); // Store animation state for each vehicle
        this.animationFrame = null;
        this.lastUpdateTime = Date.now();

        // Expanded filter mapping including all Bay Area Regional agencies
        this.filters = {
            // Existing filters (keep unchanged)
            'muni-bus': { agency: 'SFMTA', type: 'muni-bus' },
            'light-rail': { agency: 'SFMTA', type: 'light-rail' },
            'cable-car': { agency: 'SFMTA', type: 'cable-car' },
            'bart-train': { agency: 'BART', type: 'bart-train' },
            'gg-bus': { agency: 'Golden Gate', type: 'bus' },
            'ferry': { agency: 'Golden Gate', type: 'ferry' },
            'ac-bus': { agency: 'AC Transit', type: 'bus' },
            
            // New Bay Area Regional filters
            'caltrain': { agency: 'Caltrain', type: 'train' },
            'capitol-corridor': { agency: 'Capitol Corridor', type: 'train' },
            'ace-train': { agency: 'Altamont Corridor Express', type: 'train' },
            'smart-rail': { agency: 'SMART', type: 'train' },
            'sf-bay-ferry': { agency: 'SF Bay Ferry', type: 'ferry' },
            'vta': { agency: 'VTA', type: 'bus' },
            'samtrans': { agency: 'SamTrans', type: 'bus' },
            'tri-delta': { agency: 'Tri Delta Transit', type: 'bus' },
            'county-connection': { agency: 'County Connection', type: 'bus' },
            'marin-transit': { agency: 'Marin Transit', type: 'bus' },
            'dumbarton-express': { agency: 'Dumbarton Express', type: 'bus' },
            'emery-go-round': { agency: 'Emery Go-Round', type: 'bus' },
            'fs-transit': { agency: 'FS Transit', type: 'bus' },
            'mv-transportation': { agency: 'MV Transportation', type: 'bus' },
            'presidio-go': { agency: 'Presidio Go', type: 'bus' },
            'sonoma-county': { agency: 'Sonoma County Transit', type: 'bus' },
            'sonoma-county-sr': { agency: 'Sonoma County Transit (SR)', type: 'bus' },
            'soltrans': { agency: 'SolTrans', type: 'bus' },
            'union-city': { agency: 'Union City Transit', type: 'bus' },
            'vacaville': { agency: 'Vacaville City Coach', type: 'bus' },
            'vine-transit': { agency: 'Vine Transit', type: 'bus' },
            'westcat': { agency: 'WestCAT', type: 'bus' },
            'wheels': { agency: 'Wheels', type: 'bus' }
        };

        this.init();
    }

    async init() {
        // Initialize map
        this.map = L.map('map').setView([37.7749, -122.4194], 12);
        // Load dark mode map tiles with visible street names and grid
        L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
            subdomains: 'abcd',
            maxZoom: 20
        }).addTo(this.map);
        
        // Add bright labels overlay for readable street names
        L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_only_labels/{z}/{x}/{y}{r}.png', {
            subdomains: 'abcd',
            maxZoom: 20,
            pane: 'overlayPane'
        }).addTo(this.map);

        // Initialize components
        await this.initializeRouteManager();
        this.setupFilters();
        this.setupFilterToggle();
        this.setupBayAreaToggle();
        this.connectSocket();
        this.startAnimationLoop();
    }

    async initializeRouteManager() {
        // Initialize route-aware animation
        this.routeManager = new RouteManager();
        const success = await this.routeManager.initialize();
        
        // Update route status if element exists (for backward compatibility)
        const routeStatusEl = document.getElementById('route-status');
        if (routeStatusEl) {
            routeStatusEl.textContent = 
                success ? `Routes: ${this.routeManager.routes.size} loaded ✨` : 'Routes: Failed to load';
        }

        const routesLoadedEl = document.getElementById('routes-loaded');
        if (routesLoadedEl) {
            routesLoadedEl.textContent = this.routeManager.routes.size;
        }
        
        console.log(`RouteManager initialized: ${success ? 'Success' : 'Failed'}, ${this.routeManager.routes.size} routes loaded`);
    }

    setupFilters() {
        Object.keys(this.filters).forEach(filterId => {
            const checkbox = document.getElementById(`filter-${filterId}`);
            if (checkbox) {
                checkbox.addEventListener('change', () => {
                    this.updateVisibleVehicles();
                });
            }
        });
    }

    setupFilterToggle() {
        const toggleBtn = document.getElementById('filter-toggle');
        const closeBtn = document.getElementById('filter-close');
        const filterPanel = document.getElementById('filter-panel');

        if (toggleBtn && filterPanel) {
            toggleBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                
                const isCurrentlyShown = filterPanel.classList.contains('show');
                
                if (isCurrentlyShown) {
                    toggleBtn.classList.remove('active');
                    filterPanel.classList.remove('show');
                } else {
                    toggleBtn.classList.add('active');
                    filterPanel.classList.add('show');
                }
            });
        } else {
            console.error('Toggle button or filter panel not found!');
        }

        if (closeBtn && filterPanel) {
            closeBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                toggleBtn.classList.remove('active');
                filterPanel.classList.remove('show');
            });
        }

        // Close panel when clicking outside (with delay to prevent immediate closing)
        setTimeout(() => {
            document.addEventListener('click', (e) => {
                if (filterPanel && toggleBtn && !filterPanel.contains(e.target) && !toggleBtn.contains(e.target)) {
                    if (filterPanel.classList.contains('show')) {
                        toggleBtn.classList.remove('active');
                        filterPanel.classList.remove('show');
                    }
                }
            });
        }, 100);
    }

    setupBayAreaToggle() {
        const bayAreaToggle = document.getElementById('bay-area-toggle');
        const bayAreaContent = document.getElementById('bay-area-content');
        const bayAreaSection = document.querySelector('.bay-area-section');

        if (bayAreaToggle && bayAreaContent && bayAreaSection) {
            bayAreaToggle.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                
                const isCurrentlyExpanded = bayAreaSection.classList.contains('expanded');
                
                if (isCurrentlyExpanded) {
                    // Collapse
                    bayAreaSection.classList.remove('expanded');
                    bayAreaContent.style.display = 'none';
                } else {
                    // Expand
                    bayAreaSection.classList.add('expanded');
                    bayAreaContent.style.display = 'block';
                }
            });
        } else {
            console.error('Bay Area toggle elements not found!');
        }
    }

    connectSocket() {
        this.updateStatus('connecting');

        // Initialize Socket.IO client (will use HTTP polling, not WebSockets)
        // This provides reliable real-time communication and connection tracking
        this.socket = io();

        this.socket.on('connect', () => {
            this.updateStatus('connected');
        });

        this.socket.on('bulk_update', (data) => {
            this.handleVehicleUpdate(data);
        });

        this.socket.on('disconnect', () => {
            console.log('Socket.IO disconnected');
            this.updateStatus('error');
        });

        this.socket.on('connect_error', (error) => {
            console.error('Socket.IO connection error:', error);
            this.updateStatus('error');
        });

        // Fallback to pure HTTP polling if Socket.IO fails completely
        setTimeout(() => {
            if (!this.socket || !this.socket.connected) {
                console.log('Socket.IO failed, falling back to manual HTTP polling');
                this.fallbackToHTTP();
            }
        }, 5000);
    }

    async fallbackToHTTP() {
        console.log('Starting manual HTTP polling fallback (Socket.IO unavailable)');
        this.updateStatus('connected');
        
        // Immediately fetch data
        this.fetchVehicleData();
        
        // Set up manual polling (less efficient than Socket.IO polling)
        setInterval(() => {
            this.fetchVehicleData();
        }, 30000);
    }

    async fetchVehicleData() {
        try {
            console.log('Fetching vehicle data via HTTP...');
            const response = await fetch('/api/vehicles');
            const data = await response.json();
            
            if (data.vehicles && data.vehicles.length > 0) {
                console.log(`Received ${data.vehicles.length} vehicles`);
                this.handleVehicleUpdate({ vehicles: data.vehicles });
            } else {
                console.log('No vehicles in response');
            }
        } catch (error) {
            console.error('HTTP fetch failed:', error);
            this.updateStatus('error');
        }
    }

    handleVehicleUpdate(data) {
        if (!data.vehicles || !Array.isArray(data.vehicles)) {
            console.warn('Invalid vehicle data received');
            return;
        }

        // Store current time for animation calculations
        const updateTime = Date.now();
        
        // Clear vehicle counts for fresh calculation
        this.vehicleCounts = {};

        // Update vehicles
        const currentVehicleIds = new Set();
        
        data.vehicles.forEach(vehicleData => {
            if (!vehicleData.lat || !vehicleData.lng) return;
            
            // Note: RG vehicles are now included as Bay Area Regional agencies

            currentVehicleIds.add(vehicleData.id);
            
            // Update animation state for each vehicle
            this.updateVehicleAnimationState(vehicleData, updateTime);
            
            // Count vehicles by type
            const vehicleType = this.getVehicleType(vehicleData);
            if (vehicleType) { // Only count if vehicle has a valid filter type
                this.vehicleCounts[vehicleType] = (this.vehicleCounts[vehicleType] || 0) + 1;
            }

            // Store vehicle data
            this.vehicles.set(vehicleData.id, vehicleData);
        });
        
        // Update the last update time for animation
        this.lastUpdateTime = updateTime;

        // Remove vehicles that are no longer present
        this.vehicles.forEach((vehicle, vehicleId) => {
            if (!currentVehicleIds.has(vehicleId)) {
                this.removeVehicle(vehicleId);
            }
        });

        this.updateFilterCounts();
        this.updateStats();
        this.updateVisibleVehicles(); // Make sure vehicles are shown based on filter state
        
        // Update last update time (use defensive check for element existence)
        const updateTimeEl = document.getElementById('update-time') || document.getElementById('last-update');
        if (updateTimeEl) {
            updateTimeEl.textContent = 
                `Last update: ${new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'})}`;
        }
    }

    getVehicleType(vehicleData) {
        // Return the filter key that matches this vehicle
        // This must match the filter IDs in the HTML and expanded for Bay Area agencies
        
        // BART
        if (vehicleData.agency === 'BART') return 'bart-train';
        
        // Golden Gate
        if (vehicleData.agency === 'Golden Gate' && vehicleData.type === 'ferry') return 'ferry';
        if (vehicleData.agency === 'Golden Gate' && vehicleData.type === 'bus') return 'gg-bus';
        
        // AC Transit  
        if (vehicleData.agency === 'AC Transit' && vehicleData.type === 'bus') return 'ac-bus';
        
        // SFMTA vehicles
        if (vehicleData.agency === 'SFMTA' && vehicleData.type === 'light-rail') return 'light-rail';
        if (vehicleData.agency === 'SFMTA' && vehicleData.type === 'cable-car') return 'cable-car';
        if (vehicleData.agency === 'SFMTA' && vehicleData.type === 'muni-bus') return 'muni-bus';
        
        // Bay Area Regional agencies - Train services
        if (vehicleData.agency === 'Caltrain') return 'caltrain';
        if (vehicleData.agency === 'Capitol Corridor') return 'capitol-corridor';
        if (vehicleData.agency === 'Altamont Corridor Express') return 'ace-train';
        if (vehicleData.agency === 'SMART') return 'smart-rail';
        
        // Bay Area Regional agencies - Ferry services
        if (vehicleData.agency === 'SF Bay Ferry') return 'sf-bay-ferry';
        
        // Bay Area Regional agencies - Bus services
        if (vehicleData.agency === 'VTA') return 'vta';
        if (vehicleData.agency === 'SamTrans') return 'samtrans';
        if (vehicleData.agency === 'Tri Delta Transit') return 'tri-delta';
        if (vehicleData.agency === 'County Connection') return 'county-connection';
        if (vehicleData.agency === 'Marin Transit') return 'marin-transit';
        if (vehicleData.agency === 'Dumbarton Express') return 'dumbarton-express';
        if (vehicleData.agency === 'Emery Go-Round') return 'emery-go-round';
        if (vehicleData.agency === 'FS Transit') return 'fs-transit';
        if (vehicleData.agency === 'MV Transportation') return 'mv-transportation';
        if (vehicleData.agency === 'Presidio Go') return 'presidio-go';
        if (vehicleData.agency === 'Sonoma County Transit') return 'sonoma-county';
        if (vehicleData.agency === 'Sonoma County Transit (SR)') return 'sonoma-county-sr';
        if (vehicleData.agency === 'SolTrans') return 'soltrans';
        if (vehicleData.agency === 'Union City Transit') return 'union-city';
        if (vehicleData.agency === 'Vacaville City Coach') return 'vacaville';
        if (vehicleData.agency === 'Vine Transit') return 'vine-transit';
        if (vehicleData.agency === 'WestCAT') return 'westcat';
        if (vehicleData.agency === 'Wheels') return 'wheels';
        
        // Default fallback
        return vehicleData.type || 'muni-bus';
    }

    getVehicleCSSClass(vehicleData) {
        // Return the CSS class for styling the vehicle icon
        // This should match the CSS classes in default-theme.css
        
        // SFMTA vehicles FIRST (most common)
        if (vehicleData.agency === 'SFMTA') {
            if (vehicleData.type === 'light-rail') return 'light-rail';
            if (vehicleData.type === 'cable-car') return 'cable-car';
            if (vehicleData.type === 'muni-bus') return 'muni-bus';
            // Fallback for any other SFMTA vehicle
            return 'muni-bus';
        }
        
        // BART
        if (vehicleData.agency === 'BART') return 'bart-train';
        
        // Golden Gate
        if (vehicleData.agency === 'Golden Gate' && vehicleData.type === 'ferry') return 'ferry';
        if (vehicleData.agency === 'Golden Gate' && vehicleData.type === 'bus') return 'bus';
        
        // AC Transit
        if (vehicleData.agency === 'AC Transit' && vehicleData.type === 'bus') return 'bus';
        
        // Bay Area Regional - Train services (use train CSS class)
        if (vehicleData.agency === 'Caltrain') return 'train';
        if (vehicleData.agency === 'Capitol Corridor') return 'train';
        if (vehicleData.agency === 'Altamont Corridor Express') return 'train';
        if (vehicleData.agency === 'SMART') return 'train';
        
        // Bay Area Regional - Ferry services 
        if (vehicleData.agency === 'SF Bay Ferry') return 'regional-ferry';
        
        // Bay Area Regional - Express bus services
        if (vehicleData.type === 'express-bus') return 'express-bus';
        
        // Bay Area Regional - Regular bus services (use generic bus class)
        if (vehicleData.agency === 'VTA') return 'bus';
        if (vehicleData.agency === 'SamTrans') return 'bus';
        if (vehicleData.agency === 'Tri Delta Transit') return 'bus';
        if (vehicleData.agency === 'County Connection') return 'bus';
        if (vehicleData.agency === 'Marin Transit') return 'bus';
        if (vehicleData.agency === 'Dumbarton Express') return 'bus';
        if (vehicleData.agency === 'Emery Go-Round') return 'bus';
        if (vehicleData.agency === 'FS Transit') return 'bus';
        if (vehicleData.agency === 'MV Transportation') return 'bus';
        if (vehicleData.agency === 'Presidio Go') return 'bus';
        if (vehicleData.agency === 'Sonoma County Transit') return 'bus';
        if (vehicleData.agency === 'Sonoma County Transit (SR)') return 'bus';
        if (vehicleData.agency === 'SolTrans') return 'bus';
        if (vehicleData.agency === 'Union City Transit') return 'bus';
        if (vehicleData.agency === 'Vacaville City Coach') return 'bus';
        if (vehicleData.agency === 'Vine Transit') return 'bus';
        if (vehicleData.agency === 'WestCAT') return 'bus';
        if (vehicleData.agency === 'Wheels') return 'bus';
        
        // Default fallback - use the vehicle's type directly
        return vehicleData.type || 'bus';
    }

    createVehicle(vehicleData) {
        const vehicleType = this.getVehicleType(vehicleData); // For filtering
        const cssClass = this.getVehicleCSSClass(vehicleData); // For styling
        
        // Debug logging
        console.log(`Creating vehicle: ${vehicleData.id}, Agency: ${vehicleData.agency}, Type: ${vehicleData.type}, Filter: ${vehicleType}, CSS Class: ${cssClass}, Route: ${vehicleData.route || 'NONE'}`);
        
        // Get animation state or use current position
        const state = this.vehicleStates.get(vehicleData.id);
        const position = state ? [state.currentPos.lat, state.currentPos.lng] : [vehicleData.lat, vehicleData.lng];
        
        const icon = L.divIcon({
            className: 'transit-icon',
            html: `<div class="transit-icon ${cssClass}">${vehicleData.route || '•'}</div>`,
            iconSize: [24, 24],
            iconAnchor: [12, 12]
        });

        const leafletMarker = L.marker(position, { icon })
            .bindPopup(this.createPopup(vehicleData))
            .addTo(this.map);

        this.markers.set(vehicleData.id, leafletMarker);
        
        // Set initial opacity for fade-in animation
        if (state && state.isNew) {
            leafletMarker.getElement().style.opacity = 0;
        }
    }

    updateVehicleAnimationState(vehicle, updateTime) {
        const vehicleId = vehicle.id;
        const existingState = this.vehicleStates.get(vehicleId);

        if (!existingState) {
            // New vehicle - create initial state with projected movement
            const initialProjectedPos = this.calculateProjectedPosition(
                { lat: vehicle.lat, lng: vehicle.lng },
                vehicle.speed || 0,
                vehicle.heading || 0,
                30 // 30 seconds of movement
            );
            
            this.vehicleStates.set(vehicleId, {
                id: vehicleId,
                startPos: { lat: vehicle.lat, lng: vehicle.lng },
                targetPos: initialProjectedPos, // Give it somewhere to move to immediately
                currentPos: { lat: vehicle.lat, lng: vehicle.lng },
                startSpeed: vehicle.speed || 0,
                targetSpeed: vehicle.speed || 0,
                currentSpeed: vehicle.speed || 0,
                startHeading: vehicle.heading || 0,
                targetHeading: vehicle.heading || 0,
                currentHeading: vehicle.heading || 0,
                animationStartTime: updateTime,
                isNew: true,
                lastIdleTime: updateTime
            });
        } else {
            // Existing vehicle - update animation target
            const timeSinceLastUpdate = (updateTime - this.lastUpdateTime) / 1000; // seconds

            // Calculate projected position based on current speed and heading
            const projectedPos = this.calculateProjectedPosition(
                { lat: vehicle.lat, lng: vehicle.lng },
                vehicle.speed || 0,
                vehicle.heading || 0,
                30 // 30 seconds until next update
            );

            // Update state for smooth transition
            existingState.startPos = { ...existingState.currentPos };
            existingState.targetPos = projectedPos;
            existingState.startSpeed = existingState.currentSpeed;
            existingState.targetSpeed = vehicle.speed || 0;
            existingState.startHeading = existingState.currentHeading;
            existingState.targetHeading = vehicle.heading || 0;
            existingState.animationStartTime = updateTime;
            existingState.isNew = false;
        }
    }

    calculateProjectedPosition(currentPos, speed, heading, timeSeconds) {
        if (!speed || speed < 1) {
            return currentPos; // Stationary vehicle
        }

        // Convert speed from mph to meters per second
        const metersPerSecond = speed * 0.44704;
        const distanceMeters = metersPerSecond * timeSeconds;

        // Convert heading to radians (heading is in degrees, 0 = North)
        const headingRadians = (heading - 90) * (Math.PI / 180);

        // Calculate position change in meters
        const deltaLat = (distanceMeters * Math.sin(headingRadians)) / 111320; // meters to degrees lat
        const deltaLng = (distanceMeters * Math.cos(headingRadians)) / (111320 * Math.cos(currentPos.lat * Math.PI / 180)); // meters to degrees lng

        return {
            lat: currentPos.lat + deltaLat,
            lng: currentPos.lng + deltaLng
        };
    }

    removeVehicle(vehicleId) {
        const marker = this.markers.get(vehicleId);
        if (marker) {
            this.map.removeLayer(marker);
            this.markers.delete(vehicleId);
        }
        this.vehicles.delete(vehicleId);
        this.vehicleStates.delete(vehicleId);
    }

    createPopup(vehicle) {
        return `
            <div style="font-size: 12px;">
                <strong>${vehicle.agency} ${vehicle.route || 'Vehicle'}</strong><br>
                Type: ${vehicle.type}<br>
                Speed: ${Math.round(vehicle.speed || 0)} mph<br>
                Updated: ${new Date(vehicle.last_update || Date.now()).toLocaleTimeString()}
            </div>
        `;
    }

    startAnimationLoop() {
        const animate = () => {
            this.updateVehicleAnimations();
            this.animationFrame = requestAnimationFrame(animate);
        };
        animate();
    }

    updateVehicleAnimations() {
        const currentTime = Date.now();
        const mapBounds = this.map.getBounds();

        this.vehicleStates.forEach((state, vehicleId) => {
            const marker = this.markers.get(vehicleId);
            if (!marker) return;

            // Check if vehicle is reasonably close to viewport (expanded bounds for better animation)
            const expandedBounds = mapBounds.pad(0.5); // Expand bounds by 50% to ensure smooth animation
            if (!expandedBounds.contains([state.currentPos.lat, state.currentPos.lng])) {
                return; // Skip animation for vehicles far from view
            }

            const timeSinceStart = (currentTime - state.animationStartTime) / 1000; // seconds
            const animationDuration = 35; // Extended to 35 seconds
            const progress = Math.min(timeSinceStart / animationDuration, 1);

            let newPos;

            // Use traditional straight-line animation for all vehicles
            newPos = this.calculateTraditionalPosition(state, timeSinceStart, animationDuration, progress);

            // Interpolate speed for smooth transitions (over 3 seconds)
            const speedTransitionDuration = 3;
            const speedProgress = Math.min(timeSinceStart / speedTransitionDuration, 1);
            const speedEaseProgress = 1 - Math.pow(1 - speedProgress, 2);
            state.currentSpeed = state.startSpeed + (state.targetSpeed - state.startSpeed) * speedEaseProgress;

            // Handle idle movement for stationary vehicles
            if (state.currentSpeed < 2) {
                const timeSinceIdle = (currentTime - state.lastIdleTime) / 1000;
                if (timeSinceIdle > 8) { // Idle movement every 8 seconds
                    const idleRadius = 0.00002; // ~2 meters
                    const randomAngle = Math.random() * 2 * Math.PI;
                    newPos.lat += Math.sin(randomAngle) * idleRadius;
                    newPos.lng += Math.cos(randomAngle) * idleRadius;
                    state.lastIdleTime = currentTime;
                }
            }

            // Update current position and heading
            state.currentPos = newPos;

            // Update marker position
            marker.setLatLng([newPos.lat, newPos.lng]);

            // Handle new vehicle fade-in
            if (state.isNew && timeSinceStart < 1) {
                const opacity = timeSinceStart; // Fade in over 1 second
                marker.getElement().style.opacity = opacity;
            } else if (state.isNew) {
                marker.getElement().style.opacity = 1;
                state.isNew = false;
            }
        });
    }

    calculateTraditionalPosition(state, timeSinceStart, animationDuration, progress) {
        if (progress < 1) {
            // Normal interpolation phase (0-35 seconds)
            const easeProgress = 1 - Math.pow(1 - progress, 3);
            return {
                lat: state.startPos.lat + (state.targetPos.lat - state.startPos.lat) * easeProgress,
                lng: state.startPos.lng + (state.targetPos.lng - state.startPos.lng) * easeProgress
            };
        } else {
            // Extended animation phase (35+ seconds) - Continue moving predictively
            const extraTime = timeSinceStart - animationDuration;
            const basePos = state.targetPos; // Start from target position

            // Calculate movement based on current speed and heading
            const speedMph = state.currentSpeed || 15; // Use current speed or default
            const heading = state.currentHeading || 0; // Use current heading

            // Convert speed to movement per second
            const metersPerSecond = speedMph * 0.44704; // mph to m/s
            const distanceMeters = metersPerSecond * extraTime;

            // Convert heading to radians (0° = North)
            const headingRadians = (heading - 90) * (Math.PI / 180);

            // Calculate position offset
            const deltaLat = (distanceMeters * Math.sin(headingRadians)) / 111320; // meters to degrees
            const deltaLng = (distanceMeters * Math.cos(headingRadians)) / (111320 * Math.cos(basePos.lat * Math.PI / 180));

            const newPos = {
                lat: basePos.lat + deltaLat,
                lng: basePos.lng + deltaLng
            };

            // Add slight randomization to prevent vehicles from moving in perfect straight lines
            const randomFactor = 0.00001 * Math.sin(extraTime * 0.5); // Small oscillation
            newPos.lat += randomFactor;
            newPos.lng += randomFactor * 0.5;

            return newPos;
        }
    }

    updateVisibleVehicles() {
        // First, handle existing markers
        this.markers.forEach((marker, vehicleId) => {
            const vehicle = this.vehicles.get(vehicleId);
            if (!vehicle) {
                // Vehicle no longer exists, remove marker
                this.map.removeLayer(marker);
                this.markers.delete(vehicleId);
                return;
            }

            const vehicleType = this.getVehicleType(vehicle);
            const checkbox = document.getElementById(`filter-${vehicleType}`);
            
            if (checkbox && checkbox.checked) {
                marker.addTo(this.map);
            } else {
                this.map.removeLayer(marker);
            }
        });
        
        // Then, create markers for vehicles that should be visible but don't have markers yet
        this.vehicles.forEach((vehicle, vehicleId) => {
            if (!this.markers.has(vehicleId)) {
                const vehicleType = this.getVehicleType(vehicle);
                const checkbox = document.getElementById(`filter-${vehicleType}`);
                
                if (checkbox && checkbox.checked) {
                    this.createVehicle(vehicle);
                }
            }
        });
    }

    updateFilterCounts() {
        Object.keys(this.filters).forEach(filterId => {
            const countEl = document.getElementById(`count-${filterId}`);
            if (countEl) {
                const count = this.vehicleCounts[filterId] || 0;
                countEl.textContent = count;
                countEl.className = `filter-count ${count > 0 ? 'active' : 'inactive'}`;
            }
        });
    }

    updateStats() {
        const totalVehicles = Array.from(this.vehicles.values()).length;
        const agencies = new Set();

        this.vehicles.forEach(v => {
            agencies.add(v.agency);
        });

        // Update unified status panel (defensive checks)
        const vehicleCountEl = document.getElementById('vehicle-count');
        if (vehicleCountEl) {
            vehicleCountEl.textContent = `${totalVehicles} vehicles`;
        }
        
        const agencyCountEl = document.getElementById('agency-count');
        if (agencyCountEl) {
            agencyCountEl.textContent = `${agencies.size} agencies`;
        }
        
        // Update routes count (get from route manager if available)
        const routesLoaded = this.routeManager ? Object.keys(this.routeManager.routes || {}).length : 0;
        
        // Count route-aware vehicles (vehicles that have route shape data)
        let routeAwareCount = 0;
        this.vehicles.forEach(vehicle => {
            if (vehicle.route && this.routeManager && this.routeManager.routes[vehicle.route]) {
                routeAwareCount++;
            }
        });
        
        const routesCountEl = document.getElementById('routes-count');
        if (routesCountEl) {
            routesCountEl.textContent = `${routesLoaded} routes (${routeAwareCount} route aware)`;
        }
        
        // Update timestamp (defensive check for element existence)
        const now = new Date();
        const timeString = now.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'});
        const lastUpdateEl = document.getElementById('last-update') || document.getElementById('update-time');
        if (lastUpdateEl) {
            lastUpdateEl.textContent = `Last update: ${timeString}`;
        }
    }

    updateStatus(status) {
        const statusEl = document.getElementById('status');
        const dot = statusEl.querySelector('.status-dot');
        const connectionText = document.getElementById('connection-text');

        switch(status) {
            case 'connected':
                dot.className = 'status-dot connected';
                connectionText.textContent = 'Connected';
                break;
            case 'connecting':
                dot.className = 'status-dot connecting';
                connectionText.textContent = 'Connecting...';
                break;
            case 'error':
                dot.className = 'status-dot disconnected';
                connectionText.textContent = 'Disconnected';
                break;
        }
    }
}