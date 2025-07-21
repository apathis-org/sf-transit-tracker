/**
 * Route Manager - Phase 2A: Muni Light Rail Route-Aware Animation
 * Handles snapping vehicles to actual transit routes and animating along paths
 */

class RouteManager {
    constructor() {
        this.routes = new Map(); // Store route data
        this.debugMode = false; // Set to true for console logging
    }

    /**
     * Initialize route manager and fetch route data
     */
    async initialize() {
        try {
            console.log('🛤️ RouteManager: Fetching route data...');
            const response = await fetch('/api/routes');
            const data = await response.json();

            // Store routes in our map
            Object.entries(data.routes).forEach(([routeId, routeData]) => {
                this.routes.set(routeId, routeData);
            });

            console.log(`✅ RouteManager: Loaded ${this.routes.size} routes`);
            if (this.debugMode) {
                console.log('Available routes:', Array.from(this.routes.keys()));
            }

            return true;
        } catch (error) {
            console.error('❌ RouteManager: Failed to load routes:', error);
            this.enableRouteAnimation = false; // Disable if routes fail to load
            return false;
        }
    }

    /**
     * Check if route data is available for a vehicle (for future GTFS implementation)
     */
    isRouteAvailable(vehicle) {
        return this.routes.has(vehicle.route);
    }

    /**
     * Get route information for debugging or future use
     */
    getRouteInfo(routeId) {
        const route = this.routes.get(routeId);
        if (!route) return null;

        return {
            id: routeId,
            name: route.name,
            pointCount: route.shape ? route.shape.length : 0,
            bounds: this.calculateRouteBounds(route)
        };
    }

    /**
     * Enable debug mode for detailed logging
     */
    enableDebug() {
        this.debugMode = true;
        console.log('🐛 RouteManager: Debug mode enabled');
    }

    /**
     * Disable debug mode
     */
    disableDebug() {
        this.debugMode = false;
        console.log('🔇 RouteManager: Debug mode disabled');
    }
}

// Make RouteManager available globally
window.RouteManager = RouteManager;