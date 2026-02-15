# Frontend WebSocket Client - Deployment & Installation Guide

## Installation Instructions

### Prerequisites
- Node.js 14+ installed
- npm or yarn package manager
- React 18.2.0+
- Existing backend with WebSocket server running

### Step 1: Install Dependencies

```bash
cd frontend

# Install required packages (already in package.json)
npm install

# Optional: If packages not listed, install them
npm install react-dom@18.2.0 axios@1.6.0 react-router-dom@6.20.0
```

### Step 2: Configure Environment

Create `.env` file in frontend directory:

```env
# WebSocket URL (change based on environment)
REACT_APP_WS_URL=ws://localhost:8000/ws

# Debug mode (set to true for development)
REACT_APP_DEBUG_WEBSOCKET=false

# Optional: Backend API URL for HTTP requests
REACT_APP_API_URL=http://localhost:8000
```

### Development Environment (.env.development)
```env
REACT_APP_WS_URL=ws://localhost:8000/ws
REACT_APP_DEBUG_WEBSOCKET=true
REACT_APP_API_URL=http://localhost:8000
```

### Production Environment (.env.production)
```env
REACT_APP_WS_URL=wss://api.yourdomain.com/ws
REACT_APP_DEBUG_WEBSOCKET=false
REACT_APP_API_URL=https://api.yourdomain.com
```

## Running the Application

### Development Mode

```bash
cd frontend
npm start
```

This will:
- Start React development server on http://localhost:3000
- Enable hot-reload
- Show debug output in console
- Include source maps for debugging

### Production Build

```bash
cd frontend
npm run build
```

This will:
- Create optimized build in `build/` directory
- Minify and bundle code
- Generate source maps (if configured)

### Serve Production Build Locally

```bash
# Install serve package
npm install -g serve

# Serve the build
serve -s build -l 3000
```

## Integration Steps

### 1. Update App.js

```jsx
import React from 'react';
import { WebSocketProvider } from './context/WebSocketContext';
import EnrollmentPageWebSocket from './components/EnrollmentPageWebSocket';
import VerificationPageWebSocket from './components/VerificationPageWebSocket';

function App() {
  const WS_URL = process.env.REACT_APP_WS_URL || 'ws://localhost:8000/ws';

  return (
    <WebSocketProvider wsUrl={WS_URL}>
      <div className="App">
        <header className="header">
          <h1>Voice Biometric System</h1>
        </header>
        
        <div className="container">
          <div className="section">
            <EnrollmentPageWebSocket />
          </div>
          
          <div className="section">
            <VerificationPageWebSocket />
          </div>
        </div>
      </div>
    </WebSocketProvider>
  );
}

export default App;
```

### 2. Setup Routing (Optional)

```jsx
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';

function App() {
  return (
    <WebSocketProvider wsUrl={process.env.REACT_APP_WS_URL}>
      <Router>
        <Routes>
          <Route path="/enroll" element={<EnrollmentPageWebSocket />} />
          <Route path="/verify" element={<VerificationPageWebSocket />} />
        </Routes>
      </Router>
    </WebSocketProvider>
  );
}
```

### 3. Add to Existing Component

```jsx
import { useEnrollmentService } from './context/WebSocketContext';
import { useEnrollment } from './hooks/useEnrollment';

function MyComponent() {
  const enrollmentService = useEnrollmentService();
  const enrollment = useEnrollment(enrollmentService);
  
  return (
    <div>
      {/* Your UI here */}
    </div>
  );
}
```

## Backend Configuration

### Required Backend WebSocket Endpoint

The frontend expects a WebSocket endpoint at:
```
ws://host:port/ws
```

### Backend Setup Checklist

- [ ] WebSocket server running on configured URL
- [ ] Message router configured for enrollment/verification
- [ ] Database connected for storing embeddings
- [ ] CORS headers configured correctly
- [ ] Rate limiting configured (if needed)

### Test Backend Connection

```bash
# In browser console, test WebSocket connection
const ws = new WebSocket('ws://localhost:8000/ws');
ws.onopen = () => console.log('Connected');
ws.onmessage = (e) => console.log('Message:', e.data);
ws.onerror = (e) => console.error('Error:', e);
```

## Deployment Checklist

### Pre-Deployment
- [ ] All features tested locally
- [ ] No console errors or warnings
- [ ] Environment variables configured
- [ ] Backend endpoints verified
- [ ] HTTPS/WSS ready for production

### Deployment Steps

1. **Build the application**
   ```bash
   npm run build
   ```

2. **Test the build locally**
   ```bash
   serve -s build -l 3000
   ```

3. **Deploy to hosting platform**
   - Netlify: `npm run build` then connect repo
   - Vercel: `vercel --prod`
   - AWS S3 + CloudFront: `aws s3 sync build/ s3://bucket-name`
   - Docker: See Dockerfile section below

4. **Update WebSocket URL**
   - Change `REACT_APP_WS_URL` to production URL
   - Use WSS (WebSocket Secure) for HTTPS

5. **Verify deployment**
   - Check console for errors
   - Test enrollment flow
   - Test verification flow
   - Monitor WebSocket connection

## Docker Deployment

### Dockerfile

