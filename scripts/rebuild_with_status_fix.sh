#!/bin/bash
# Docker Rebuild Script with Status Monitoring Fix

echo "🚀 Rebuilding PyWemo API with Status Monitoring Fix"
echo "=================================================="

# Stop current container
echo "🛑 Stopping current container..."
docker stop pywemo-fixed 2>/dev/null || true
docker rm pywemo-fixed 2>/dev/null || true

# Remove old image 
echo "🗑️ Removing old image..."
docker rmi pywemo-api-fixed 2>/dev/null || true

# Build new image
echo "🔨 Building new Docker image..."
docker build -t pywemo-api-fixed .

if [ $? -eq 0 ]; then
    echo "✅ Build successful!"
    
    # Run new container
    echo "🚀 Starting new container..."
    docker run -d --name pywemo-fixed -p 5000:5000 pywemo-api-fixed
    
    echo "⏰ Waiting for container to start..."
    sleep 5
    
    # Test if it's working
    echo "🧪 Testing API..."
    if curl -s http://localhost:5000/devices/status > /dev/null; then
        echo "✅ Container is running and API is responding!"
        echo ""
        echo "🌟 STATUS MONITORING SHOULD NOW WORK:"
        echo "   1. Open http://localhost:5000 in your browser"
        echo "   2. Click '🔄 Enable Auto-Refresh' button"
        echo "   3. Press physical buttons on WeMo devices"  
        echo "   4. Watch UI update automatically within 30 seconds"
        echo ""
        echo "🔍 Container status:"
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    else
        echo "❌ Container started but API is not responding"
        echo "📋 Container logs:"
        docker logs pywemo-fixed --tail 10
    fi
else
    echo "❌ Build failed!"
    exit 1
fi