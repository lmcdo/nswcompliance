# Demo Recording Setup

This document explains how to prepare the UI for clean demo recordings by hiding optional widgets.

## Environment Variable: AI Assistant Toggle

The AI Assistant floating button (bottom-left corner) can be hidden for demo recordings to keep the UI focused and distraction-free.

### To Hide AI Assistant for Demo Recording

1. **Create `.env.local` file** in `frontend-nextjs/` directory:
   ```bash
   cd frontend-nextjs
   echo "NEXT_PUBLIC_ENABLE_AI_ASSISTANT=false" > .env.local
   ```

2. **Restart the dev server:**
   ```bash
   npm run dev
   ```

3. **Verify**: The "Quick Reference" floating button should be hidden from the bottom-left corner

### To Restore AI Assistant After Recording

Simply delete the `.env.local` file and restart:
```bash
rm .env.local
npm run dev
```

The AI Assistant will reappear in the bottom-left corner.

## Why Hide It for Demos?

**Objective reasoning:**
- **Focus**: 3-minute demos need tight focus on core CDC workflow
- **B2B pattern**: Product demos (Notion, Linear, Airtable) show ONE workflow clearly, not all features
- **Cognitive load**: Chat assistant is a separate discovery feature, not part of main compliance flow
- **Distraction**: Floating button draws attention away from Pattern Book → DCP provisions workflow

**Production should have it enabled** - this is only for clean demo recordings.

## Production Deployment

On Vercel (or production environment), the AI Assistant is enabled by default unless you explicitly set:
```
NEXT_PUBLIC_ENABLE_AI_ASSISTANT=false
```

**Do NOT set this in production** - only use for local demo recordings.

## Implementation Details

See `app/assessment/page.tsx` line 546-568:
```typescript
{/* AI Assistant Widget - toggle via NEXT_PUBLIC_ENABLE_AI_ASSISTANT env var */}
{process.env.NEXT_PUBLIC_ENABLE_AI_ASSISTANT !== 'false' && (
  <AIAssistantWidget ... />
)}
```

The widget is shown by default (undefined or true) and hidden only when explicitly set to 'false'.
