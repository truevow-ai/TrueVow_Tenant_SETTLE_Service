@echo off
echo 🔄 Transferring SETTLE Enterprise UI Components...

set SOURCE_DIR=C:\Users\yasha\OneDrive\Documents\TrueVow\Cursor\2025-TrueVow-Settle-Service\frontend
set TARGET_DIR=C:\Users\yasha\OneDrive\Documents\TrueVow\Cursor\Truevow-Customer-Portal

echo 📋 Creating directories...
mkdir "%TARGET_DIR%\lib\components\settle" 2>nul
mkdir "%TARGET_DIR%\app\(dashboard)\dashboard\settle" 2>nul
mkdir "%TARGET_DIR%\styles" 2>nul

echo 📋 Copying components...
copy "%SOURCE_DIR%\components\*" "%TARGET_DIR%\lib\components\settle\" /Y >nul
echo ✅ Components copied

echo 📋 Copying demo page...
copy "%SOURCE_DIR%\pages\dashboard.tsx" "%TARGET_DIR%\app\(dashboard)\dashboard\settle\" /Y >nul
echo ✅ Demo page copied

echo 📋 Copying styles...
copy "%SOURCE_DIR%\styles\globals.css" "%TARGET_DIR%\styles\settle-enterprise.css" /Y >nul
echo ✅ Styles copied

echo 📝 Creating environment documentation...
(
echo # SETTLE Service Environment Variables
echo.
echo Add these to your Customer Portal .env.local file:
echo.
echo NEXT_PUBLIC_SETTLE_API_URL=http://localhost:3008
echo NEXT_PUBLIC_SETTLE_API_KEY=your_api_key_here
echo.
echo For production:
echo NEXT_PUBLIC_SETTLE_API_URL=https://your-settle-service-url.com
) > "%TARGET_DIR%\SETTLE_ENV_SETUP.md"

echo ✅ Environment documentation created

echo.
echo 🎉 Transfer Complete!
echo Next steps:
echo 1. cd %TARGET_DIR%
echo 2. Add environment variables to .env.local
echo 3. npm run dev
echo 4. Visit http://localhost:3000/dashboard/settle