# stage-buddy-v2
Updated Stage Buddy AI repo

# Stage-Buddy

## Development

### Port Management

The dev server always runs on **port 3000**. In Codespaces:

1. **Use the forwarded port 3000 URL** from the VS Code Ports panel as the canonical URL
2. Open it in a **fresh browser tab** for best results
3. The Simple Browser can be ignored if it desyncs with your actual dev server

**If you see multiple ports (3000, 3001, 3002) or stale processes:**

```bash
# Diagnose
npm run dev:doctor

# Kill extra Next.js processes
pkill -f "next dev"

# Restart dev server
npm run dev
```

This prevents dev-server drift and ensures clean state.
