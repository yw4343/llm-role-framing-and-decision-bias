# Deployment Guide - Render

This guide covers deploying the LLM Role Framing frontend and backend to Render.

## Architecture Overview

- **Backend**: Flask API server (`src/api_server.py`) that runs experiments
- **Frontend**: Standalone HTML file (`frontend/index.html`) that connects to the backend API

## Prerequisites

1. A GitHub account with your project repository
2. A Render account (sign up at https://render.com - free tier available)

## Deployment Steps

### Step 1: Deploy the Backend API

1. **Create a Render Account**
   - Go to https://render.com
   - Sign up for a free account (or log in if you already have one)

2. **Create a New Web Service**
   - In your Render dashboard, click "New +" → "Web Service"
   - Connect your GitHub account if you haven't already
   - Select the repository containing this project

3. **Configure the Backend Service**
   - **Name**: `llm-role-framing-api` (or any name you prefer)
   - **Environment**: `Python 3`
   - **Region**: Choose the closest region to your users
   - **Branch**: `main` (or your default branch)
   - **Root Directory**: Leave empty (or set to `.` if needed)
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python src/api_server.py $PORT`
   - **Plan**: Free (or choose a paid plan for better performance)

4. **Environment Variables** (Optional)
   - You can add environment variables in the Render dashboard if needed
   - The OpenRouter API key will be entered through the frontend (users enter their own)
   - `PORT` is automatically set by Render (don't set manually)

5. **Deploy**
   - Click "Create Web Service"
   - Render will automatically build and deploy your backend
   - Wait for the deployment to complete (first deployment may take a few minutes)
   - Note your backend URL (e.g., `https://llm-role-framing-api.onrender.com`)

6. **Verify Backend is Running**
   - Once deployed, test the backend by visiting: `https://your-backend-url.onrender.com/api/experiments`
   - You should see a JSON response (empty array if no experiments yet)

### Step 2: Deploy the Frontend

1. **Create a Static Site**
   - In your Render dashboard, click "New +" → "Static Site"
   - Connect your GitHub repository (same one as the backend)
   - Select the repository

2. **Configure the Frontend Service**
   - **Name**: `llm-role-framing-frontend` (or any name you prefer)
   - **Branch**: `main` (or your default branch)
   - **Root Directory**: Leave empty
   - **Build Command**: Leave empty (no build needed - it's a standalone HTML file)
   - **Publish Directory**: `frontend`
   - **Plan**: Free

3. **Deploy**
   - Click "Create Static Site"
   - Render will deploy your frontend
   - Wait for deployment to complete
   - Note your frontend URL (e.g., `https://llm-role-framing-frontend.onrender.com`)

4. **Configure API URL**
   - After deployment, open your frontend URL in a browser
   - In the "API Base URL" field at the top of the page, enter your backend URL with `/api` appended
   - Format: `https://your-backend-url.onrender.com/api`
   - Example: If your backend is `https://llm-role-framing-api.onrender.com`, enter `https://llm-role-framing-api.onrender.com/api`

### Step 3: Using the Deployed Application

1. **Open the Frontend**
   - Navigate to your frontend URL in a web browser
   - Example: `https://llm-role-framing-frontend.onrender.com`

2. **Configure API Connection**
   - In the "API Base URL" field at the top, ensure it points to your backend
   - Format: `https://your-backend-url.onrender.com/api`

3. **Run Experiments**
   - Enter your OpenRouter API key
   - Select models, scenarios, and roles
   - Click "Run Experiment"
   - Monitor progress in real-time

## Using render.yaml (Alternative Method)

If you prefer to use the `render.yaml` configuration file:

1. **Deploy via Blueprint**
   - In Render dashboard, click "New +" → "Blueprint"
   - Connect your GitHub repository
   - Render will automatically detect and use `render.yaml`
   - Review the configuration and click "Apply"

2. **Manual Configuration**
   - The `render.yaml` file is already configured for the backend
   - You'll still need to create the static site manually for the frontend (as described above)

## Environment Variables

### Backend Environment Variables

Render automatically sets:
- `PORT`: Automatically set by Render (don't set manually)

Optional (set in Render dashboard if needed):
- `PYTHON_VERSION`: Defaults to 3.11.0 (can be set in `runtime.txt`)

### Frontend Configuration

The frontend uses the "API Base URL" input field to connect to the backend. Users can:
- Enter the backend URL manually in the UI
- The frontend will auto-detect the URL if deployed on the same domain (not applicable for separate services)

## Troubleshooting

### Backend Not Responding

1. **Check Render Logs**
   - Go to your backend service in Render dashboard
   - Click on "Logs" tab
   - Look for any error messages

2. **Verify Build Success**
   - Check that the build completed successfully
   - Ensure all dependencies in `requirements.txt` are installed

3. **Test Backend Directly**
   - Try accessing: `https://your-backend-url.onrender.com/api/experiments`
   - You should see a JSON response (empty array `[]` if no experiments)

4. **Check Service Status**
   - In Render dashboard, ensure the service shows "Live" status
   - If it shows "Sleeping" (free tier), the first request may take 30-60 seconds to wake up

### Frontend Can't Connect to Backend

1. **Verify API URL**
   - Ensure the API Base URL is correct
   - Must end with `/api`
   - Format: `https://your-backend-url.onrender.com/api`

2. **Check CORS**
   - The backend has CORS enabled for all origins
   - If you see CORS errors, check browser console for details

3. **Test Backend Accessibility**
   - Open the backend URL directly in a browser
   - Try: `https://your-backend-url.onrender.com/api/experiments`
   - Should return JSON (even if empty)

4. **Check Browser Console**
   - Open browser developer tools (F12)
   - Look for error messages in the Console tab
   - Check Network tab for failed requests

### Free Tier Limitations

Render's free tier has some limitations:
- **Sleeping Services**: Free services sleep after 15 minutes of inactivity
- **Wake Time**: First request after sleep may take 30-60 seconds
- **Build Time**: Limited build minutes per month
- **Bandwidth**: Limited bandwidth per month

**Solutions:**
- Upgrade to a paid plan for always-on services
- Use a service like UptimeRobot to ping your backend every 5 minutes (keeps it awake)
- Accept the wake delay for free tier usage

### Port Issues

- Render automatically sets the `PORT` environment variable
- The code reads `PORT` from environment variables automatically
- No manual configuration needed

## Local Development

For local development before deploying:

```bash
# Start backend
python src/api_server.py

# Open frontend
open frontend/index.html
# Or use: python -m http.server 8000 -d frontend
```

The frontend will default to `http://localhost:5001/api` for local development.

## Security Notes

1. **API Keys**: Users enter their OpenRouter API key through the frontend. Never commit API keys to the repository.

2. **CORS**: The backend allows all origins. For production, consider restricting CORS to your frontend domain in `src/api_server.py`:
   ```python
   CORS(app, origins=["https://your-frontend-url.onrender.com"])
   ```

3. **HTTPS**: Render automatically provides HTTPS for all services.

## Updating Your Deployment

To update your deployed application:

1. **Push Changes to GitHub**
   ```bash
   git add .
   git commit -m "Your update message"
   git push origin main
   ```

2. **Render Auto-Deploys**
   - Render automatically detects pushes to your repository
   - It will rebuild and redeploy both services
   - Check the "Events" tab in Render dashboard to monitor deployment

3. **Manual Deploy**
   - If auto-deploy is disabled, click "Manual Deploy" in Render dashboard
   - Select the branch and commit to deploy

## Cost

- **Free Tier**: Both backend and frontend can run on Render's free tier
- **Paid Plans**: Available if you need always-on services or more resources
- **No Credit Card Required**: Free tier doesn't require payment information

## Need Help?

If you encounter issues:

1. **Check Render Logs**: Most issues are visible in the service logs
2. **Verify Configuration**: Ensure all settings match this guide
3. **Test Locally First**: Make sure everything works locally before deploying
4. **Render Support**: Render has helpful documentation and support

For Render-specific help:
- Documentation: https://render.com/docs
- Community: https://community.render.com