```dockerfile
# Build stage
FROM node:18-alpine as builder

WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# Production stage
FROM node:18-alpine

WORKDIR /app
RUN npm install -g serve
COPY --from=builder /app/build ./build

ENV REACT_APP_WS_URL=wss://api.yourdomain.com/ws
EXPOSE 3000

CMD ["serve", "-s", "build", "-l", "3000"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - REACT_APP_WS_URL=ws://backend:8000/ws
      - REACT_APP_API_URL=http://backend:8000
    depends_on:
      - backend

  backend:
    build:
      context: ./backend
    ports:
      - "8000:8000"
    environment:
      - DEBUG=false
```

### Build and Run

```bash
# Build Docker image
docker build -t voice-biometric-frontend ./frontend

# Run container
docker run -p 3000:3000 \
  -e REACT_APP_WS_URL=ws://localhost:8000/ws \
  voice-biometric-frontend

# Using Docker Compose
docker-compose up -d
```

## NGINX Configuration

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        root /var/www/voice-biometric/build;
        try_files $uri /index.html;
    }

    # WebSocket proxy
    location /ws {
        proxy_pass http://backend:8000/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

## Troubleshooting Deployment

### WebSocket Connection Failed

1. **Check WebSocket URL**
   ```bash
   # Verify backend is running
   curl -i http://localhost:8000/
   ```

2. **Check CORS**
   - Backend should allow WebSocket connections
   - Check backend logs for CORS errors

3. **Check HTTPS/WSS**
   - If frontend is HTTPS, backend must use WSS
   - Certificate must be valid

4. **Check Firewall**
   - Port 8000 (or custom port) must be open
   - WebSocket may need special firewall rules

### Performance Issues

1. **Reduce bundle size**
   ```bash
   npm run build -- --analyze
   ```

2. **Enable compression**
   - Configure GZIP on server
   - Use CDN for static assets

3. **Monitor WebSocket traffic**
   - Use browser DevTools → Network
   - Check WebSocket message frequency

## Monitoring and Logging

### Browser Console Logs

Enable debug mode to see detailed logs:
```jsx
<WebSocketProvider 
  wsUrl={WS_URL}
  debug={true}
>
  {children}
</WebSocketProvider>
```

### Production Error Tracking

Consider integrating error tracking:
```bash
npm install @sentry/react
```

```jsx
import * as Sentry from "@sentry/react";

Sentry.init({
  dsn: "your-dsn-here",
  environment: process.env.NODE_ENV,
});
```

### Analytics

Track enrollment/verification events:
```javascript
// In enrollment component
enrollmentService.on('enrollment:completed', (data) => {
  // Send analytics event
  console.log('Enrollment completed', data);
});
```

## Performance Optimization

### Build Optimization

```bash
# Analyze bundle size
npm install -g webpack-bundle-analyzer
npm run build -- --analyze

# Profile production build
npm run build --profile
```

### Runtime Optimization

1. **Lazy load components**
   ```jsx
   const EnrollmentPage = React.lazy(() => 
     import('./components/EnrollmentPageWebSocket')
   );
   ```

2. **Memoize components**
   ```jsx
   export default React.memo(EnrollmentPageWebSocket);
   ```

3. **Optimize re-renders**
   - Use React DevTools Profiler
   - Check for unnecessary re-renders

## Rollback Plan

If deployment fails:

1. **Revert to previous version**
   ```bash
   git revert HEAD
   npm run build
   # Redeploy
   ```

2. **Keep previous build**
   ```bash
   # Keep previous build in /build-backup
   # Restore if needed
   ```

3. **Database backups**
   - Ensure database is backed up
   - Can rollback data if needed

## Monitoring Checklist

After deployment, verify:

- [ ] Frontend loads without errors
- [ ] WebSocket connects successfully
- [ ] Enrollment flow works
- [ ] Verification flow works
- [ ] Error handling works
- [ ] Performance is acceptable
- [ ] No console errors
- [ ] Logs are clean

## Maintenance

### Regular Tasks

- **Weekly**: Check logs for errors
- **Monthly**: Update dependencies
- **Quarterly**: Review performance metrics

### Update Dependencies

```bash
# Check for updates
npm outdated

# Update all packages
npm update

# Update to latest major version
npm install -latest package-name
```

### Security Updates

```bash
# Check for vulnerabilities
npm audit

# Fix vulnerabilities
npm audit fix
```

## Support Contacts

- **Frontend Issues**: Contact frontend development team
- **WebSocket Issues**: Check backend logs
- **Deployment Issues**: Contact DevOps team
- **Backend Issues**: Contact backend development team

## Resources

- React Documentation: https://react.dev
- WebSocket API: https://developer.mozilla.org/en-US/docs/Web/API/WebSocket
- Deployment Guides: https://create-react-app.dev/deployment
- Docker: https://docs.docker.com

## Deployment Timeline

| Phase | Duration | Tasks |
|-------|----------|-------|
| Preparation | 1 hour | Setup, config, testing |
| Staging | 1 hour | Deploy to staging, verify |
| Production | 30 min | Deploy to production |
| Monitoring | 2 hours | Monitor for issues |

**Total Deployment Time**: ~4.5 hours

## Success Criteria

✅ Frontend loads successfully  
✅ WebSocket connects to backend  
✅ Enrollment flow completes  
✅ Verification flow completes  
✅ No console errors  
✅ Performance meets specs  
✅ All features working  
✅ Monitoring enabled  

---

**Deployment Date**: [To be filled]  
**Version**: 1.0.0  
**Status**: Ready for Deployment
